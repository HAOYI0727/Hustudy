"""M2 snapshot/restore; importing saved consent never dispatches a new request."""

from ..core import backup_contract as contract
from ..models import AIResult, RemoteQuery

MODELS = [AIResult, RemoteQuery]


def snapshot(db, user_id):
    return contract.serialize(db, user_id, MODELS), []


def empty(db, user_id):
    contract.assert_empty(db, user_id, MODELS)


def validate(db, user_id, source_user, tables, all_ids, paths):
    return contract.validate(db, user_id, source_user, MODELS, tables, all_ids, paths)


def apply(db, decoded):
    contract.apply(db, MODELS, decoded)
