from datetime import date
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator
from uuid import UUID


class TopicCreate(BaseModel):
    parent_id: UUID | None = None
    name: str = Field(min_length=1, max_length=240)
    aliases: List[str] = []


class TopicResponse(BaseModel):
    parent_id: str | None = None
    id: str
    name: str
    aliases: List[str]
    revision: int = 1
    merged_into_id: str | None = None


class PastPaperCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    year: Optional[int] = None
    content: str = ""


class PastQuestionResponse(BaseModel):
    id: str
    number: str
    stem: str
    question_type: str
    points: Optional[int]
    answer: Optional[str]
    answer_source: str
    status: str
    topic_id: Optional[str]
    revision: int = 1
    bank_data: Dict[str, Any] = Field(default_factory=dict)


class PastPaperResponse(BaseModel):
    id: str
    title: str
    year: Optional[int]
    review_status: str
    questions: List[PastQuestionResponse] = []


class QuestionTypeQuota(BaseModel):
    @field_validator("type", mode="before")
    @classmethod
    def retire_fill(cls, value):
        return "solution" if value == "fill_blank" else value

    type: Literal["single_choice", "true_false", "short_answer", "solution"]
    count: int = Field(ge=0, le=100, strict=True)
    points: int = Field(gt=0, le=500, strict=True)
    difficulty: str = Field(default="基础", max_length=40)


class ChapterQuota(BaseModel):
    name: str = Field(min_length=1, max_length=240)
    count: int = Field(ge=0, le=100, strict=True)


class BlueprintCreate(BaseModel):
    name: str = Field(min_length=1, max_length=240)
    mode: Literal["history_blueprint", "topic_variant", "weakness_practice"] = (
        "history_blueprint"
    )
    total_points: int = Field(gt=0, le=500)
    duration_minutes: int = Field(gt=0, le=180)
    question_types: List[QuestionTypeQuota] = Field(min_length=1, max_length=3)
    topics: List[ChapterQuota] = Field(default_factory=list, max_length=100)


class BlueprintResponse(BaseModel):
    id: str
    name: str
    config: Dict[str, Any]
    status: str


class PaperResponse(BaseModel):
    id: str
    title: str
    mode: str
    status: str
    questions: List[Dict[str, Any]]


class AnswerRequest(BaseModel):
    answer: Any


class AttemptResponse(BaseModel):
    id: str
    paper_id: str
    status: str
    answers: Dict[str, Any]
    score: Optional[int]
    grading: Dict[str, Any] = Field(default_factory=dict)
    deadline_at: Optional[str] = None


class ReviewTaskCreate(BaseModel):
    mistake_id: Optional[str] = None
    title: str = Field(min_length=1, max_length=240)
    due_date: date | None = None


class ReviewTaskResponse(BaseModel):
    id: str
    mistake_id: Optional[str]
    title: str
    due_date: str
    status: str


class ReviewReschedule(BaseModel):
    due_date: date
    expected_due_date: date


class FeedbackCreate(BaseModel):
    kind: str = Field(min_length=1, max_length=40)
    content: str = Field(min_length=1, max_length=5000)
    rating: Optional[int] = Field(default=None, ge=1, le=5)


class BankImport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID | None = None
    strict_markdown: bool = False
    title: str = Field(min_length=1, max_length=240)
    content: str = Field(default="", max_length=240000)
    version_id: UUID | None = None
    year: int | None = Field(default=None, ge=1900, le=2200)
    provenance: str = Field(default="用户提供", max_length=500)
    variant: str = Field(default="", max_length=80)
    default_topic_ids: list[UUID] = Field(default_factory=list, max_length=5)


class TopicEdit(BaseModel):
    parent_id: UUID | None = None
    revision: int = Field(ge=1, strict=True)
    name: str = Field(min_length=1, max_length=240)
    aliases: list[str] = Field(default_factory=list, max_length=30)


class TopicMerge(BaseModel):
    revision: int = Field(ge=1, strict=True)
    target_id: UUID
    target_revision: int = Field(ge=1, strict=True)


class TopicSourceEdit(BaseModel):
    revision: int = Field(ge=1, strict=True)
    version_id: UUID
    chunk_id: UUID
    quote: str = Field(min_length=1, max_length=1000)


class BankSplit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=1, strict=True)
    parts: list[str] = Field(min_length=2, max_length=20)


class BankMerge(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question_ids: list[UUID] = Field(min_length=2, max_length=20)
    revisions: dict[str, int]
    stem: str = Field(min_length=1, max_length=20000)


class ExamIdentityInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["exercise", "past_exam"]
    confirmed: bool = Field(strict=True)


class BankMetadataEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(default=1, ge=1, strict=True)
    year: int | None = Field(default=None, ge=1900, le=2200, strict=True)
    variant: str = Field(default="", max_length=80)
    provenance: str = Field(default="用户提供", max_length=500)
    duplicate_of: UUID | None = None
    exam_identity: ExamIdentityInput | None = None


class BankMetadataBatchItem(BankMetadataEdit):
    paper_id: UUID
    expected_revision: int = Field(ge=1, strict=True)


class BankMetadataBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[BankMetadataBatchItem] = Field(min_length=1, max_length=100)


class BankQuestionEdit(BaseModel):
    @field_validator("question_type", mode="before")
    @classmethod
    def retire_fill(cls, value):
        return "solution" if value == "fill_blank" else value

    model_config = ConfigDict(extra="forbid")
    year: int | None = Field(default=None, ge=1900, le=2200, strict=True)
    revision: int = Field(ge=1, strict=True)
    stem: str = Field(min_length=1, max_length=20000)
    question_type: Literal["single_choice", "solution"]
    options: list[str] = Field(default_factory=list, max_length=4)
    answer: str | None = Field(default=None, max_length=20000)
    blank_answers: list[str] = Field(default_factory=list, max_length=30)
    unique_answer: bool | None = None
    topic_ids: list[UUID] = Field(default_factory=list, max_length=5)
    points: int | None = Field(default=None, gt=0, le=500, strict=True)
    explanation: str = Field(default="", max_length=20000)
    illustrations: list[dict] | None = Field(default=None, max_length=8)
    images_reviewed: bool = False


class BankSaveItem(BankQuestionEdit):
    question_id: UUID


class BankSave(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[BankSaveItem] = Field(min_length=1, max_length=100)


class BankBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question_ids: list[UUID] = Field(min_length=1, max_length=100)
    revisions: dict[str, int]
    action: Literal["delete", "tag", "tag_add", "confirm", "review_topics"]
    topic_ids: list[UUID] = Field(default_factory=list, max_length=5)


class BankValuesBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question_ids: list[UUID] = Field(min_length=1, max_length=100)
    revisions: dict[str, int]
    year: int | None = Field(default=None, ge=1900, le=2200, strict=True)
    points: int | None = Field(default=None, gt=0, le=500, strict=True)


class BankImageImport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    title: str = Field(min_length=1, max_length=240)
    asset_ids: list[UUID] = Field(min_length=1, max_length=20)
    layout: Literal["single", "double"] = "single"
    engine: Literal["local", "ai"] = "local"
    confirm_remote_send: bool = False
    questions_only: bool = False
    classify_topics: bool = False
    year: int | None = Field(default=None, ge=1900, le=2200)
    default_topic_ids: list[UUID] = Field(default_factory=list, max_length=5)


class BankDraw(BaseModel):
    @field_validator("question_type", mode="before")
    @classmethod
    def retire_fill(cls, value):
        return "solution" if value == "fill_blank" else value

    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    topic_ids: list[UUID] = Field(default_factory=list)
    count: int = Field(default=5, ge=1, le=100, strict=True)
    question_type: Literal["single_choice", "solution"] | None = None
    duration_minutes: int = Field(default=30, ge=1, le=180, strict=True)
    title: str = Field(default="题库随机练习", min_length=1, max_length=240)


class BankWholePaperPractice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    duration_minutes: int = Field(default=90, ge=1, le=180, strict=True)


class SelfGrade(BaseModel):
    model_config = ConfigDict(extra="forbid")
    correct: bool | None = Field(default=None, strict=True)
    score: int | None = Field(default=None, ge=0, le=500, strict=True)
