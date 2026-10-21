"""Isolated import classification, explicit OCR, image privacy and removal risks."""

import io
import json
from uuid import uuid4
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models import PastPaper, PastQuestion, ProcessingJob
from app.services import question_bank as bank
from app.services.bank_ocr import assemble
from app.workers.bank_ocr import run_bank_ocr_once
from test_materialhub import context
from test_question_bank import seed_bank, draw, start


def image_upload(client, headers, course, color="white"):
    data = io.BytesIO()
    Image.new("RGB", (320, 400), color).save(data, format="PNG")
    response = client.post(
        f"/api/v1/courses/{course}/assets",
        headers=headers,
        files={"file": ("question.png", data.getvalue(), "image/png")},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_content_profiles_and_separate_answer_appendix():
    raw = """1. 正确的协议是什么？
A. IP B. TCP C. ARP D. ICMP
【解析】这道题需要按网络分层判断。故选B。
2. TCP名为____。
3. 说明协议的作用。
参考答案与解析
1. B。TCP是传输层协议。
2. 传输控制协议
"""
    rows = bank.parse_text(raw)
    assert len(rows) == 3
    assert (
        rows[0]["answer"] == "B" and rows[0]["content_profile"] == "with_explanations"
    )
    assert (
        rows[1]["answer"] is None
    )  # Unlabelled fill appendix is not silently guessed.
    assert rows[1]["explanation"] == "传输控制协议"
    assert rows[2]["content_profile"] == "questions_only"
    only = bank.parse_text("1. 答案：B\n解析：仅解析没有题干。")
    assert only[0]["content_profile"] == "answer_only"
    assert (
        bank.parse_text(
            "1. 什么是答案？\nA.甲 B.乙 C.丙 D.丁\n解析：甲和乙都需要分析。"
        )[0]["answer"]
        is None
    )


def test_ocr_assembly_cross_page_question_and_source_strips():
    a, b = str(uuid4()), str(uuid4())

    def page(aid, lines, left=0, width=1):
        return {
            "asset_id": aid,
            "left": left,
            "width": width,
            "lines": [{"text": t, "y": y, "bottom": y + 0.04} for t, y in lines],
        }

    text, parsed = assemble(
        [
            page(a, [("1. 选择协议？", 0.1), ("A. IP", 0.2), ("B. TCP", 0.3)]),
            page(
                b,
                [
                    ("C. ARP", 0.1),
                    ("D. ICMP", 0.2),
                    ("答案：B", 0.3),
                    ("2. 解释网络。", 0.6),
                ],
            ),
        ]
    )
    assert len(parsed) == 2 and parsed[0]["options"] == ["IP", "TCP", "ARP", "ICMP"]
    assert parsed[0]["answer"] == "B"
    assert [i["asset_id"] for i in parsed[0]["source_images"]] == [a, b]
    assert (
        parsed[0]["source_images"][1]["box"][1]
        + parsed[0]["source_images"][1]["box"][3]
        < 0.6
    )
    assert "解释网络" in text


def test_unnumbered_photos_stay_separate_and_empty_images_are_reported():
    pages = [
        {
            "asset_id": str(uuid4()),
            "left": 0,
            "width": 1,
            "lines": [{"text": text, "y": 0.1, "bottom": 0.3}],
        }
        for text in ["解释网络。", "说明协议。"]
    ]
    pages.append({"asset_id": str(uuid4()), "left": 0, "width": 1, "lines": []})
    _, rows = assemble(pages)
    assert len(rows) == 2
    assert rows[0]["stem"] == "解释网络。" and rows[1]["stem"] == "说明协议。"
    assert (
        rows[0]["source_images"][0]["asset_id"]
        != rows[1]["source_images"][0]["asset_id"]
    )
    assert any("没有识别到文字" in warning for warning in rows[0]["warnings"])


def test_label_without_colon_and_question_words_not_confused_with_metadata():
    row = bank.parse_text(
        "1. 分析这个算法的作用。\n答案\n这是一个示例\n解析\n保留具体推理。"
    )[0]
    assert row["stem"] == "分析这个算法的作用。"
    assert row["answer"] == "这是一个示例" and row["explanation"] == "保留具体推理。"


def test_explicit_ocr_job_and_source_images_are_review_only(monkeypatch):
    calls = []
    with TestClient(app) as client:
        h, c = context(client)
        image = image_upload(client, h, c)
        assert not run_bank_ocr_once()  # Uploading a picture alone never starts OCR.
        payload = {
            "request_id": str(uuid4()),
            "title": "图片题库",
            "asset_ids": [image],
            "layout": "single",
        }
        monkeypatch.setattr(
            "app.services.bank_ocr.importlib.util.find_spec", lambda name: True
        )

        def ocr(items, layout):
            calls.append((items, layout))
            return [
                {
                    "asset_id": image,
                    "left": 0,
                    "width": 1,
                    "lines": [{"text": "1. 说明图形。", "y": 0.1, "bottom": 0.2}],
                }
            ]

        monkeypatch.setattr("app.workers.bank_ocr.recognize", ocr)
        job = client.post(
            f"/api/v1/courses/{c}/question-bank/images", headers=h, json=payload
        )
        assert job.status_code == 202, job.text
        assert not calls
        assert (
            client.post(
                f"/api/v1/courses/{c}/question-bank/images", headers=h, json=payload
            ).json()["id"]
            == job.json()["id"]
        )
        assert run_bank_ocr_once() and len(calls) == 1
        assert not run_bank_ocr_once()
        reuploaded = image_upload(client, h, c)
        duplicate = client.post(
            f"/api/v1/courses/{c}/question-bank/images",
            headers=h,
            json={**payload, "request_id": str(uuid4()), "asset_ids": [reuploaded]},
        )
        assert (
            duplicate.status_code == 202 and duplicate.json()["id"] == job.json()["id"]
        )
        assert not run_bank_ocr_once()
        result = client.get(
            f"/api/v1/courses/{c}/question-bank/image-jobs", headers=h
        ).json()
        assert result[0]["status"] == "SUCCEEDED"
        questions = client.get(f"/api/v1/courses/{c}/question-bank", headers=h).json()[
            "items"
        ]
        assert (
            len(questions) == 1
            and questions[0]["bank_data"]["source_images"][0]["asset_id"] == image
        )
        q = questions[0]
        assert "illustrations" not in bank.public_question(
            {"id": "x", "source_images": q["bank_data"]["source_images"]}
        )
        with SessionLocal() as db:
            paper = db.get(PastPaper, q["paper_id"])
            assert paper.content == "1. 说明图形。\n"


def test_images_crop_authorization_and_reviewed_snapshot():
    with TestClient(app) as client:
        h, c = context(client)
        foreign, other = context(client)
        aid = image_upload(client, h, c)
        bad = image_upload(client, foreign, other)
        p, topic = seed_bank(client, h, c, "1. 说明插图。\n知识标签：网络")
        q = p["questions"][0]
        payload = {
            "revision": q["revision"],
            "stem": q["stem"],
            "question_type": "solution",
            "topic_ids": [topic],
            "illustrations": [{"asset_id": aid, "box": [0.1, 0.2, 0.5, 0.5]}],
        }
        endpoint = f"/api/v1/past-questions/{q['id']}"
        invalid = client.patch(
            endpoint, headers=h, json={**payload, "illustrations": [{"asset_id": bad}]}
        )
        assert invalid.status_code == 404
        invalid = client.patch(
            endpoint,
            headers=h,
            json={
                **payload,
                "illustrations": [{"asset_id": aid, "box": [0.5, 0, 0.8, 1]}],
            },
        )
        assert invalid.status_code == 422
        saved = client.patch(endpoint, headers=h, json=payload).json()
        assert (
            client.post(f"/api/v1/past-papers/{p['id']}/confirm", headers=h).status_code
            == 422
        )
        payload["revision"] = saved["revision"]
        payload["images_reviewed"] = True
        assert client.patch(endpoint, headers=h, json=payload).status_code == 200
        assert (
            client.post(f"/api/v1/past-papers/{p['id']}/confirm", headers=h).status_code
            == 200
        )
        cropped = client.get(
            f"/api/v1/question-bank/illustrations/{aid}?course_id={c}&box=0.1,0.2,0.5,0.5",
            headers=h,
        )
        assert cropped.status_code == 200
        assert Image.open(io.BytesIO(cropped.content)).size == (
            160,
            200,
        )  # Pixels actually cropped on the server.
        assert (
            client.get(
                f"/api/v1/question-bank/illustrations/{aid}?course_id={c}",
                headers=foreign,
            ).status_code
            == 404
        )
        exam = draw(client, h, c, topic, 1)
        public = client.get(f"/api/v1/exam-papers/{exam['id']}", headers=h).json()
        assert public["questions"][0]["illustrations"][0]["asset_id"] == aid
        assert "source_images" not in public["questions"][0]
        assert "answer" not in public["questions"][0]


def test_batch_delete_revision_atomicity_active_attempt_and_old_snapshot():
    with TestClient(app) as client:
        h, c = context(client)
        p, t = seed_bank(
            client, h, c, "1. 说明网络。\n知识标签：网络\n2. 说明协议。\n知识标签：网络"
        )
        questions = p["questions"]
        ids = [q["id"] for q in questions]
        revisions = {q["id"]: q["revision"] for q in questions}
        url = f"/api/v1/courses/{c}/question-bank/batch"
        failed = client.post(
            url,
            headers=h,
            json={
                "question_ids": ids,
                "revisions": {ids[0]: 999, ids[1]: revisions[ids[1]]},
                "action": "delete",
            },
        )
        assert failed.status_code == 409
        assert (
            client.get(f"/api/v1/courses/{c}/question-bank", headers=h).json()["total"]
            == 2
        )
        exam = draw(client, h, c, t, 2)
        attempt = start(client, h, exam)
        assert (
            client.delete(
                f"/api/v1/past-questions/{ids[0]}?revision={revisions[ids[0]]}",
                headers=h,
            ).status_code
            == 409
        )
        client.post(f"/api/v1/attempts/{attempt['id']}/submit", headers=h)
        assert (
            client.post(
                url,
                headers=h,
                json={"question_ids": ids, "revisions": revisions, "action": "delete"},
            ).status_code
            == 200
        )
        assert (
            client.get(f"/api/v1/courses/{c}/question-bank", headers=h).json()["total"]
            == 0
        )
        with SessionLocal() as db:
            assert all(db.get(PastQuestion, qid).status == "SUPERSEDED" for qid in ids)
            assert json.loads(db.get(PastQuestion, ids[0]).bank_data_json)[
                "removed_by_user"
            ]
        result = client.get(f"/api/v1/attempts/{attempt['id']}/result", headers=h)
        assert result.status_code == 200 and len(result.json()["questions"]) == 2


def test_ocr_failure_and_cancellation_never_publish_drafts(monkeypatch):
    with TestClient(app) as client:
        h, c = context(client)
        aid = image_upload(client, h, c)
        monkeypatch.setattr(
            "app.services.bank_ocr.importlib.util.find_spec", lambda name: True
        )
        job = client.post(
            f"/api/v1/courses/{c}/question-bank/images",
            headers=h,
            json={"request_id": str(uuid4()), "title": "失败样例", "asset_ids": [aid]},
        ).json()

        def broken(*args):
            raise ValueError("未识别到文字，请核对原图")

        monkeypatch.setattr("app.workers.bank_ocr.recognize", broken)
        assert run_bank_ocr_once()
        with SessionLocal() as db:
            assert db.get(ProcessingJob, job["id"]).status == "FAILED"
        assert (
            client.get(f"/api/v1/courses/{c}/question-bank", headers=h).json()["total"]
            == 0
        )


def test_ocr_and_illustrations_roundtrip_backup(monkeypatch):
    from app.models import User
    from test_account_backups import exported, restored, empty_account

    with TestClient(app) as client:
        h, c = context(client)
        source_user = client.get("/api/v1/auth/me", headers=h).json()["id"]
        aid = image_upload(client, h, c)
        topic = client.post(
            f"/api/v1/courses/{c}/topics", headers=h, json={"name": "图文"}
        ).json()["id"]
        monkeypatch.setattr(
            "app.services.bank_ocr.importlib.util.find_spec", lambda name: True
        )
        monkeypatch.setattr(
            "app.workers.bank_ocr.recognize",
            lambda *args: [
                {
                    "asset_id": aid,
                    "left": 0,
                    "width": 1,
                    "lines": [{"text": "1. 说明图形。", "y": 0.1, "bottom": 0.3}],
                }
            ],
        )
        job = client.post(
            f"/api/v1/courses/{c}/question-bank/images",
            headers=h,
            json={
                "request_id": str(uuid4()),
                "title": "恢复样例",
                "asset_ids": [aid],
                "default_topic_ids": [topic],
            },
        ).json()
        assert run_bank_ocr_once()
        q = client.get(f"/api/v1/courses/{c}/question-bank", headers=h).json()["items"][
            0
        ]
        assert (
            client.patch(
                f"/api/v1/past-questions/{q['id']}",
                headers=h,
                json={
                    "revision": q["revision"],
                    "stem": q["stem"],
                    "question_type": "solution",
                    "topic_ids": [topic],
                    "illustrations": [{"asset_id": aid, "box": [0.1, 0.1, 0.4, 0.4]}],
                    "images_reviewed": True,
                },
            ).status_code
            == 200
        )
        body, _ = exported(client, h)
        with SessionLocal() as db:
            db.delete(db.get(User, source_user))
            db.commit()
        target, _ = empty_account(client)
        restored_job = restored(client, target, body)
        assert restored_job["job"]["status"] == "SUCCEEDED", restored_job
        jobs = client.get(
            f"/api/v1/courses/{c}/question-bank/image-jobs", headers=target
        ).json()
        assert jobs[0]["id"] == job["id"] and jobs[0]["status"] == "SUCCEEDED"
        question = client.get(
            f"/api/v1/courses/{c}/question-bank", headers=target
        ).json()["items"][0]
        assert question["bank_data"]["source_images"][0]["asset_id"] == aid
        assert question["bank_data"]["illustrations"][0]["box"] == [0.1, 0.1, 0.4, 0.4]
        assert (
            client.get(
                f"/api/v1/question-bank/illustrations/{aid}?course_id={c}&box=.1,.1,.4,.4",
                headers=target,
            ).status_code
            == 200
        )
