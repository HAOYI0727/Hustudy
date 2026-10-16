"""M3 snapshot/restore boundary; account coordinator never reads note tables."""

from ..core import backup_contract as contract
from ..models import Note, NoteLink, Citation, AssetReference

MODELS = [Note, NoteLink, Citation, AssetReference]


def snapshot(db, user_id):
    return contract.serialize(db, user_id, MODELS), []


def empty(db, user_id):
    contract.assert_empty(db, user_id, MODELS)


def validate(db, user_id, source_user, tables, all_ids, paths):
    return contract.validate(db, user_id, source_user, MODELS, tables, all_ids, paths)


def apply(db, decoded):
    contract.apply(db, MODELS, decoded)
