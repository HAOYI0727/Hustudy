"""Whitelisted learning metadata; no question answers or note bodies."""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class TopicMetadata(BaseModel):
    id: str
    name: str
    aliases: list[str]
    parent_id: str | None
    revision: int


class LearningCounts(BaseModel):
    confirmed: int = Field(ge=0)
    pending: int = Field(ge=0)
    needs_review: int = Field(ge=0)


class LearningTopic(TopicMetadata, LearningCounts):
    pass


class LearningDirectory(BaseModel):
    course_id: str
    items: list[LearningTopic]
    total: int
    offset: int
    limit: int
    checked_at: datetime


class SourceReference(BaseModel):
    version_id: str
    chunk_id: str


class SourceCandidate(SourceReference):
    document_id: str
    title: str
    version_no: int
    locator: str
    quote: str


class ActiveSource(SourceCandidate):
    availability: Literal["active"]


class UnavailableSource(SourceReference):
    availability: Literal["unavailable"]


class RelatedNote(BaseModel):
    id: str
    title: str
    updated_at: datetime
    relation: Literal["shared_source", "same_tag_candidate"]


class LearningMistake(BaseModel):
    id: str
    updated_at: datetime


class LearningReview(BaseModel):
    id: str
    title: str
    due_date: str
    mistake_id: str


class LearningDetail(BaseModel):
    course_id: str
    topic: TopicMetadata
    counts: LearningCounts
    sources: list[ActiveSource | UnavailableSource]
    candidates: list[SourceCandidate]
    notes: list[RelatedNote]
    mistakes: list[LearningMistake]
    reviews: list[LearningReview]
    review_total: int
    today: str
    timezone: str
    checked_at: datetime
