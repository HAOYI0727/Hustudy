from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from .ai import AIResultResponse
from .material import JobResponse
from .ai_supplements import SupplementSelection

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class PreviewRequest(SupplementSelection):
    model_config = ConfigDict(extra="forbid")
    max_structure_repairs: int = Field(default=0, ge=0, le=2, strict=True)
    query: Text = Field(max_length=2000)
    version_ids: list[UUID] = Field(default_factory=list, max_length=20)
    chunk_ids: list[UUID] = Field(default_factory=list, max_length=400)


class ConsentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirm_remote_send: bool = Field(strict=True)

    @model_validator(mode="after")
    def explicit_consent(self):
        if self.confirm_remote_send is not True:
            raise ValueError("必须明确确认发送")
        return self


class ReuseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    result_id: UUID


class RelatedReuseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirm_related_reuse: Literal[True]

    @model_validator(mode="before")
    @classmethod
    def strict_confirmation(cls, value):
        if not isinstance(value, dict) or value.get("confirm_related_reuse") is not True:
            raise ValueError("须明确确认原问题或学习目标及原结果适用于本次需求")
        return value


class RelatedAnswer(BaseModel):
    id: str
    query: str
    answer_preview: str
    model: str
    created_at: datetime


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: UUID
    quote: Text = Field(max_length=500)


class ExcerptReference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    excerpt_id: str = Field(pattern=r"^E[1-9][0-9]{0,2}$")


class GroundedAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    status: Literal["grounded", "insufficient_evidence"]
    answer: Text = Field(max_length=8000)
    evidence: list[ExcerptReference | Evidence] = Field(max_length=32)

    @model_validator(mode="after")
    def valid_status(self):
        if (self.status == "grounded") != bool(self.evidence):
            raise ValueError("grounded必须有证据，证据不足不能添加引用")
        return self


class RemoteQueryResponse(BaseModel):
    id: str
    course_id: str
    query: str
    request_kind: Literal["qa", "study_report", "question_drafts"] = "qa"
    report_scope: dict | None = None
    qa_scope: dict | None = None
    candidate_scope: dict | None = None
    batch_progress: dict | None = None
    model: str
    endpoint: str
    expires_at: datetime
    consented_at: datetime | None
    dispatched_at: datetime | None
    sources: list[dict]
    job: JobResponse | None
    result: AIResultResponse | None
    reusable_result: AIResultResponse | None = None
    related_results: list[RelatedAnswer] = Field(default_factory=list, max_length=3)
    execution: dict | None = None
