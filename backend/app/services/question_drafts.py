"""M2 candidate preview/demo services; dependencies come through read-only interfaces."""

import hashlib
import json
from pathlib import Path
from fastapi import HTTPException
from ..ai.question_drafts import build_candidates
from ..models import AIResult
from ..repositories.materials import active_version
from ..schemas.question_drafts import (
    CandidateEnvelope,
    CandidateOutput,
    CANDIDATE_PREFIX,
    DEMO_PROMPT_VERSION,
)
from .ai_material_scope import full_context
from .exam_ai_context import candidate_context
from .courses import owned_course


def prepare(db, user_id, course_id, request):
    sources, coverage = full_context(
        db,
        user_id,
        course_id,
        [str(v) for v in request.version_ids],
        [str(c) for c in request.chunk_ids],
        max_chars=32000,
        max_chunks=128,
    )
    context = candidate_context(
        db,
        user_id,
        course_id,
        [str(t) for t in request.topic_ids],
        [str(q) for q in request.original_past_question_ids],
    )
    if not sources or not any(
        s["version_id"] == str(request.chapter_id) for s in sources
    ):
        raise HTTPException(
            409,
            {
                "message": "目标章节没有纳入可用片段，请调整片段范围",
                "status": "insufficient_evidence",
            },
        )
    envelope = CandidateEnvelope(
        request=request, coverage=coverage, exam_context=context, per_question_topics=True
    )
    return sources, envelope


def encode(envelope):
    return CANDIDATE_PREFIX + envelope.model_dump_json()


def demo(db, user_id, course_id, request):
    owned_course(db, user_id, course_id, lock=True)
    sources, envelope = prepare(db, user_id, course_id, request)
    fixture = Path(__file__).resolve().parents[3] / "fixtures/materialhub_demo.md"
    version = active_version(db, str(request.chapter_id), user_id, course_id)
    known = (
        version.sha256 == hashlib.sha256(fixture.read_bytes()).hexdigest()
        and request.count <= 2
        and request.mode != "variant"
        and request.difficulty_label == "basic"
        and [t["name"] for t in envelope.exam_context["topics"]] == ["进程与线程"]
    )
    quote = "进程是资源分配的基本单位，线程是调度和执行的基本单位。"
    source = next(
        (s for s in sources if s["version_id"] == version.id and quote in s["text"]),
        None,
    )
    if not known or source is None:
        output = {
            "status": "insufficient_evidence",
            "reason": "固定演示仅支持自制materialhub_demo.md、进程与线程Topic、基础难度及最多2题；未知输入不模拟AI理解。",
            "questions": [],
        }
    else:
        questions = []
        for index in range(request.count):
            exercise = {
                "topic_ids": [str(t) for t in request.topic_ids],
                "options": [],
                "rubric": [],
                "original_past_question_ids": [],
                "evidence": [{"source_id": source["source_id"], "quote": quote}],
                "explanation": "原文区分了进程的资源分配职责与线程的调度执行职责。",
            }
            if request.type == "single_choice":
                exercise.update(
                    stem=[
                        "进程是哪一方面的基本单位？",
                        "调度和执行的基本单位是哪一个？",
                    ][index],
                    options=[
                        {"id": "A", "text": "资源分配" if index == 0 else "进程"},
                        {"id": "B", "text": "调度和执行" if index == 0 else "线程"},
                    ],
                    answer="A" if index == 0 else "B",
                )
            elif request.type == "boolean":
                exercise.update(
                    stem=["进程是资源分配的基本单位。", "线程是资源分配的基本单位。"][
                        index
                    ],
                    answer=index == 0,
                )
            else:
                exercise.update(
                    stem=[
                        "分别说明进程和线程的基本职责。",
                        "说明资源分配单位与执行单位之间的区别。",
                    ][index],
                    answer=quote,
                    rubric=[
                        {
                            "criterion": "正确区分进程和线程的职责",
                            "points": str(request.points),
                        }
                    ],
                )
            questions.append(exercise)
        output = {"status": "grounded", "reason": None, "questions": questions}
    result, status = build_candidates(
        CandidateOutput.model_validate_json(json.dumps(output)),
        envelope,
        sources,
        model="fixed-materialhub-demo",
        model_mode="demo",
    )
    result["prompt_version"] = DEMO_PROMPT_VERSION
    row = AIResult(
        user_id=user_id,
        course_id=course_id,
        query=request.goal,
        status=status,
        model_mode="demo",
        prompt_version=DEMO_PROMPT_VERSION,
        result_json=json.dumps(result, ensure_ascii=False),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
