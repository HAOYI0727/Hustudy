from typing import Optional
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, OwnedResourceMixin


class Topic(Base, OwnedResourceMixin):
    __tablename__ = "topics"
    course_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    aliases_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    merged_into_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    sources_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)


class ExamAnalysisReport(Base, OwnedResourceMixin):
    __tablename__ = "exam_analysis_reports"
    course_id: Mapped[str] = mapped_column(String(36), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    report_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="READY", nullable=False)


class PastPaper(Base, OwnedResourceMixin):
    __tablename__ = "past_papers"
    course_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    bank_meta_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    review_status: Mapped[str] = mapped_column(
        String(32), default="DRAFT", nullable=False
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


class PastQuestion(Base, OwnedResourceMixin):
    __tablename__ = "past_questions"
    paper_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("past_papers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    number: Mapped[str] = mapped_column(String(40), nullable=False)
    stem: Mapped[str] = mapped_column(Text, nullable=False)
    bank_data_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    question_type: Mapped[str] = mapped_column(
        String(32), default="short_answer", nullable=False
    )
    points: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    answer_source: Mapped[str] = mapped_column(
        String(24), default="unknown", nullable=False
    )
    status: Mapped[str] = mapped_column(String(24), default="DRAFT", nullable=False)
    topic_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("topics.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )


class ExamBlueprint(Base, OwnedResourceMixin):
    __tablename__ = "exam_blueprints"
    course_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    config_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="DRAFT", nullable=False)


class ExamPaper(Base, OwnedResourceMixin):
    __tablename__ = "exam_papers"
    course_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    blueprint_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("exam_blueprints.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    mode: Mapped[str] = mapped_column(
        String(40), default="history_blueprint", nullable=False
    )
    status: Mapped[str] = mapped_column(String(24), default="DRAFT", nullable=False)
    questions_json: Mapped[str] = mapped_column(Text, nullable=False)


class ExamAttempt(Base, OwnedResourceMixin):
    __tablename__ = "exam_attempts"
    paper_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("exam_papers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(24), default="IN_PROGRESS", nullable=False
    )
    answers_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    snapshot_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    grading_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class Mistake(Base, OwnedResourceMixin):
    __tablename__ = "mistakes"
    attempt_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("exam_attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[str] = mapped_column(String(36), nullable=False)
    detail_json: Mapped[str] = mapped_column(Text, nullable=False)


class ReviewTask(Base, OwnedResourceMixin):
    __tablename__ = "review_tasks"
    course_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("courses.id", ondelete="CASCADE"), nullable=True, index=True
    )
    mistake_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("mistakes.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    due_date: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="PENDING", nullable=False)


class Feedback(Base, OwnedResourceMixin):
    __tablename__ = "feedback"
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
