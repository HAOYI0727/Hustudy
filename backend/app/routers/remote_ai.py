from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..dependencies import current_user
from ..models import User
from ..schemas.remote_ai import PreviewRequest, ConsentRequest, RemoteQueryResponse
from ..schemas.remote_ai import ReuseRequest
from ..schemas.remote_ai import RelatedReuseRequest
from ..services import remote_ai
from ..schemas.study_reports import (
    ReportPreviewRequest,
    REPORT_PROMPT_VERSION,
    DEMO_REPORT_PROMPT_VERSION,
)
from ..schemas.ai import AIResultResponse
from ..models import AIResult
from ..services.courses import owned_course
from sqlalchemy import select
from fastapi import HTTPException
from ..schemas.question_drafts import (
    CandidateRequest,
    CANDIDATE_PROMPT_VERSION,
    DEMO_PROMPT_VERSION,
)
from ..services.exam_ai_context import candidate_context
from ..ai.providers import PROMPT_VERSION

router = APIRouter(prefix="/api/v1", tags=["ai"])


@router.get("/remote-queries/{query_id}/related-results/{result_id}", response_model=AIResultResponse)
def view_related_answer(
    query_id: str, result_id: str,
    user: User = Depends(current_user), db: Session = Depends(get_db),
):
    from ..services.related_answers import related_answer

    return related_answer(db, user.id, query_id, result_id)


@router.post("/remote-queries/{query_id}/related-results/{result_id}/reuse", response_model=AIResultResponse)
def use_related_answer(
    query_id: str, result_id: str, payload: RelatedReuseRequest,
    user: User = Depends(current_user), db: Session = Depends(get_db),
):
    from ..services.related_answers import related_answer

    return related_answer(db, user.id, query_id, result_id)


@router.post("/remote-queries/{query_id}/reuse", response_model=AIResultResponse)
def reuse_result(
    query_id: str,
    payload: ReuseRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from ..services.ai_result_reuse import reuse

    return reuse(db, user.id, query_id, str(payload.result_id))


@router.post(
    "/courses/{course_id}/study-reports/demo",
    response_model=AIResultResponse,
    status_code=201,
)
def demo_report(
    course_id: str,
    payload: ReportPreviewRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from ..services.study_report_demo import demo_report as generate_demo

    return remote_ai.validated_result(
        db, generate_demo(db, user.id, course_id, payload)
    )


@router.get("/courses/{course_id}/question-draft-context")
def draft_context(
    course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return candidate_context(db, user.id, course_id)


@router.post(
    "/courses/{course_id}/question-drafts/preview",
    response_model=RemoteQueryResponse,
    status_code=201,
)
def preview_candidates(
    course_id: str,
    payload: CandidateRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    owned_course(db, user.id, course_id)
    raise HTTPException(410, "练习题已改为用户题库随机抽题，请使用question-bank/draw")


@router.post(
    "/courses/{course_id}/question-drafts/demo",
    response_model=AIResultResponse,
    status_code=201,
)
def demo_candidates(
    course_id: str,
    payload: CandidateRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    owned_course(db, user.id, course_id)
    raise HTTPException(410, "练习题已改为用户题库随机抽题；历史候选仍可查看")


@router.get(
    "/courses/{course_id}/question-drafts", response_model=list[AIResultResponse]
)
def candidate_history(
    course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    owned_course(db, user.id, course_id)
    rows = db.scalars(
        select(AIResult)
        .where(
            AIResult.user_id == user.id,
            AIResult.course_id == course_id,
            AIResult.prompt_version.in_(
                [
                    CANDIDATE_PROMPT_VERSION,
                    DEMO_PROMPT_VERSION,
                    "zhipu-question-drafts-v1",
                    "zhipu-question-drafts-v2",
                    "zhipu-question-drafts-v3",
                    "zhipu-question-drafts-v4",
                ]
            ),
        )
        .order_by(AIResult.created_at.desc(), AIResult.id.desc())
        .limit(20)
    )
    return [remote_ai.validated_result(db, row) for row in rows]


@router.get("/question-drafts/{result_id}", response_model=AIResultResponse)
def saved_candidates(
    result_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    row = db.scalar(
        select(AIResult).where(
            AIResult.id == result_id,
            AIResult.user_id == user.id,
            AIResult.prompt_version.in_(
                [
                    CANDIDATE_PROMPT_VERSION,
                    DEMO_PROMPT_VERSION,
                    "zhipu-question-drafts-v1",
                    "zhipu-question-drafts-v2",
                    "zhipu-question-drafts-v3",
                    "zhipu-question-drafts-v4",
                ]
            ),
        )
    )
    if row is None:
        raise HTTPException(404, "候选结果不存在")
    owned_course(db, user.id, row.course_id)
    return remote_ai.validated_result(db, row)


@router.get("/courses/{course_id}/ai-results", response_model=list[AIResultResponse])
def query_history(
    course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    owned_course(db, user.id, course_id)
    rows = db.scalars(
        select(AIResult)
        .where(
            AIResult.user_id == user.id,
            AIResult.course_id == course_id,
            AIResult.prompt_version.in_(
                [
                    PROMPT_VERSION,
                    "zhipu-grounded-qa-v4",
                    "zhipu-grounded-qa-v3",
                    "zhipu-grounded-qa-v2",
                    "zhipu-grounded-qa-v1",
                    "mock-v1",
                ]
            ),
            ~AIResult.query.startswith("study-report:"),
        )
        .order_by(AIResult.created_at.desc(), AIResult.id.desc())
        .limit(20)
    )
    return [remote_ai.validated_result(db, row) for row in rows]


@router.post(
    "/courses/{course_id}/study-reports/preview",
    response_model=RemoteQueryResponse,
    status_code=201,
)
def preview_report(
    course_id: str,
    payload: ReportPreviewRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return remote_ai.preview(
        db,
        user.id,
        course_id,
        PreviewRequest(query=payload.goal, version_ids=payload.version_ids),
        report_request=payload,
    )


@router.get("/courses/{course_id}/study-reports", response_model=list[AIResultResponse])
def report_history(
    course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    owned_course(db, user.id, course_id)
    rows = db.scalars(
        select(AIResult)
        .where(
            AIResult.user_id == user.id,
            AIResult.course_id == course_id,
            AIResult.prompt_version.in_(
                [
                    REPORT_PROMPT_VERSION,
                    DEMO_REPORT_PROMPT_VERSION,
                    "zhipu-study-report-v1",
                    "zhipu-study-report-v2",
                    "zhipu-study-report-v3",
                    "zhipu-study-report-v4",
                    "zhipu-study-report-v5",
                    "zhipu-study-report-v6",
                    "zhipu-study-report-v7",
                    "zhipu-study-report-v8",
                    "zhipu-study-report-v9",
                    "zhipu-study-report-v10",
                ]
            ),
        )
        .order_by(AIResult.created_at.desc(), AIResult.id.desc())
        .limit(20)
    )
    return [remote_ai.validated_result(db, row) for row in rows]


@router.get("/study-reports/{result_id}", response_model=AIResultResponse)
def saved_report(
    result_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    row = db.scalar(
        select(AIResult).where(
            AIResult.id == result_id,
            AIResult.user_id == user.id,
            AIResult.prompt_version.in_(
                [
                    REPORT_PROMPT_VERSION,
                    DEMO_REPORT_PROMPT_VERSION,
                    "zhipu-study-report-v1",
                    "zhipu-study-report-v2",
                    "zhipu-study-report-v3",
                    "zhipu-study-report-v4",
                    "zhipu-study-report-v5",
                    "zhipu-study-report-v6",
                    "zhipu-study-report-v7",
                    "zhipu-study-report-v8",
                    "zhipu-study-report-v9",
                    "zhipu-study-report-v10",
                ]
            ),
        )
    )
    if row is None:
        raise HTTPException(404, "学习报告不存在")
    owned_course(db, user.id, row.course_id)
    return remote_ai.validated_result(db, row)


@router.get("/ai/provider")
def provider(user: User = Depends(current_user)):
    return remote_ai.provider_status(user.id)


@router.post(
    "/courses/{course_id}/remote-queries/preview",
    response_model=RemoteQueryResponse,
    status_code=201,
)
def preview(
    course_id: str,
    payload: PreviewRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return remote_ai.preview(db, user.id, course_id, payload)


@router.post(
    "/remote-queries/{query_id}/confirm",
    response_model=RemoteQueryResponse,
    status_code=202,
)
def confirm(
    query_id: str,
    payload: ConsentRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return remote_ai.confirm(db, user.id, query_id)


@router.get("/remote-queries/{query_id}", response_model=RemoteQueryResponse)
def get_query(
    query_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return remote_ai.response(db, remote_ai.owned_query(db, user.id, query_id))


@router.post("/remote-queries/{query_id}/cancel", response_model=RemoteQueryResponse)
def cancel(
    query_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return remote_ai.cancel(db, user.id, query_id)


@router.post(
    "/remote-queries/{query_id}/resume",
    response_model=RemoteQueryResponse,
    status_code=202,
)
def resume_report(
    query_id: str,
    payload: ConsentRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from ..services.report_batches import resume

    row = remote_ai.owned_query(db, user.id, query_id)
    from ..services import qa_batches

    return qa_batches.resume(db, row) if qa_batches.batched(row) else resume(db, row)
