"""Strict model output, separate from server-owned IDs and citations."""

from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .remote_ai import Evidence, Text

REQUEST_PREFIX = "hustudy:study-report:v1\n"
REPORT_PROMPT_VERSION = "zhipu-study-report-v2"
DEMO_REPORT_PROMPT_VERSION = "demo-study-report-v2"


class ReportPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    goal: Text = Field(default="理解所选资料，梳理知识点并完成自测", max_length=2000)
    version_ids: list[UUID] = Field(min_length=1, max_length=20)
    chunk_ids: list[UUID] = Field(default_factory=list, max_length=6)
    study_mode: Literal["preview", "systematic", "revision"] = "systematic"


class ReportEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    goal: Text = Field(max_length=2000)
    scope_version_ids: list[UUID] = Field(min_length=1, max_length=20)
    chunk_ids: list[UUID] = Field(default_factory=list, max_length=6)
    study_mode: Literal["preview", "systematic", "revision"]
    coverage: dict


def report_envelope(query: str) -> ReportEnvelope | None:
    if not query.startswith(REQUEST_PREFIX):
        return None
    return ReportEnvelope.model_validate_json(query[len(REQUEST_PREFIX) :])


class StrictOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ReportLabel(StrictOutput):
    kind: Literal["key", "difficult", "exam"]
    reason: Text = Field(max_length=1000)
    # Teacher/exam evidence is not connected in this slice.
    origin: Literal["ai_suggestion"]


class ConceptRelation(StrictOutput):
    target: Text = Field(max_length=200)
    relation: Text = Field(max_length=1000)


class ReportTopic(StrictOutput):
    name: Text = Field(max_length=200)
    explanation: Text = Field(max_length=3000)
    misconceptions: list[Text] = Field(max_length=8)
    labels: list[ReportLabel] = Field(min_length=1, max_length=3)
    evidence: list[Evidence] = Field(min_length=1, max_length=3)
    concept_group: Text | None = Field(default=None, max_length=200)
    related_concepts: list[ConceptRelation] = Field(default_factory=list, max_length=7)
    breakthrough_steps: list[Text] = Field(default_factory=list, max_length=8)


class ReportExercise(StrictOutput):
    question: Text = Field(max_length=1500)
    answer: Text = Field(max_length=2500)
    evidence: list[Evidence] = Field(min_length=1, max_length=3)


class TeachingReport(StrictOutput):
    summary: Text = Field(max_length=2000)
    learning_goals: list[Text] = Field(min_length=1, max_length=8)
    prerequisites: list[Text] = Field(max_length=8)
    learning_sequence: list[Text] = Field(min_length=1, max_length=8)
    topics: list[ReportTopic] = Field(min_length=1, max_length=8)
    examples: list[ReportExercise] = Field(min_length=1, max_length=3)
    self_checks: list[ReportExercise] = Field(min_length=3, max_length=5)
    evidence: list[Evidence] = Field(min_length=1, max_length=6)
    review_suggestions: list[Text] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def valid_relations(self):
        names = {topic.name for topic in self.topics}
        if len(names) != len(self.topics):
            raise ValueError("报告知识点名称不能重复")
        for topic in self.topics:
            targets = [item.target for item in topic.related_concepts]
            if len(set(targets)) != len(targets) or any(
                target not in names or target == topic.name for target in targets
            ):
                raise ValueError("概念关系必须指向本报告其他知识点且不能重复")
        return self


class ReportOutput(StrictOutput):
    status: Literal["grounded", "insufficient_evidence"]
    reason: Text | None = Field(max_length=1000)
    report: TeachingReport | None

    @model_validator(mode="after")
    def valid_status(self):
        if self.status == "grounded":
            if self.report is None or self.reason is not None:
                raise ValueError("成功报告必须有report且reason=null")
        elif self.report is not None or not self.reason:
            raise ValueError("证据不足必须有reason且report=null")
        return self
