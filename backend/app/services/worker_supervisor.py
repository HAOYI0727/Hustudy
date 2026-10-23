"""Development API owns at most one child; production can use an external manager."""

import logging
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

from .worker_runtime import inspect_runtime

logger = logging.getLogger(__name__)


class ManagedWorker:
    def __init__(self):
        self.stop = threading.Event()
        self.child = None
        self.thread = None
        self.next_start = 0.0
        self.delay = 1.0
        self.started_at = 0.0

    def tick(self):
        now = time.monotonic()
        if self.child is not None:
            code = self.child.poll()
            if code is None:
                if now - self.started_at >= 30:
                    self.delay = 1.0
                return
            logger.warning(
                "Processing worker exited code=%s; restart after %.0fs",
                code,
                self.delay,
            )
            # A killed worker can leave an Office/parser descendant alive. Its
            # session is ours even after the leader exits; reap it before restart.
            if os.name != "nt":
                try:
                    os.killpg(self.child.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            self.child = None
            self.next_start = now + self.delay
            self.delay = min(self.delay * 2, 15)
        if self.stop.is_set() or now < self.next_start or inspect_runtime()[0]:
            return
        root = Path(__file__).resolve().parents[3]
        env = {**os.environ, "PYTHONPATH": str(root / "backend")}
        try:
            self.child = subprocess.Popen(
                [sys.executable, "-m", "app.workers.materials"],
                cwd=root,
                env=env,
                start_new_session=os.name != "nt",
            )
            self.started_at = now
            logger.info("Started managed processing worker")
        except OSError:
            logger.exception("Cannot start processing worker; will retry")
            self.next_start = now + self.delay
            self.delay = min(self.delay * 2, 15)

    def _loop(self):
        while not self.stop.is_set():
            try:
                self.tick()
            except Exception:
                logger.exception("Processing supervisor check failed; will retry")
            self.stop.wait(0.5)

    def start(self):
        self.thread = threading.Thread(
            target=self._loop, daemon=True, name="processing-supervisor"
        )
        self.thread.start()

    def close(self):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=3)
        child = self.child
        if child is None:
            return
        try:
            if os.name != "nt":
                os.killpg(child.pid, signal.SIGTERM)
            else:
                child.terminate()
            child.wait(timeout=5)
        except ProcessLookupError:
            pass
        except subprocess.TimeoutExpired:
            if os.name != "nt":
                os.killpg(child.pid, signal.SIGKILL)
            else:
                child.kill()
            child.wait(timeout=5)
