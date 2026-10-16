"""Disposable local API + worker for Playwright; never reads the real account DB."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="hustudy-e2e-") as scratch:
        env = {
            **os.environ,
            "PYTHONPATH": str(root / "backend"),
            "HUSTUDY_DATABASE_URL": f"sqlite:///{scratch}/e2e.db",
            "HUSTUDY_STORAGE_ROOT": f"{scratch}/storage",
            "HUSTUDY_JWT_SECRET": "isolated-playwright-test-secret-only-123456789",
            "HUSTUDY_LLM_PROVIDER": "mock",
            "HUSTUDY_ZHIPU_API_KEY": "",
            "HUSTUDY_CORS_ORIGINS": "http://127.0.0.1:5178",
        }
        processes = []

        def stop(_signal=None, _frame=None):
            for process in processes:
                process.terminate()
            for process in processes:
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

        signal.signal(signal.SIGTERM, lambda *args: sys.exit(0))
        signal.signal(signal.SIGINT, lambda *args: sys.exit(0))
        try:
            # Initialize migrations before concurrently starting API/worker.
            subprocess.run([sys.executable, "-c", "from app.core.database import init_db; init_db()"], cwd=root, env=env, check=True)
            for command in (["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8056"], ["-m", "app.workers.materials"]):
                processes.append(subprocess.Popen([sys.executable, *command], cwd=root, env=env))
            while all(process.poll() is None for process in processes):
                time.sleep(0.2)
            raise RuntimeError("E2E API or worker exited early")
        finally:
            stop()


if __name__ == "__main__":
    main()
