import json
import re
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..dependencies import current_user
from ..core.database import get_db
from ..models import AIResult, Course, Document, DocumentChunk, DocumentVersion, User
from ..schemas.ai import AIQueryRequest, AIResultResponse, StudyReportRequest, StudyReportResponse

router = APIRouter(prefix="/api/v1", tags=["ai"])


def _course(course_id: str, user: User, db: Session) -> Course:
    course = db.scalar(select(Course).where(Course.id == course_id, Course.user_id == user.id))
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    return course


def _chunks(course_id: str, user_id: str, db: Session, version_ids: list[str] | None = None):
    statement = select(DocumentChunk, DocumentVersion, Document).join(DocumentVersion, DocumentChunk.version_id == DocumentVersion.id).join(Document, DocumentVersion.document_id == Document.id).where(DocumentChunk.user_id == user_id, Document.course_id == course_id, Document.deleted_at.is_(None), DocumentVersion.index_status == "SUCCEEDED")
    if version_ids:
        statement = statement.where(DocumentVersion.id.in_(version_ids))
    return db.execute(statement).all()


def _rank(query: str, rows: list[Any]) -> list[Any]:
    terms = {term.lower() for term in re.findall(r"[A-Za-z0-9_]+", query) if len(term) > 1}
    for phrase in re.findall(r"[一-龥]{2,}", query):
        terms.add(phrase)
        terms.update(phrase[index:index + size] for size in (2, 3, 4) for index in range(max(0, len(phrase) - size + 1)))
    scored = []
    for row in rows:
        chunk = row[0]
        text = f"{chunk.locator_value}\n{chunk.text}".lower()
        score = sum(text.count(term) for term in terms)
        if score:
            scored.append((score, row))
    return [row for _score, row in sorted(scored, key=lambda item: item[0], reverse=True)[:5]]


def _citation(chunk: DocumentChunk, version: DocumentVersion) -> dict[str, Any]:
    return {"version_id": version.id, "chunk_id": chunk.id, "locator": {"type": chunk.locator_type, "value": chunk.locator_value}, "quote": chunk.text[:500], "availability": "active"}


def _save(user_id: str, course_id: str, query: str, status: str, mode: str, result: dict[str, Any], db: Session) -> AIResult:
    row = AIResult(user_id=user_id, course_id=course_id, query=query, result_json=json.dumps(result, ensure_ascii=False), status=status, model_mode=mode)
    db.add(row); db.commit(); db.refresh(row); return row


def _response(row: AIResult) -> AIResultResponse:
    return AIResultResponse(id=row.id, course_id=row.course_id, query=row.query, status=row.status, model_mode=row.model_mode, result=json.loads(row.result_json))


@router.post("/courses/{course_id}/ai-queries", response_model=AIResultResponse, status_code=201)
def query(course_id: str, payload: AIQueryRequest, user: User = Depends(current_user), db: Session = Depends(get_db)) -> AIResultResponse:
    _course(course_id, user, db)
    if payload.mode == "real":
        result = {"message": "真实模型尚未配置；请确认发送范围并配置服务端 Provider。", "citations": []}
        return _response(_save(user.id, course_id, payload.query, "provider_error", "real", result, db))
    ranked = _rank(payload.query, _chunks(course_id, user.id, db))
    if not ranked:
        result = {"message": "当前课程资料没有支持该问题的可检索证据。", "citations": [], "grounded": False}
        return _response(_save(user.id, course_id, payload.query, "insufficient_evidence", "demo", result, db))
    citations = [_citation(row[0], row[1]) for row in ranked]
    result = {"answer": f"演示模型根据当前课程资料整理：{ranked[0][0].text[:360]}", "grounded": True, "citations": citations, "model_notice": "演示模型；回答仅供学习辅助，需回看原文。"}
    return _response(_save(user.id, course_id, payload.query, "grounded", "demo", result, db))


@router.get("/ai-results/{result_id}", response_model=AIResultResponse)
def get_result(result_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> AIResultResponse:
    row = db.scalar(select(AIResult).where(AIResult.id == result_id, AIResult.user_id == user.id))
    if not row: raise HTTPException(status_code=404, detail="AI 结果不存在")
    return _response(row)


@router.post("/versions/{version_id}/study-reports", response_model=StudyReportResponse, status_code=201)
def study_report(version_id: str, payload: StudyReportRequest, user: User = Depends(current_user), db: Session = Depends(get_db)) -> StudyReportResponse:
    version = db.scalar(select(DocumentVersion).where(DocumentVersion.id == version_id, DocumentVersion.user_id == user.id))
    if not version: raise HTTPException(status_code=404, detail="资料版本不存在")
    document = db.get(Document, version.document_id)
    rows = _chunks(document.course_id, user.id, db, [version_id])
    citations = [_citation(row[0], row[1]) for row in rows[:5]]
    report = {"scope_version_ids": payload.scope_version_ids or [version_id], "learning_sequence": ["目标", "概念", "例子", "误区", "自测"], "summary": "演示模型报告；请结合引用原文审阅。", "topics": [{"topic_id": "demo-topic", "name": "资料中的核心概念", "explanation": rows[0][0].text[:240] if rows else "当前资料没有可提取文本", "origin": "ai_suggestion", "citations": citations}], "self_checks": ["用自己的话解释该概念。", "指出一个适用边界。"], "citations": citations}
    row = _save(user.id, document.course_id, "study-report:" + version_id, "grounded" if citations else "insufficient_evidence", "demo", report, db)
    return StudyReportResponse(id=row.id, status=row.status, model_mode=row.model_mode, report=report)
