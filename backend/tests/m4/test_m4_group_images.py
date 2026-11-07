from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.core.database import SessionLocal
from app.models import PastQuestion, PastPaper
import io
import json
from PIL import Image
from tests.m1.test_materialhub import context
from tests.m4.test_question_bank import seed_bank


def test_group_images_include_all_siblings_and_reject_stale_revision():
    with TestClient(app) as client:
        headers, course = context(client)
        paper, _ = seed_bank(client, headers, course, "1. 第一问。\n知识标签：综合\n2. 第二问。\n知识标签：综合\n")
        with SessionLocal() as db:
            rows = db.scalars(select(PastQuestion).where(PastQuestion.paper_id == paper["id"])).all()
            for index, row in enumerate(rows, 1):
                row.number = f"一.{index}"
                row.status = "DRAFT"
            db.get(PastPaper, paper["id"]).review_status = "DRAFT"
            db.commit()
            identity = rows[0].id
        path = f"/api/v1/past-questions/{identity}/image-group"
        group = client.get(path, headers=headers).json()
        assert len(group) == 2
        buffer = io.BytesIO()
        Image.new("RGB", (20, 20), "white").save(buffer, format="PNG")
        asset = client.post(f"/api/v1/courses/{course}/assets", headers=headers,
                            files={"file": ("figure.png", buffer.getvalue(), "image/png")}).json()
        images = [{"asset_id": asset["id"], "box": [0, 0, 1, 1], "alt": "草稿插图"}]
        payload = {"revisions": {q["id"]: q["revision"] for q in group}, "images": images}
        response = client.put(path, headers=headers, json=payload)
        assert response.status_code == 200, response.text
        assert response.json()["changed"] == 2
        assert response.json()["revisions"] == {q["id"]: q["revision"] + 1 for q in group}
        with SessionLocal() as db:
            assert all(json.loads(row.bank_data_json)["illustrations"] == images
                       for row in db.scalars(select(PastQuestion).where(PastQuestion.paper_id == paper["id"])))
        assert client.put(path, headers=headers, json=payload).status_code == 409
        other, _ = context(client)
        assert client.get(path, headers=other).status_code == 404


def test_forced_pdf_render_never_extracts_text(tmp_path, monkeypatch):
    from app.services import bank_pdf
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument.new()
    page = document.new_page(200, 300)
    path = tmp_path / "source.pdf"
    document.save(str(path))
    page.close()
    document.close()
    def forbidden(*args):
        raise AssertionError("Forced AI rendering must skip text extraction")
    monkeypatch.setattr(bank_pdf, "examine", forbidden)
    pages = bank_pdf.render_pages(path, tmp_path, True)
    assert len(pages) == 1 and pages[0]["number"] == 1
    assert (tmp_path / pages[0]["image"]).is_file()
