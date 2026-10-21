"""Derive current mastery without rewriting original exam answers."""

from datetime import datetime


def judgments(data):
    events = [
        item for item in data.get("redoes", {}).values()
        if item.get("status") == "COMPLETED" and item.get("completed_at")
    ] + [
        {**item, "correct": False}
        for item in data.get("relapses", {}).values()
    ]
    return sorted(events, key=lambda item: (
        item.get("sequence", 0), datetime.fromisoformat(item["completed_at"]),
    ))


def next_sequence(data):
    return max((item.get("sequence", 0) for item in judgments(data)), default=0) + 1


def mastered_since(data):
    since = None
    for item in judgments(data):
        if item.get("correct") is not True:
            since = None
        elif since is None:
            since = datetime.fromisoformat(item["completed_at"])
    return since
