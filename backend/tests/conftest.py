"""Use a disposable database and uploads for the entire test session."""

import os
from tempfile import TemporaryDirectory

_test_directory = TemporaryDirectory(prefix="hustudy-tests-")
os.environ["HUSTUDY_DATABASE_URL"] = f"sqlite:///{_test_directory.name}/test.db"
os.environ["HUSTUDY_STORAGE_ROOT"] = f"{_test_directory.name}/storage"
os.environ["HUSTUDY_JWT_SECRET"] = "isolated-test-secret-only-not-for-real-use-12345"
os.environ["HUSTUDY_LLM_PROVIDER"] = "mock"
os.environ["HUSTUDY_ZHIPU_API_KEY"] = "deterministic-test-key"

# Deterministic tests never depend on Office being installed on the host.
os.environ["HUSTUDY_LIBREOFFICE_PATH"] = "/nonexistent/hustudy-test-office"
