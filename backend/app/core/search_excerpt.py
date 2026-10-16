"""Display excerpts only: offsets count Unicode characters, never Citation offsets."""

import re


def excerpt(body: str, query: str, size: int = 260) -> dict:
    parts = list(dict.fromkeys(re.findall(r"[\w]+", query, re.UNICODE)))
    pattern = (
        re.compile(
            "|".join(re.escape(term) for term in sorted(parts, key=len, reverse=True)),
            re.IGNORECASE,
        )
        if parts
        else None
    )
    first = pattern.search(body) if pattern else None
    if not first and parts:
        # FTS can match constituent Chinese bigrams in separate passages.
        pairs = {
            run[i : i + 2]
            for run in re.findall(r"[\u3400-\u9fff]+", query)
            for i in range(len(run) - 1)
        }
        if pairs:
            pattern = re.compile(
                "|".join(re.escape(term) for term in sorted(pairs)), re.IGNORECASE
            )
            first = pattern.search(body)
    start = max(0, first.start() - 60) if first else 0
    end = min(len(body), start + size)
    value = body[start:end]
    return {
        "text": value,
        "start_offset": start,
        "truncated_after": end < len(body),
        "highlights": [
            {"start": m.start(), "end": m.end()} for m in pattern.finditer(value)
        ]
        if pattern
        else [],
    }
