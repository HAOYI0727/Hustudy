"""Small periodic maintenance hook, independent of the queued job backlog."""

import logging
import time
from ..core.database import SessionLocal
from ..services.note_trash import cleanup_due

_next_run = 0.0


def run_trash_cleanup(force=False):
    global _next_run
    if not force and time.monotonic() < _next_run:
        return
    _next_run = time.monotonic() + 60
    try:
        with SessionLocal() as db:
            count = cleanup_due(db)
        if count:
            logging.getLogger(__name__).info("Removed %s expired trash notes", count)
    except Exception:
        logging.getLogger(__name__).exception(
            "Trash maintenance failed; retry next minute"
        )
