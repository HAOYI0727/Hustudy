"""M4 snapshot/restore boundary preserves paper and attempt snapshots."""

from ..core import backup_contract as contract
from ..models import (
    Topic,
    PastPaper,
    PastQuestion,
    ExamBlueprint,
    ExamPaper,
    ExamAttempt,
    Mistake,
    ReviewTask,
    Feedback,
)

MODELS = [
    Topic,
    PastPaper,
    PastQuestion,
    ExamBlueprint,
    ExamPaper,
    ExamAttempt,
    Mistake,
    ReviewTask,
    Feedback,
]


def snapshot(db, user_id):
    return contract.serialize(db, user_id, MODELS), []


def empty(db, user_id):
    contract.assert_empty(db, user_id, MODELS)


def validate(db, user_id, source_user, tables, all_ids, paths):
    return contract.validate(db, user_id, source_user, MODELS, tables, all_ids, paths)


def apply(db, decoded):
    contract.apply(db, MODELS, decoded)
