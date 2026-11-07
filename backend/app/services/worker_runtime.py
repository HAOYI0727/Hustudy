"""Local process liveness, separate from durable jobs and their attempt budget."""

import errno
import hashlib
import json
import os
from pathlib import Path
import threading
import time
from uuid import uuid4

from sqlalchemy.engine import make_url

from ..core.config import base_settings

HEARTBEAT_SECONDS = 2
STALE_SECONDS = 15


def runtime_directory() -> Path:
    settings = base_settings()
    url = make_url(settings.database_url)
    identity = (
        str(Path(url.database).resolve())
        if url.database and url.drivername == "sqlite"
        else settings.database_url
    )
    key = hashlib.sha256(identity.encode()).hexdigest()[:24]
    return Path(settings.storage_root).resolve() / ".runtime" / key


def _lock(stream) -> bool:
    try:
        if os.name == "nt":
            import msvcrt

            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError as exc:
        if exc.errno in (errno.EACCES, errno.EAGAIN):
            return False
        raise


def _unlock(stream):
    if os.name == "nt":
        import msvcrt

        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(stream, fcntl.LOCK_UN)


def inspect_runtime() -> tuple[bool, dict | None]:
    """Read only: never create a lock, heartbeat, directory, or database row."""
    folder = runtime_directory()
    try:
        with (folder / "worker.lock").open("r+b") as stream:
            if _lock(stream):
                _unlock(stream)
                return False, None
        with (folder / "heartbeat.json").open("rb") as stream:
            raw = stream.read(1025)
        if len(raw) > 1024:
            return True, None
        data = json.loads(raw)
        if not isinstance(data, dict) or set(data) != {
            "version",
            "pid",
            "updated_at",
            "ready",
        }:
            return True, None
        if (
            data["version"] != 1
            or type(data["pid"]) is not int
            or type(data["ready"]) is not bool
        ):
            return True, None
        stamp = data["updated_at"]
        if (
            type(stamp) not in (int, float)
            or not 0 <= time.time() - stamp <= STALE_SECONDS
        ):
            return True, None
        return True, data
    except FileNotFoundError:
        # Missing heartbeat under a held lock means startup, not an absent process.
        return (folder / "worker.lock").exists(), None
    except (OSError, ValueError, TypeError):
        return True, None


def processing_status() -> str:
    locked, heartbeat = inspect_runtime()
    if not locked:
        return "unavailable"
    if heartbeat:
        return "ready" if heartbeat["ready"] else "starting"
    return "unavailable"


class WorkerAlreadyRunning(RuntimeError):
    pass


class WorkerRuntime:
    def __init__(self):
        self.folder = runtime_directory()
        self.stop = threading.Event()
        self.ready = False
        self.stream = None
        self.thread = None
        self.source_stamp = self._source_stamp()
        self.next_source_check = 0.0

    @staticmethod
    def _source_stamp():
        app_root = Path(__file__).resolve().parents[1]
        return tuple(
            (
                str(path.relative_to(app_root)),
                path.stat().st_mtime_ns,
                path.stat().st_size,
            )
            for path in sorted(app_root.rglob("*.py"))
        )

    def source_changed(self):
        if base_settings().env != "development":
            return False
        now = time.monotonic()
        if now < self.next_source_check:
            return False
        self.next_source_check = now + 2
        try:
            return self._source_stamp() != self.source_stamp
        except OSError:
            # A checkout can temporarily remove files; check again after it settles.
            return False

    def publish(self):
        payload = {
            "version": 1,
            "pid": os.getpid(),
            "updated_at": time.time(),
            "ready": self.ready,
        }
        scratch = self.folder / ("heartbeat-" + uuid4().hex + ".tmp")
        try:
            with scratch.open("x", encoding="utf-8") as stream:
                os.chmod(scratch, 0o600)
                json.dump(payload, stream)
            scratch.replace(self.folder / "heartbeat.json")
        finally:
            scratch.unlink(missing_ok=True)

    def _heartbeat(self):
        while not self.stop.wait(HEARTBEAT_SECONDS):
            try:
                self.publish()
            except OSError:
                # A failed heartbeat becomes stale; it must never count as ready.
                continue

    def __enter__(self):
        self.folder.mkdir(parents=True, exist_ok=True)
        self.stream = (self.folder / "worker.lock").open("a+b")
        if self.stream.tell() == 0:
            self.stream.write(b"0")
            self.stream.flush()
        if not _lock(self.stream):
            self.stream.close()
            self.stream = None
            raise WorkerAlreadyRunning(
                "A worker already owns this database/storage runtime"
            )
        try:
            self.publish()
            self.thread = threading.Thread(
                target=self._heartbeat, daemon=True, name="worker-heartbeat"
            )
            self.thread.start()
        except Exception:
            _unlock(self.stream)
            self.stream.close()
            raise
        return self

    def __exit__(self, *_exc):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=3)
        if self.stream:
            _unlock(self.stream)
            self.stream.close()
