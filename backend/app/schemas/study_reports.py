"""Strict model output, separate from server-owned IDs and citations."""

from typing import ClassVar, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator
from pydantic_core import PydanticCustomError
from .remote_ai import Evidence, ExcerptReference, Text
from .ai_supplements import SupplementSelection

REQUEST_PREFIX = "hustudy:study-report:v1\n"
REPORT_PROMPT_VERSION = "zhipu-study-report-v11"
DEMO_REPORT_PROMPT_VERSION = "demo-study-report-v2"


class ReportPreviewRequest(SupplementSelection):
    model_config = ConfigDict(extra="forbid")
    max_structure_repairs: int = Field(default=0, ge=0, le=2, strict=True)
    goal: Text = Field(default="理解所选资料，梳理知识点并完成自测", max_length=2000)
    version_ids: list[UUID] = Field(min_length=1, max_length=20)
    chunk_ids: list[UUID] = Field(default_factory=list, max_length=400)
    study_mode: Literal["preview", "systematic", "revision"] = "systematic"


class ReportEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    goal: Text = Field(max_length=2000)
    scope_version_ids: list[UUID] = Field(min_length=1, max_length=20)
    chunk_ids: list[UUID] = Field(default_factory=list, max_length=400)
    batched: bool = False
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
    # Model output only. Trusted teacher/exam labels are attached by the server.
    origin: Literal["ai_suggestion"]


class ConceptRelation(StrictOutput):
    target: Text = Field(max_length=200)
    relation: Text = Field(max_length=3000)


class ReportTopic(StrictOutput):
    name: Text = Field(max_length=200)
    explanation: Text = Field(max_length=12000)
    misconceptions: list[Text] = Field(max_length=32)
    labels: list[ReportLabel] = Field(min_length=1, max_length=3)
    evidence: list[ExcerptReference | Evidence] = Field(min_length=1, max_length=64)
    concept_group: Text | None = Field(default=None, max_length=200)
    related_concepts: list[ConceptRelation] = Field(default_factory=list, max_length=32)
    breakthrough_steps: list[Text] = Field(default_factory=list, max_length=32)


class ReportExercise(StrictOutput):
    question: Text = Field(max_length=6000)
    answer: Text = Field(max_length=12000)
    evidence: list[ExcerptReference | Evidence] = Field(min_length=1, max_length=64)


class TeachingReport(StrictOutput):
    _removed_relation_count: int = PrivateAttr(default=0)
    summary: Text = Field(max_length=8000)
    learning_goals: list[Text] = Field(min_length=1, max_length=32)
    prerequisites: list[Text] = Field(max_length=32)
    learning_sequence: list[Text] = Field(min_length=1, max_length=64)
    topics: list[ReportTopic] = Field(min_length=1, max_length=32)
    examples: list[ReportExercise] = Field(min_length=1, max_length=12)
    self_checks: list[ReportExercise] = Field(min_length=3, max_length=5)
    evidence: list[ExcerptReference | Evidence] = Field(min_length=1, max_length=64)
    review_suggestions: list[Text] = Field(default_factory=list, max_length=32)

    @model_validator(mode="after")
    def valid_relations(self):
        names = {topic.name for topic in self.topics}
        if len(names) != len(self.topics):
            raise PydanticCustomError("report_duplicate_topics", "报告知识点名称重复")
        for topic in self.topics:
            targets, valid = set(), []
            for item in topic.related_concepts:
                if (
                    item.target in names
                    and item.target != topic.name
                    and item.target not in targets
                ):
                    valid.append(item)
                    targets.add(item.target)
                else:
                    self._removed_relation_count += 1
            topic.related_concepts = valid
        return self


class ReportOutput(StrictOutput):
    status: Literal["grounded", "insufficient_evidence"]
    reason: Text | None = Field(max_length=1000)
    report: TeachingReport | None

    @model_validator(mode="after")
    def valid_status(self):
        if self.status == "grounded":
            if self.report is None or self.reason is not None:
                raise PydanticCustomError(
                    "report_status_mismatch", "报告状态与内容不一致"
                )
        elif self.report is not None or not self.reason:
            raise PydanticCustomError("report_status_mismatch", "报告状态与内容不一致")
        return self


class DraftSelfCheck(ReportExercise):
    evidence: list[ExcerptReference | Evidence] = Field(
        default_factory=list, max_length=64
    )


class DraftTeachingReport(TeachingReport):
    self_checks: list[DraftSelfCheck] = Field(min_length=3, max_length=5)


class ReportGenerationOutput(ReportOutput):
    """Only self-check evidence may be absent before explicit local replacement."""

    report: DraftTeachingReport | None
    diagnostic_labels: ClassVar[dict[str, str]] = {
        "report": "报告",
        "learning_sequence": "学习步骤",
        "learning_goals": "学习目标",
        "prerequisites": "前置知识",
        "topics": "知识点",
        "evidence": "依据引用",
        "self_checks": "自测题",
        "examples": "例题",
        "summary": "概述",
        "explanation": "概念讲解",
        "answer": "答案",
        "question": "问题",
        "misconceptions": "易错点",
        "breakthrough_steps": "难点步骤",
        "related_concepts": "概念关系",
        "review_suggestions": "复习建议",
    }
