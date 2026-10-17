"""Complete report demo is restricted to the repository's authored fixture."""

from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.models import ProcessingJob
from app.core.database import SessionLocal
from test_material_organization import setup_course, import_document


def test_complete_fixed_report_persistence_legacy_and_no_model_jobs():
    with TestClient(app) as client:
        owner, course = setup_course(client)
        fixture = Path(__file__).resolve().parents[2] / "fixtures/materialhub_demo.md"
        _, version = import_document(client, owner, course, fixture.read_bytes())
        result = client.post(
            f"/api/v1/courses/{course}/study-reports/demo",
            headers=owner,
            json={"version_ids": [version]},
        ).json()
        assert result["status"] == "grounded" and result["model_mode"] == "demo"
        report = result["result"]["study_report"]
        assert report["learning_goals"] and len(report["self_checks"]) == 3
        assert report["model_mode"] == "demo" and report["citations"]
        assert (
            client.get(f"/api/v1/study-reports/{result['id']}", headers=owner).json()
            == result
        )
        assert (
            client.get(f"/api/v1/courses/{course}/study-reports", headers=owner).json()[
                0
            ]["id"]
            == result["id"]
        )
        legacy = client.post(
            f"/api/v1/versions/{version}/study-reports", headers=owner, json={}
        ).json()
        assert legacy["report"]["learning_goals"] and legacy["model_mode"] == "demo"
        with SessionLocal() as db:
            uid = client.get("/api/v1/auth/me", headers=owner).json()["id"]
            assert not db.scalars(
                select(ProcessingJob).where(
                    ProcessingJob.user_id == uid, ProcessingJob.type == "AI_ANALYSIS"
                )
            ).all()


def test_fixed_report_unknown_and_unrelated_fragment_are_insufficient():
    with TestClient(app) as client:
        owner, course = setup_course(client)
        _, unknown = import_document(
            client, owner, course, "# 随便的资料\n\n无法模拟理解。"
        )
        result = client.post(
            f"/api/v1/courses/{course}/study-reports/demo",
            headers=owner,
            json={"version_ids": [unknown]},
        ).json()
        assert (
            result["status"] == "insufficient_evidence"
            and "study_report" not in result["result"]
        )
        fixture = Path(__file__).resolve().parents[2] / "fixtures/materialhub_demo.md"
        _, version = import_document(client, owner, course, fixture.read_bytes())
        chunks = client.get(f"/api/v1/versions/{version}/chunks", headers=owner).json()
        unrelated = next(c for c in chunks if c["locator_value"] == "进程状态")
        result = client.post(
            f"/api/v1/courses/{course}/study-reports/demo",
            headers=owner,
            json={"version_ids": [version], "chunk_ids": [unrelated["id"]]},
        ).json()
        assert (
            result["status"] == "insufficient_evidence"
            and result["result"]["citations"] == []
        )
