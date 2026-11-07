import io
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from fastapi import UploadFile

from app.services.documents import validate_file
from app.services.worker_runtime import WorkerRuntime
from app.workers.materials import parse_isolated


def test_disguised_old_office_is_actionable():
    upload = UploadFile(
        filename="course.pptx",
        file=io.BytesIO(bytes.fromhex("d0cf11e0a1b11ae1") + b"legacy"),
    )
    with pytest.raises(ValueError, match="仅修改扩展名无效"):
        validate_file(upload)


def test_expanded_budget_remains_enforced_with_actionable_message():
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("ppt/presentation.xml", "<presentation/>")
        archive.writestr("ppt/media/big.bin", bytes(100 * 1024 * 1024))
    upload = UploadFile(filename="large.pptx", file=io.BytesIO(data.getvalue()))
    with pytest.raises(ValueError, match="压缩内嵌图片或拆分"):
        validate_file(upload)


@pytest.mark.parametrize(
    "error",
    [
        subprocess.CalledProcessError(
            1, ["private/path", "private/source"], stderr=b"private-provider-response"
        ),
        subprocess.TimeoutExpired(["private/path"], 60),
        OSError("private/path"),
    ],
)
def test_parser_process_errors_do_not_expose_commands_or_paths(
    monkeypatch, tmp_path, error
):
    def fail(*args, **kwargs):
        assert kwargs["cwd"] == str(Path(__file__).resolve().parents[2])
        assert Path(args[0][-2]).is_absolute()
        raise error

    monkeypatch.setattr(subprocess, "run", fail)
    with pytest.raises(ValueError) as caught:
        parse_isolated(tmp_path / "source.pptx")
    assert "private" not in str(caught.value)


def test_parser_does_not_depend_on_launch_directory(monkeypatch, tmp_path):
    source = tmp_path / "source.md"
    source.write_text("# 数据库\n\n事务的原子性。", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    chunks = parse_isolated(source)
    assert chunks[0]["text"] == "事务的原子性。"
    assert sys.executable


def test_worker_detects_development_source_changes(monkeypatch):
    stamp = [("file.py", 1, 10)]
    monkeypatch.setattr(
        WorkerRuntime, "_source_stamp", staticmethod(lambda: tuple(stamp))
    )
    runtime = WorkerRuntime()
    assert not runtime.source_changed()
    stamp.append(("new.py", 2, 20))
    runtime.next_source_check = 0
    assert runtime.source_changed()
    from app.core.config import base_settings

    monkeypatch.setattr(base_settings(), "env", "production")
    assert not runtime.source_changed()


def test_missing_original_does_not_leak_path(tmp_path):
    with pytest.raises(ValueError, match="无法读取原件") as caught:
        parse_isolated(tmp_path / "private-missing.pptx")
    assert str(tmp_path) not in str(caught.value)


def test_parser_missing_output_is_safe(monkeypatch, tmp_path):
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: None)
    with pytest.raises(ValueError, match="解析结果不可读取") as caught:
        parse_isolated(tmp_path / "private-source.pptx")
    assert str(tmp_path) not in str(caught.value)


def test_source_reload_waits_for_preview_and_releases_lock(monkeypatch):
    from app.services import worker_runtime
    from app.workers import materials

    events = []

    class Runtime:
        def __enter__(self):
            events.append("lock")
            return self

        def __exit__(self, *_):
            events.append("unlock")

        def publish(self):
            pass

        def source_changed(self):
            return True

    class Preview:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            pass

        def is_alive(self):
            return True

        def join(self, timeout=None):
            events.append("preview_finished")

    monkeypatch.setattr(worker_runtime, "WorkerRuntime", Runtime)
    monkeypatch.setattr(materials.threading, "Thread", Preview)
    monkeypatch.setattr(
        materials,
        "run_core_once",
        lambda: pytest.fail("reload must not claim a new task"),
    )
    assert materials.serve() is True
    assert events[0] == "lock"
    assert events.index("preview_finished") < events.index("unlock")
