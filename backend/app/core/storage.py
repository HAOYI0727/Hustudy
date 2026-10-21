"""Atomic local storage with path containment and observable low-disk failures."""

from collections.abc import Iterator
import errno
import os
from pathlib import Path
import shutil
import tempfile
from typing import Protocol
from uuid import UUID, uuid4
from .config import get_settings


class InsufficientStorage(ValueError):
    def __init__(self):
        super().__init__("磁盘剩余空间不足，请释放空间后重试；已保存的资料保留")


def check_capacity(path: Path, required: int = 0) -> None:
    if required < 0:
        raise ValueError("文件空间预算不能为负数")
    existing = path
    while not existing.exists():
        parent = existing.parent
        if parent == existing:
            raise ValueError("文件系统不可用")
        existing = parent
    if (
        shutil.disk_usage(existing).free
        < required + get_settings().storage_reserve_bytes
    ):
        raise InsufficientStorage()


def map_disk_error(error: OSError) -> None:
    if error.errno in {errno.ENOSPC, errno.EDQUOT}:
        raise InsufficientStorage() from error
    raise error


class FileStorage(Protocol):
    def new_path(
        self, user_id: str, course_id: str, suffix: str, group: str = ""
    ) -> Path: ...
    def write(self, path: Path, content: bytes) -> None: ...
    def copy(self, source: Path, target: Path) -> None: ...
    def remove(self, path: Path) -> None: ...
    def write_stream(self, path: Path, stream, size: int) -> None: ...


class LocalFileStorage:
    def __init__(self, root: Path):
        self.root = root.absolute()

    def checked(self, path: Path) -> Path:
        path = path.absolute()
        if not path.is_relative_to(self.root) or not path.resolve().is_relative_to(
            self.root.resolve()
        ):
            raise ValueError("文件路径不在存储根目录内")
        current = path
        while current != self.root:
            if current.is_symlink():
                raise ValueError("存储路径不能使用符号链接")
            current = current.parent
        return path

    def new_path(
        self, user_id: str, course_id: str, suffix: str, group: str = ""
    ) -> Path:
        user_id, course_id = str(UUID(user_id)), str(UUID(course_id))
        if group not in {"", "assets", "exports", "backups", "question_bank"} or suffix not in {
            ".pdf",
            ".pptx",
            ".docx",
            ".md",
            ".markdown",
            ".txt",
            ".png",
            ".jpg",
            ".webp",
            ".zip",
        }:
            raise ValueError("不支持的存储类型")
        return self.checked(
            self.root / user_id / course_id / group / (uuid4().hex + suffix)
        )

    def _publish(self, path: Path, blocks: Iterator[bytes], size: int) -> None:
        path = self.checked(path)
        check_capacity(path.parent, size)
        temporary = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            descriptor, name = tempfile.mkstemp(prefix=".upload-", dir=path.parent)
            temporary = Path(name)
            with os.fdopen(descriptor, "wb") as stream:
                for block in blocks:
                    check_capacity(path.parent, len(block))
                    stream.write(block)
                stream.flush()
                os.fsync(stream.fileno())
            os.link(temporary, path)
        except OSError as error:
            map_disk_error(error)
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)

    def write(self, path: Path, content: bytes) -> None:
        self._publish(path, iter([content]), len(content))

    def write_stream(self, path: Path, stream, size: int) -> None:
        def blocks():
            total = 0
            while block := stream.read(65536):
                total += len(block)
                if total > size:
                    raise ValueError("文件流超过申明大小")
                yield block
            if total != size:
                raise ValueError("文件流大小与申明不符")

        self._publish(path, blocks(), size)

    def copy(self, source: Path, target: Path) -> None:
        with source.open("rb") as stream:
            self._publish(
                target, iter(lambda: stream.read(65536), b""), source.stat().st_size
            )

    def remove(self, path: Path) -> None:
        self.checked(path).unlink(missing_ok=True)


def get_storage() -> FileStorage:
    return LocalFileStorage(Path(get_settings().storage_root))
