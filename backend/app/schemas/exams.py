from datetime import date
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field


class TopicCreate(BaseModel):
    name: str = Field(min_length=1, max_length=240)
    aliases: List[str] = []


class TopicResponse(BaseModel):
    id: str
    name: str
    aliases: List[str]


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


class PastPaperResponse(BaseModel):
    id: str
    title: str
    year: Optional[int]
    review_status: str
    questions: List[PastQuestionResponse] = []


class QuestionTypeQuota(BaseModel):
    type: Literal["single_choice", "true_false", "short_answer"]
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


class ReviewTaskCreate(BaseModel):
    mistake_id: Optional[str] = None
    title: str = Field(min_length=1, max_length=240)
    due_date: date


class ReviewTaskResponse(BaseModel):
    id: str
    mistake_id: Optional[str]
    title: str
    due_date: str
    status: str


class FeedbackCreate(BaseModel):
    kind: str = Field(min_length=1, max_length=40)
    content: str = Field(min_length=1, max_length=5000)
    rating: Optional[int] = Field(default=None, ge=1, le=5)
