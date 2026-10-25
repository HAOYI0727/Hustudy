"""Complete fixed teaching example. Unknown material explicitly exceeds demo capability."""

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from ..ai.study_reports import generate_report
from ..models import AIResult
from ..repositories.materials import active_version
from ..schemas.study_reports import (
    ReportEnvelope,
    ReportOutput,
    DEMO_REPORT_PROMPT_VERSION,
)
from .ai_context import select_report_context
from .courses import owned_course


class FixedReportProvider:
    settings = SimpleNamespace(llm_model="fixed-materialhub-demo")

    def __init__(self, supported):
        self.supported = supported

    def structured(self, query, sources, system_prompt, output_schema, max_tokens):
        quote = "进程是资源分配的基本单位，线程是调度和执行的基本单位。"
        source = next((s for s in sources if quote in s["text"]), None)
        if not self.supported or not source:
            return ReportOutput(
                status="insufficient_evidence",
                reason="固定报告演示仅支持自制materialhub_demo.md中进程与线程片段；未知资料或其它片段不模拟AI理解。",
                report=None,
            ), {}
        evidence = [{"source_id": source["source_id"], "quote": quote}]
        exercise = {
            "question": "资源分配的基本单位是什么？",
            "answer": "进程。",
            "evidence": evidence,
        }
        value = {
            "status": "grounded",
            "reason": None,
            "report": {
                "summary": "通过原文区分进程与线程的基本职责。",
                "learning_goals": ["区分资源分配与调度执行的基本单位"],
                "prerequisites": [],
                "learning_sequence": ["阅读定义", "比较职责", "完成自测"],
                "review_suggestions": [
                    "合上原文，分别说出资源分配与调度执行对应的单位，再对照原文核实。"
                ],
                "topics": [
                    {
                        "name": "进程与线程",
                        "explanation": quote,
                        "concept_group": "基础概念",
                        "breakthrough_steps": [
                            "先圈出原文的资源分配与调度执行。",
                            "分别对应进程和线程，再用自己的话说明区别。",
                        ],
                        "misconceptions": [
                            "不要把资源分配单位与调度执行单位混为一谈。"
                        ],
                        "labels": [
                            {
                                "kind": "key",
                                "origin": "ai_suggestion",
                                "reason": "原文直接对比两种单位，固定演示供核实。",
                            }
                        ],
                        "evidence": evidence,
                    }
                ],
                "examples": [exercise],
                "self_checks": [
                    exercise,
                    {
                        "question": "调度和执行的基本单位是什么？",
                        "answer": "线程。",
                        "evidence": evidence,
                    },
                    {
                        "question": "进程和线程的职责有何区别？",
                        "answer": quote,
                        "evidence": evidence,
                    },
                ],
                "evidence": evidence,
            },
        }
        return output_schema.model_validate_json(
            json.dumps(value, ensure_ascii=False)
        ), {}


def demo_report(db, user_id, course_id, request):
    if request.note_ids:
        from fastapi import HTTPException

        raise HTTPException(422, "固定演示不支持补充笔记，请使用真实预览")
    owned_course(db, user_id, course_id, lock=True)
    ids = list(dict.fromkeys(str(v) for v in request.version_ids))
    sources, coverage = select_report_context(
        db, user_id, course_id, ids, [str(c) for c in request.chunk_ids]
    )
    fixture = Path(__file__).resolve().parents[3] / "fixtures/materialhub_demo.md"
    supported = (
        len(ids) == 1
        and active_version(db, ids[0], user_id, course_id).sha256
        == hashlib.sha256(fixture.read_bytes()).hexdigest()
    )
    envelope = ReportEnvelope(
        goal=request.goal,
        scope_version_ids=ids,
        chunk_ids=request.chunk_ids,
        study_mode=request.study_mode,
        coverage=coverage,
    )
    result, status = generate_report(FixedReportProvider(supported), envelope, sources)
    result.update(
        prompt_version=DEMO_REPORT_PROMPT_VERSION,
        model_notice="演示模型 · 固定自制教学例，不执行AI推理，不根据任意目标理解资料",
    )
    if "study_report" in result:
        result["study_report"]["model_mode"] = "demo"
    row = AIResult(
        user_id=user_id,
        course_id=course_id,
        query=request.goal,
        status=status,
        model_mode="demo",
        prompt_version=DEMO_REPORT_PROMPT_VERSION,
        result_json=json.dumps(result, ensure_ascii=False),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
