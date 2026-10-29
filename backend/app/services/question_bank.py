"""M4 deterministic bank import, validated sampling and grading. No model calls."""

from .topic_tree import active_clause
from collections import Counter
import hashlib
import json
import re
import secrets
import unicodedata
from datetime import timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select

from ..models import (
    Topic,
    PastPaper,
    PastQuestion,
    ExamPaper,
    ExamBlueprint,
    ExamAttempt,
)
from ..models.base import utc_now
from ..repositories.materials import checked_chunk, active_version
from .ai_material_scope import full_context
from .courses import owned_course
from .question_display import display_group

RNG = secrets.SystemRandom()
KINDS = {"single_choice", "solution"}
START = re.compile(r"(?m)^\s*(?:第\s*)?(\d{1,4})\s*(?:[.、．)）]|题[：:、.]?)\s*")
OPTION = re.compile(r"(?:^|[ \t]+)([A-DＡ-Ｄ])[.．、:：)）]\s*", re.M)
META = re.compile(
    r"^\s*(?:【\s*)?(参考答案|正确答案|答案|解析|知识点|知识标签|标签|唯一答案|分值)(?:\s*】)?\s*[:：]?\s*(.*)$"
)


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def normal(value):
    return unicodedata.normalize("NFKC", value).strip()


def question_fingerprint(stem):
    return hashlib.sha256(
        normal(stem).replace("\r\n", "\n").replace("\r", "\n").encode()
    ).hexdigest()


def no_active_attempt(db, user_id, course_id):
    if db.scalar(
        select(ExamAttempt.id)
        .join(ExamPaper)
        .where(
            ExamAttempt.user_id == user_id,
            ExamPaper.course_id == course_id,
            ExamAttempt.status == "IN_PROGRESS",
        )
        .limit(1)
    ):
        raise HTTPException(
            409, "请先提交本课程正在进行的作答，再查看题库答案或编辑题目"
        )


def topic_rows(db, user_id, course_id, ids):
    ids = [str(t) for t in ids]
    rows = db.scalars(
        select(Topic).where(
            active_clause(),
            Topic.user_id == user_id,
            Topic.course_id == course_id,
            Topic.id.in_(ids),
        )
    ).all()
    if len(rows) != len(set(ids)):
        raise HTTPException(404, "知识标签不存在或不属于本课程")
    if any(t.merged_into_id for t in rows):
        raise HTTPException(409, "所选标签已合并，请重新选择")
    return rows


def parse_text(content):
    from .bank_strict_markdown import HEADER, parse as parse_strict
    from .bank_parser import parse

    if content.lstrip("\ufeff").startswith(HEADER):
        return parse_strict(content)
    return parse(content)


def validate_question(question, data):
    errors = []
    kind = question.question_type
    if kind not in KINDS or not question.stem.strip() or len(question.stem) > 20000:
        errors.append("请核对题型与非空题干")
    if kind == "single_choice":
        options = data.get("options", [])
        if (
            len(options) != 4
            or any(not v.strip() or len(v) > 10000 for v in options)
            or len(set(normal(v) for v in options)) != 4
        ):
            errors.append("单选题需要四个非空且不同的选项")
        if question.answer not in (None, "") and question.answer not in list("ABCD"):
            errors.append("请设置正确选项A/B/C/D；不会自动猜答案")
    if kind == "fill_blank":
        if type(data.get("unique_answer")) is not bool:
            errors.append("请明确选择是否唯一答案")
        answers = data.get("blank_answers", [])
        blank_count = len(re.findall(r"_{2,}|（\s*）|\(\s*\)", question.stem))
        if answers and blank_count and len(answers) != blank_count:
            errors.append("逐空参考答案数量应与题干空位数量一致")
        if len(answers) > 30 or any(
            not isinstance(a, str) or not a.strip() or len(a) > 20000 for a in answers
        ):
            errors.append("请填写逐空参考答案，多空用 || 分隔")
    if data.get("illustrations") and not data.get("images_reviewed"):
        errors.append("请核对插图")
    if data.get("content_profile") == "answer_only":
        errors.append("此段只有答案或解析，请补充实际题干")
    return errors


def question_payload(question):
    data = json.loads(question.bank_data_json)
    return {
        "id": question.id,
        "number": question.number,
        "display_group": display_group(question.number, question.paper_id),
        "stem": question.stem,
        "question_type": question.question_type,
        "points": question.points,
        "answer": question.answer,
        "answer_source": question.answer_source,
        "status": question.status,
        "topic_id": question.topic_id,
        "revision": question.revision,
        "bank_data": data | {"warnings": validate_question(question, data)},
    }


def import_bank(db, user_id, course_id, payload):
    owned_course(db, user_id, course_id, lock=True)
    no_active_attempt(db, user_id, course_id)
    if bool(payload.content.strip()) == bool(payload.version_id):
        raise HTTPException(422, "请提供正文或已解析资料版本，两者只能选一")
    sources = []
    content = payload.content
    if payload.version_id:
        if payload.strict_markdown:
            version = active_version(db, str(payload.version_id), user_id, course_id)
            from pathlib import Path
            from ..core.storage import get_storage
            from .bank_strict_markdown import validate_file

            try:
                with (
                    get_storage()
                    .checked(Path(version.source_path))
                    .open("rb") as stream
                ):
                    raw = stream.read(2 * 1024 * 1024 + 1)
            except OSError:
                raise HTTPException(409, "Markdown原件不可用，请重新上传") from None
            content = validate_file(version.original_filename, raw)
            if hashlib.sha256(raw).hexdigest() != version.sha256:
                raise HTTPException(409, "Markdown原件已变化，请重新上传以建立新版本")
        sources, _ = full_context(db, user_id, course_id, [str(payload.version_id)])
        if payload.strict_markdown:
            if not sources:
                raise HTTPException(409, "Markdown原件尚未解析和索引就绪，请稍后重试")
            from ..models import DocumentChunk

            offsets = dict(
                db.execute(
                    select(DocumentChunk.id, DocumentChunk.start_offset).where(
                        DocumentChunk.user_id == user_id,
                        DocumentChunk.version_id == str(payload.version_id),
                    )
                ).all()
            )
            sources = [
                source
                | {"raw_start": offsets[source["source_id"]] + source["chunk_start"]}
                for source in sources
            ]
        else:
            content = "\n".join(s["text"] for s in sources)
    if payload.strict_markdown:
        from .bank_strict_markdown import parse as parse_strict

        parse_strict(content)
    digest = hashlib.sha256(content.strip().encode()).hexdigest()
    request_hash = hashlib.sha256(
        encode(payload.model_dump(mode="json")).encode()
    ).hexdigest()
    if payload.request_id:
        existing = db.get(PastPaper, str(payload.request_id))
        if existing:
            if existing.user_id != user_id or existing.course_id != course_id:
                raise HTTPException(404, "导入请求不可访问")
            if (
                json.loads(existing.bank_meta_json).get("import_request_hash")
                != request_hash
            ):
                raise HTTPException(409, "同一导入请求不能更改内容")
            return existing
    parser_version = "bank-markdown-v1" if payload.strict_markdown else "bank-rules-v3"
    parsed = parse_text(content)
    if payload.strict_markdown and payload.version_id:
        parsed = [
            item | {"source_version_id": str(payload.version_id)} for item in parsed
        ]
    paper = PastPaper(
        id=str(payload.request_id) if payload.request_id else str(uuid4()),
        user_id=user_id,
        course_id=course_id,
        title=payload.title,
        year=payload.year,
        content=content,
        content_hash=digest,
        bank_meta_json=encode(
            {
                "version_id": str(payload.version_id) if payload.version_id else None,
                "provenance": payload.provenance,
                "variant": payload.variant,
                "parser": parser_version,
                "import_request_hash": request_hash,
                "content_profile": Counter(i["content_profile"] for i in parsed),
            }
        ),
    )
    db.add(paper)
    db.flush()
    populate_bank(
        db,
        user_id,
        course_id,
        paper,
        content,
        parsed,
        sources,
        payload.default_topic_ids,
    )
    db.commit()
    return paper


def populate_bank(
    db, user_id, course_id, paper, content, parsed, sources=None, default_topic_ids=()
):
    sources = sources or []
    default_topic_ids = [str(t) for t in default_topic_ids]
    topic_rows(db, user_id, course_id, default_topic_ids)
    cursor = 0
    segments = []
    for source in sources:
        start = source.get("raw_start", cursor)
        segments.append((start, start + len(source["text"]), source))
        cursor += len(source["text"]) + 1
    from .bank_markdown import normalize

    for item in parsed:
        if item["kind"] in {"fill_blank", "solution"}:
            from .bank_question_types import solution_reference

            item = item | {
                "kind": "solution",
                "answer": solution_reference(
                    item.get("answer"), item.get("blank_answers", [])
                ),
                "blank_answers": [],
            }
        normalize_item = (
            (lambda value: value) if item.get("strict_markdown") else normalize
        )
        item = {
            **item,
            "stem": normalize_item(item["stem"]),
            "options": [normalize_item(o) for o in item["options"]],
            "explanation": normalize_item(item["explanation"]),
        }
        topics = list(default_topic_ids)
        for name in item["tag_names"]:
            if len(name) > 240:
                raise HTTPException(422, "标签最长240字符")
            candidates = db.scalars(
                select(Topic).where(
                    active_clause(),
                    Topic.user_id == user_id,
                    Topic.course_id == course_id,
                )
            ).all()
            matches = {}
            for existing_topic in candidates:
                if normal(name) in {
                    normal(existing_topic.name),
                    *(normal(a) for a in json.loads(existing_topic.aliases_json)),
                }:
                    canonical = existing_topic
                    visited = set()
                    while canonical.merged_into_id and canonical.id not in visited:
                        visited.add(canonical.id)
                        canonical = db.get(Topic, canonical.merged_into_id)
                    from .topic_tree import is_deleted

                    if not is_deleted(canonical):
                        matches[canonical.id] = canonical
            if len(matches) > 1:
                raise HTTPException(422, "知识标签别名存在歧义，请先整理词表")
            topic = next(iter(matches.values()), None)
            if not topic:
                topic = Topic(user_id=user_id, course_id=course_id, name=name)
                db.add(topic)
                db.flush()
            while topic.merged_into_id:
                topic = db.get(Topic, topic.merged_into_id)
            topics.append(topic.id)
        topics = list(dict.fromkeys(topics))
        if len(topics) > 5:
            raise HTTPException(
                422, f"题号{item['number']}超过每题5个标签的上限，请先整理标签"
            )
        recommendation = {
            "version": "bank-topic-ai-v3",
            "existing": [],
            "candidates": [],
            "auto_assigned": False,
        }
        citations = []
        for start, end, source in segments:
            left, right = max(start, item["start"]), min(end, item["end"])
            if right > left:
                quote = source["text"][left - start : right - start][:500]
                if quote.strip():
                    citations.append(
                        {
                            "version_id": source["version_id"],
                            "chunk_id": source["source_id"],
                            "locator": source["locator"],
                            "source_kind": source["source_kind"],
                            "quote": quote,
                            "quote_hash": hashlib.sha256(quote.encode()).hexdigest(),
                        }
                    )
        db.add(
            PastQuestion(
                user_id=user_id,
                paper_id=paper.id,
                number=item["number"],
                stem=item["stem"],
                question_type=item["kind"],
                points=item["points"],
                answer=normalize_item(item["answer"])
                if item["kind"] == "solution"
                else item["answer"],
                answer_source="user_provided" if item["answer"] else "unknown",
                topic_id=topics[0] if topics else None,
                bank_data_json=encode(
                    {
                        **({"year": item["year"]} if "year" in item else {}),
                        "content_format": "markdown",
                        "options": item["options"],
                        "blank_answers": item["blank_answers"],
                        "unique_answer": None,
                        "topic_ids": topics,
                        "topic_index": recommendation,
                        "explanation": item["explanation"],
                        "citations": citations,
                        "content_profile": item["content_profile"],
                        "import_warnings": item.get("warnings", []),
                        "source_images": item.get("source_images", []),
                        "source_version_id": item.get("source_version_id"),
                    }
                ),
            )
        )
    db.flush()
    return paper


def eligible_questions(db, user_id, course_id, *, paper_id=None, deduplicate=False):
    rows = db.execute(
        select(PastQuestion, PastPaper.bank_meta_json)
        .join(PastPaper)
        .where(
            PastQuestion.user_id == user_id,
            PastPaper.user_id == user_id,
            PastPaper.course_id == course_id,
            PastQuestion.status == "CONFIRMED",
            PastPaper.review_status == "CONFIRMED",
            *([PastPaper.id == paper_id] if paper_id else []),
        )
        .order_by(PastQuestion.id)
    ).all()
    result = []
    seen = set()
    for q, paper_meta in rows:
        meta = json.loads(paper_meta)
        if meta.get("deleted_by_user"):
            continue
        data = json.loads(q.bank_data_json)
        if validate_question(q, data):
            continue  # Legacy/unknown content is not silently promoted to a bank question.
        try:
            from .bank_images import check_images

            if data.get("source_version_id"):
                active_version(db, data["source_version_id"], user_id, course_id)
            check_images(db, user_id, course_id, data.get("illustrations", []))
            for citation in data.get("citations", []):
                checked_chunk(
                    db,
                    citation["version_id"],
                    citation["chunk_id"],
                    citation["quote"],
                    user_id,
                    course_id,
                )
        except HTTPException:
            continue
        fingerprint = question_fingerprint(q.stem)
        if not deduplicate or fingerprint not in seen:
            seen.add(fingerprint)
            result.append((q, data))
    return result


def shuffled_question(q, data, points=None, *, shuffle_options=True):
    options = list(data.get("options", []))
    answer = q.answer
    if q.question_type == "single_choice" and shuffle_options:
        indices = list(range(4))
        RNG.shuffle(indices)
        options = [options[i] for i in indices]
        answer = (
            "ABCD"[indices.index("ABCD".index(q.answer))]
            if q.answer in list("ABCD")
            else None
        )
    return {
        "id": str(uuid4()),
        "type": "solution" if q.question_type == "fill_blank" else q.question_type,
        "stem": q.stem,
        "options": options,
        "answer": answer,
        "blank_answers": data.get("blank_answers", []),
        "unique_answer": data.get("unique_answer"),
        "blank_count": len(data.get("blank_answers", []))
        or len(re.findall(r"_{2,}|（\s*）|\(\s*\)", q.stem))
        or 1,
        "points": points or q.points or 1,
        "points_known": points is not None or q.points is not None,
        "topic_ids": data["topic_ids"],
        "topic": "题库知识标签",
        "source_question_id": q.id,
        "display_group": display_group(q.number, q.paper_id),
        "source_revision": q.revision,
        "source_version_id": data.get("source_version_id"),
        "citations": data.get("citations", []),
        "explanation": data.get("explanation", ""),
        "illustrations": data.get("illustrations", []),
        "generation_status": "USER_BANK",
    }


def draw(db, user_id, course_id, payload):
    owned_course(db, user_id, course_id, lock=True)
    # Same key is stored as the blueprint ID, preserving old paper/blueprint relationships.
    key = str(payload.request_id)
    config = payload.model_dump(mode="json")
    existing = db.get(ExamBlueprint, key)
    if existing:
        if existing.user_id != user_id or existing.course_id != course_id:
            raise HTTPException(404, "抽题请求不可访问")
        if json.loads(existing.config_json) != config:
            raise HTTPException(409, "同一抽题请求不能更改条件")
        paper = db.scalar(
            select(ExamPaper).where(
                ExamPaper.blueprint_id == key, ExamPaper.user_id == user_id
            )
        )
        if paper:
            return paper
    topic_rows(db, user_id, course_id, payload.topic_ids)
    from .topic_tree import expand

    requested = expand(db, user_id, course_id, payload.topic_ids)
    pool = [
        (q, data)
        for q, data in eligible_questions(db, user_id, course_id)
        if (not requested or requested.intersection(data["topic_ids"]))
        and (not payload.question_type or q.question_type == payload.question_type)
    ]
    if len(pool) < payload.count:
        raise HTTPException(
            422,
            {
                "message": "符合标签和题型的已确认题目不足，请补充或减少题数",
                "available": len(pool),
                "requested": payload.count,
            },
        )
    questions = [
        shuffled_question(q, data) for q, data in RNG.sample(pool, payload.count)
    ]
    from .question_context import attach_context

    attach_context(db, user_id, course_id, questions)
    db.add(
        ExamBlueprint(
            id=key,
            user_id=user_id,
            course_id=course_id,
            name=payload.title,
            config_json=encode(config),
        )
    )
    paper = ExamPaper(
        user_id=user_id,
        course_id=course_id,
        blueprint_id=key,
        title=payload.title,
        mode="question_bank",
        questions_json=encode(questions),
    )
    db.add(paper)
    db.commit()
    return paper


def public_question(q):
    return {"points_known": points_known(q)} | {
        k: q[k]
        for k in (
            "id",
            "type",
            "stem",
            "options",
            "points",
            "topic",
            "topic_ids",
            "blank_count",
            "unique_answer",
            "illustrations",
            "display_group",
            "source_number",
            "whole_stem",
            "whole_illustrations",
            "practice_unit",
            "context_stem",
            "context_illustrations",
        )
        if k in q
    }


def generate_blueprint(db, user_id, blueprint):
    from collections import deque

    config = json.loads(blueprint.config_json)
    pool = eligible_questions(db, user_id, blueprint.course_id, deduplicate=True)
    RNG.shuffle(pool)
    items = {item["type"]: item for item in config["question_types"]}
    count = sum(item["count"] for item in items.values())
    unscoped = not config.get("topics")
    quotas = config.get("topics") or [{"name": "综合", "count": count}]
    topics = db.scalars(
        select(Topic).where(
            active_clause(),
            Topic.user_id == user_id,
            Topic.course_id == blueprint.course_id,
        )
    ).all()
    from .topic_tree import expand

    names_by_id = {t.id: {t.name, *json.loads(t.aliases_json)} for t in topics}
    for topic in topics:
        for child_id in expand(db, user_id, blueprint.course_id, [topic.id]):
            names_by_id.setdefault(child_id, set()).update(
                {topic.name, *json.loads(topic.aliases_json)}
            )
    graph = {}

    def edge(a, b, capacity):
        graph.setdefault(a, {})[b] = capacity
        graph.setdefault(b, {})[a] = 0

    for kind, item in items.items():
        edge("start", "type:" + kind, item["count"])
    for i, (q, data) in enumerate(pool):
        if q.question_type not in items:
            continue
        node = "q:" + str(i)
        edge("type:" + q.question_type, node, 1)
        for n, quota in enumerate(quotas):
            if unscoped or any(
                quota["name"] in names_by_id.get(t, set()) for t in data["topic_ids"]
            ):
                edge(node, "topic:" + str(n), 1)
    for n, quota in enumerate(quotas):
        edge("topic:" + str(n), "end", quota["count"])
    # Integral max-flow satisfies independent type/tag quotas without inventing
    # a type-by-tag pairing or reusing a question with overlapping labels.
    flow = 0
    while flow < count:
        previous = {"start": None}
        queue = deque(["start"])
        while queue and "end" not in previous:
            node = queue.popleft()
            for nxt, capacity in graph[node].items():
                if capacity and nxt not in previous:
                    previous[nxt] = node
                    queue.append(nxt)
        if "end" not in previous:
            raise HTTPException(
                422, "题库无法同时满足题型、标签配额与不重复约束，请补充题库或调整蓝图"
            )
        node = "end"
        while previous[node] is not None:
            before = previous[node]
            graph[before][node] -= 1
            graph[node][before] += 1
            node = before
        flow += 1
    questions = []
    for i, (q, data) in enumerate(pool):
        node = "q:" + str(i)
        parent = "type:" + q.question_type
        if node in graph.get(parent, {}) and graph[parent][node] == 0:
            question = shuffled_question(
                q, data, points=items[q.question_type]["points"]
            )
            assigned = next(
                n
                for n in range(len(quotas))
                if graph[node].get("topic:" + str(n)) == 0
                and "topic:" + str(n) in graph[node]
            )
            question["topic"] = (
                quotas[assigned]["name"] if not unscoped else "题库知识标签"
            )
            questions.append(question)
    from .question_context import attach_context

    attach_context(db, user_id, blueprint.course_id, questions)
    paper = ExamPaper(
        user_id=user_id,
        course_id=blueprint.course_id,
        blueprint_id=blueprint.id,
        title=blueprint.name,
        mode="question_bank",
        questions_json=encode(questions),
    )
    db.add(paper)
    db.commit()
    return paper


def attempt_snapshot(attempt, paper, blueprint):
    snapshot = json.loads(attempt.snapshot_json)
    if snapshot:
        return snapshot
    return {
        "questions": json.loads(paper.questions_json),
        "duration_minutes": json.loads(blueprint.config_json).get(
            "duration_minutes", 30
        ),
    }


def deadline(attempt, snapshot):
    started = attempt.created_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    return started + timedelta(minutes=snapshot["duration_minutes"])


def points_known(q):
    return q.get("points_known", not bool(q.get("source_question_id")))


def grade(q, given):
    answered = (
        isinstance(given, str)
        and bool(given.strip())
        or isinstance(given, bool)
        or isinstance(given, list)
        and bool(given)
        and all(isinstance(v, str) and bool(v.strip()) for v in given)
    )
    kind = q["type"]
    if kind in {"solution", "short_answer"}:
        return {
            "status": "pending_self_review"
            if points_known(q)
            else "submitted"
            if answered
            else "unanswered",
            "automatic": False,
            "submitted": bool(answered),
        }
    if (
        kind == "fill_blank"
        and (not q.get("unique_answer") or not q.get("blank_answers"))
    ) or (kind == "single_choice" and q.get("answer") not in list("ABCD")):
        return {
            "status": "pending_self_review",
            "automatic": False,
            "submitted": bool(answered),
        }
    if kind == "fill_blank":
        expected = q["blank_answers"]
        actual = [given] if isinstance(given, str) and len(expected) == 1 else given
        correct = (
            isinstance(actual, list)
            and len(actual) == len(expected)
            and all(normal(a) == normal(b) for a, b in zip(actual, expected))
        )
    else:
        correct = type(given) is type(q.get("answer")) and given == q.get("answer")
    return {
        "status": "correct" if correct else "incorrect" if answered else "unanswered",
        "automatic": True,
        "submitted": bool(answered),
        **(
            {"score": q["points"] if correct else 0, "max_score": q["points"]}
            if points_known(q)
            else {}
        ),
    }


def mark_mistake(db, user_id, attempt_id, q, given):
    from ..models import Mistake

    existing = db.scalar(
        select(Mistake.id).where(
            Mistake.user_id == user_id,
            Mistake.attempt_id == attempt_id,
            Mistake.question_id == q["id"],
        )
    )
    if not existing:
        source_id = q.get("source_question_id")
        attempt = db.get(ExamAttempt, attempt_id)
        paper = db.get(ExamPaper, attempt.paper_id)
        if source_id:
            from .mistake_progress import next_sequence

            prior = db.scalars(
                select(Mistake)
                .join(ExamAttempt, Mistake.attempt_id == ExamAttempt.id)
                .join(ExamPaper, ExamAttempt.paper_id == ExamPaper.id)
                .where(
                    Mistake.user_id == user_id,
                    ExamPaper.user_id == user_id,
                    ExamPaper.course_id == paper.course_id,
                )
                .order_by(Mistake.created_at.desc())
            ).all()
            for row in prior:
                data = json.loads(row.detail_json)
                if data.get("question", {}).get("source_question_id") != source_id:
                    continue
                events = data.setdefault("relapses", {})
                event_id = f"{attempt_id}:{q['id']}"
                if event_id not in events:
                    sequence = next_sequence(data)
                    events[event_id] = {
                        "attempt_id": attempt_id,
                        "question_id": q["id"],
                        "completed_at": utc_now().isoformat(),
                        "sequence": sequence,
                    }
                data["removed_from_bank"] = False
                row.detail_json = encode(data)
                return
        db.add(
            Mistake(
                user_id=user_id,
                attempt_id=attempt_id,
                question_id=q["id"],
                detail_json=encode({"question": q, "given": given}),
            )
        )


def finish_grading(db, attempt, questions):
    answers = json.loads(attempt.answers_json)
    grades = {q["id"]: grade(q, answers.get(q["id"])) for q in questions}
    for q in questions:
        g = grades[q["id"]]
        if g["automatic"] and g["status"] != "correct":
            mark_mistake(db, attempt.user_id, attempt.id, q, answers.get(q["id"]))
    attempt.score = sum(
        grades[q["id"]].get("score", 0) for q in questions if points_known(q)
    )
    attempt.grading_json = encode(grades)
    attempt.status = (
        "SUBMITTED"
        if any(g["status"] == "pending_self_review" for g in grades.values())
        else "SCORED"
    )


def submitted_questions(attempt, paper, blueprint):
    return attempt_snapshot(attempt, paper, blueprint)["questions"]


def require_source_valid(db, user_id, course_id, questions):
    for q in questions:
        from .question_context import validate_sources

        validate_sources(
            db,
            user_id,
            course_id,
            q.get("context_sources", []),
            q.get("context_illustrations", []),
        )
        if q.get("source_version_id"):
            active_version(db, q["source_version_id"], user_id, course_id)
        for c in q.get("citations", []):
            checked_chunk(
                db, c["version_id"], c["chunk_id"], c["quote"], user_id, course_id
            )


def new_attempt(db, user_id, paper, blueprint):
    existing = db.scalar(
        select(ExamAttempt).where(
            ExamAttempt.user_id == user_id,
            ExamAttempt.paper_id == paper.id,
            ExamAttempt.status == "IN_PROGRESS",
        )
    )
    if existing:
        return existing
    questions = json.loads(paper.questions_json)
    require_source_valid(db, user_id, paper.course_id, questions)
    attempt = ExamAttempt(
        user_id=user_id,
        paper_id=paper.id,
        snapshot_json=encode(
            {
                "questions": questions,
                "duration_minutes": json.loads(blueprint.config_json).get(
                    "duration_minutes", 30
                ),
            }
        ),
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


def is_expired(attempt, snapshot):
    return utc_now() >= deadline(attempt, snapshot)
