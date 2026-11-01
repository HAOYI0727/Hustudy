"""Local QA/report suggestions, never a semantic-equivalence decision."""

import re
import unicodedata
from fastapi import HTTPException
from sqlalchemy import select
from ..core.config import get_user_settings
from ..models import AIResult, ProcessingJob, RemoteQuery
from ..models.base import utc_now
from ..ai.providers import PROMPT_VERSION
from ..schemas.study_reports import REPORT_PROMPT_VERSION, report_envelope
from ..schemas.question_drafts import candidate_envelope
from .ai_context import validate_context
from ..repositories.materials import active_version

HISTORY_LIMIT = 100
CHECK_LIMIT = 12
RESULT_LIMIT = 3
MIN_SIMILARITY = 0.42
GENERIC = {"依据", "根据", "所选", "资料", "解释", "说明", "请问", "什么", "哪些", "如何"}


def features(question):
    # Normalize for ranking only. Never rewrite the actual request or drop negation.
    text = unicodedata.normalize("NFKC", question).casefold()
    result = {"word:" + word: 3 for word in re.findall(r"[a-z0-9_]+", text)}
    for phrase in re.findall(r"[\u4e00-\u9fff]+", text):
        for i in range(max(1, len(phrase) - 1)):
            term = phrase[i:i + 2]
            if term not in GENERIC:
                result["han:" + term] = 1
    return result


def similarity(left, right):
    a, b = features(left), features(right)
    denominator = sum(a.values()) + sum(b.values())
    return 2 * sum(a[k] for k in a.keys() & b.keys()) / denominator if denominator else 0


def request_context(query):
    try:
        if candidate_envelope(query):
            return None
        report = report_envelope(query)
    except (ValueError, TypeError, KeyError):
        return None
    if report:
        return report.goal, report.model_dump(mode="json", exclude={"goal"})
    return query, None


def ready(db, row):
    from .remote_ai import validate_request_dependencies

    settings = get_user_settings(row.user_id)
    if (
        row.job_id or row.expires_at <= utc_now()
        or request_context(row.query) is None
        or settings.llm_provider not in {"zhipu", "compatible"}
        or settings.llm_model != row.model or settings.llm_endpoint != row.endpoint
    ):
        return False
    try:
        validate_context(db, row.user_id, row.course_id, row.sources)
        validate_request_dependencies(db, row)
        for source in row.sources:
            for version_id in source.get("request_scope", {}).get("version_ids", []):
                active_version(db, version_id, row.user_id, row.course_id)
    except HTTPException:
        return False
    return True


def active_references(value):
    if isinstance(value, list):
        return all(active_references(item) for item in value)
    if isinstance(value, dict):
        if {"version_id", "chunk_id", "quote"} <= value.keys():
            return value.get("availability") == "active"
        return all(active_references(item) for item in value.values())
    return True


def find_related(db, row):
    from .remote_ai import validated_result

    if not ready(db, row):
        return []
    goal, settings = request_context(row.query)
    is_report = settings is not None
    # Project only bounded metadata first, not 100 complete source/answer snapshots.
    history = db.execute(
        select(RemoteQuery.id, RemoteQuery.query, AIResult.id, AIResult.created_at)
        .join(AIResult, AIResult.id == RemoteQuery.result_id)
        .join(ProcessingJob, ProcessingJob.id == RemoteQuery.job_id)
        .where(
            RemoteQuery.user_id == row.user_id,
            RemoteQuery.course_id == row.course_id,
            RemoteQuery.query != row.query,
            RemoteQuery.model == row.model,
            RemoteQuery.endpoint == row.endpoint,
            AIResult.user_id == row.user_id,
            AIResult.course_id == row.course_id,
            AIResult.status == "grounded",
            AIResult.model_mode == "real",
            AIResult.prompt_version == (REPORT_PROMPT_VERSION if is_report else PROMPT_VERSION),
            ProcessingJob.user_id == row.user_id,
            ProcessingJob.resource_id == RemoteQuery.id,
            ProcessingJob.type == "AI_ANALYSIS",
            ProcessingJob.status == "SUCCEEDED",
        )
        .order_by(AIResult.created_at.desc(), AIResult.id.desc())
        .limit(HISTORY_LIMIT)
    ).all()
    ranked = []
    for index, (request_id, question, result_id, _) in enumerate(history):
        context = request_context(question)
        if context is not None and context[1] == settings and context[0] != goal:
            ranked.append((similarity(goal, context[0]), index, request_id, result_id))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    found, seen = [], set()
    for score, _, request_id, result_id in ranked[:CHECK_LIMIT]:
        if score < MIN_SIMILARITY:
            break
        previous = db.get(RemoteQuery, request_id)
        result = db.get(AIResult, result_id)
        if previous.sources != row.sources:
            continue
        try:
            validated = validated_result(db, result)
        except (HTTPException, ValueError, TypeError, KeyError):
            continue
        body = validated.result
        if (
            body.get("partial") or body.get("dependency_status") == "stale"
            or not active_references(body) or not body.get("citations")
            or is_report != (body.get("result_kind") == "study_report")
            or is_report and not (body.get("study_report") or body.get("study_report_sections"))
        ):
            continue
        # Prefer the latest usable answer for each original question.
        if previous.query in seen:
            continue
        answer = re.sub(r"\s+", " ", str(body.get("answer", ""))).strip()
        if not answer:
            continue
        seen.add(previous.query)
        found.append({
            "id": result.id, "query": result.query,
            "answer_preview": answer[:260] + ("…" if len(answer) > 260 else ""),
            "model": row.model, "created_at": result.created_at,
        })
        if len(found) == RESULT_LIMIT:
            break
    return found


def related_answer(db, user_id, query_id, result_id):
    from .remote_ai import owned_query, validated_result
    from .courses import owned_course

    row = owned_query(db, user_id, query_id)
    owned_course(db, user_id, row.course_id, lock=True)
    if not any(item["id"] == result_id for item in find_related(db, row)):
        raise HTTPException(409, "历史结果不再符合推荐条件或来源已变化，请重新预览后核对")
    # Return the unchanged historical identity and original question, never a new answer.
    return validated_result(db, db.get(AIResult, result_id))
