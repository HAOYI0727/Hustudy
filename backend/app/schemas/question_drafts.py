"""M2 candidate contract. No exam paper or attempt state is accepted from a model."""

from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from .remote_ai import Text, Evidence, ExcerptReference

CANDIDATE_PREFIX = "hustudy:question-drafts:v1\n"
CANDIDATE_PROMPT_VERSION = "zhipu-question-drafts-v5"
DEMO_PROMPT_VERSION = "demo-question-drafts-v1"
Money = Annotated[
    Decimal, Field(gt=0, le=100, max_digits=5, decimal_places=2, allow_inf_nan=False)
]


class CandidateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    goal: Text = Field(default="依据所选资料生成练习候选题", max_length=1000)
    version_ids: list[UUID] = Field(min_length=1, max_length=20)
    chunk_ids: list[UUID] = Field(default_factory=list, max_length=128)
    chapter_id: UUID
    topic_ids: list[UUID] = Field(min_length=1, max_length=4)
    type: Literal["single_choice", "boolean", "short_answer"] = "single_choice"
    count: int = Field(default=1, ge=1, le=6, strict=True)
    points: Money = Decimal("5")
    difficulty_label: Literal["basic", "application", "advanced"] = "basic"
    mode: Literal["historical", "variant", "weakness"] = "historical"
    original_past_question_ids: list[UUID] = Field(default_factory=list, max_length=6)

    @field_validator("type", mode="before")
    @classmethod
    def normalize_type(cls, value):
        return "boolean" if value == "true_false" else value

    @field_validator("mode", mode="before")
    @classmethod
    def normalize_mode(cls, value):
        return (
            {
                "history_blueprint": "historical",
                "topic_variant": "variant",
                "weakness_practice": "weakness",
            }.get(value, value)
            if isinstance(value, str)
            else value
        )

    @model_validator(mode="after")
    def valid_scope(self):
        if self.chapter_id not in self.version_ids:
            raise ValueError("章节范围必须是选定资料版本，接入正式蓝图需由M4映射")
        for values in (
            self.version_ids,
            self.chunk_ids,
            self.topic_ids,
            self.original_past_question_ids,
        ):
            if len(set(values)) != len(values):
                raise ValueError("范围ID不能重复")
        if self.mode == "variant" and not self.original_past_question_ids:
            raise ValueError("同考点变式必须选择已确认原题")
        return self


class CandidateEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    per_question_topics: bool = False
    request: CandidateRequest
    coverage: dict
    exam_context: dict


def candidate_envelope(query: str) -> CandidateEnvelope | None:
    if not query.startswith(CANDIDATE_PREFIX):
        return None
    return CandidateEnvelope.model_validate_json(query[len(CANDIDATE_PREFIX) :])


class Option(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: Text = Field(max_length=8)
    text: Text = Field(max_length=1000)


class RubricItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    criterion: Text = Field(max_length=1000)
    points: Money


class ModelQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    topic_ids: list[UUID] = Field(default_factory=list, max_length=4)
    stem: Text = Field(max_length=8000)
    options: list[Option] = Field(max_length=6)
    answer: str | bool | None
    rubric: list[RubricItem] = Field(max_length=12)
    explanation: Text = Field(max_length=3000)
    evidence: list[ExcerptReference | Evidence] = Field(min_length=1, max_length=4)
    original_past_question_ids: list[UUID] = Field(max_length=6)


class CandidateOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    status: Literal["grounded", "insufficient_evidence"]
    reason: Text | None = Field(max_length=1000)
    questions: list[ModelQuestion] = Field(max_length=6)

    @model_validator(mode="after")
    def consistent(self):
        if self.status == "grounded":
            if not self.questions or self.reason is not None:
                raise ValueError("成功须有候选且reason=null")
        elif self.questions or not self.reason:
            raise ValueError("证据不足须无候选且有原因")
        return self


class DraftLocator(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["slide", "page", "heading", "docx_block"]
    value: str


class DraftCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: UUID
    version_id: UUID
    chunk_id: UUID
    locator: DraftLocator
    quote: Text = Field(max_length=500)
    quote_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    availability: Literal["active", "unavailable"]
    source_kind: Literal["extracted", "manual_transcript"]
    start_offset: int = Field(ge=0)
    end_offset: int = Field(gt=0)


class DraftRubric(BaseModel):
    model_config = ConfigDict(extra="forbid")
    criterion: Text = Field(max_length=1000)
    points: float = Field(gt=0, le=100, multiple_of=0.01, allow_inf_nan=False)


class QuestionDraft(BaseModel):
    """Public import contract for M4; final exam acceptance remains its responsibility."""

    model_config = ConfigDict(extra="forbid")
    question_id: UUID
    chapter_id: UUID
    type: Literal["single_choice", "boolean", "short_answer"]
    stem: Text = Field(max_length=8000)
    options: list[Option] = Field(max_length=6)
    answer: str | bool | None
    rubric: list[DraftRubric] = Field(max_length=12)
    points: float = Field(gt=0, le=100, multiple_of=0.01, allow_inf_nan=False)
    explanation: Text = Field(max_length=3000)
    topic_ids: list[UUID] = Field(min_length=1, max_length=4)
    difficulty_label: Literal["basic", "application", "advanced"]
    mode: Literal["historical", "variant", "weakness"]
    original_past_question_ids: list[UUID] = Field(max_length=6)
    material_citations: list[DraftCitation] = Field(min_length=1, max_length=4)
    generation_status: Literal["draft"]
