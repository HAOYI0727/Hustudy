"""Read-only knowledge tag metadata for source links."""

from ..models import Topic
from .topic_tree import active_clause
from .workspace_record_query import metadata_query
from ..repositories.source_links import json_references


def linked_records(user_id, course_id, version_id, chunk_id=None):
    return metadata_query(
        Topic.id, Topic.name, "topic", "LINKED", Topic.updated_at
    ).where(
        Topic.user_id == user_id,
        Topic.course_id == course_id,
        Topic.merged_into_id.is_(None),
        active_clause(),
        json_references(Topic.sources_json, user_id, version_id, chunk_id),
    )
