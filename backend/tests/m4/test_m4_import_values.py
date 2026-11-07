from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.main import app
from app.services import bank_ai, bank_vision
from app.services.bank_strict_markdown import parse
from app.services.bank_parser import parse as parse_plain
from tests.m1.test_materialhub import context
from tests.m4.test_bank_vision import block


def test_strict_year_points_import_and_explicit_unknown():
    raw = "# Hustudy 题库 v1\n\n## 题目 1\n### 年份\n2023\n### 分值\n10\n### 题型\n解答题\n### 题干\n测试题。\n\n## 题目 2\n### 年份\n\n### 分值\n\n### 题型\n解答题\n### 题干\n未知值题。"
    rows = parse(raw)
    assert (rows[0]["year"], rows[0]["points"]) == (2023, 10)
    assert rows[1]["year"] is None and rows[1]["points"] is None
    for invalid in ["2023年", "1899", "2201", "-1"]:
        with pytest.raises(HTTPException):
            parse(raw.replace("\n2023\n", "\n" + invalid + "\n"))
    with TestClient(app) as client:
        h, course = context(client)
        result = client.post(
            f"/api/v1/courses/{course}/question-bank/import",
            headers=h,
            json={
                "title": "明确元数据",
                "year": 2020,
                "content": raw,
                "strict_markdown": True,
            },
        )
        assert result.status_code == 201, result.text
        questions = result.json()["questions"]
        assert (
            questions[0]["bank_data"]["year"] == 2023 and questions[0]["points"] == 10
        )
        assert (
            questions[1]["bank_data"]["year"] is None and questions[1]["points"] is None
        )


def test_vision_values_survive_assembly_import_and_old_payloads():
    first = block("1") | {"year": 2024, "points": 8}
    second = block("2")
    pages = [
        {
            "asset_id": str(uuid4()),
            "result": {"year": 2023, "blocks": [first, second], "empty": False},
        },
        {"asset_id": str(uuid4()), "result": {"blocks": [block("3")], "empty": False}},
    ]
    content, rows = bank_vision.assemble(pages)
    assert [q.get("year") for q in rows] == [2024, 2023, 2023]
    assert [q["points"] for q in rows] == [8, None, None]
    with pytest.raises(ValidationError):
        bank_vision.Block.model_validate(first | {"points": 501})
    with pytest.raises(ValidationError):
        bank_vision.Page.model_validate(pages[0]["result"] | {"year": "2023"})
    assert (
        "year"
        not in bank_vision.assemble(
            [{"asset_id": "old", "result": {"blocks": [block("1")], "empty": False}}]
        )[1][0]
    )
    # Actual shared persistence receives the parsed metadata, preserving defaults.
    from app.core.database import SessionLocal
    from app.models import PastPaper, PastQuestion
    from app.services import question_bank as bank
    from sqlalchemy import select
    import json

    with TestClient(app) as client:
        h, course = context(client)
        uid = client.get("/api/v1/auth/me", headers=h).json()["id"]
        with SessionLocal() as db:
            paper = PastPaper(
                user_id=uid,
                course_id=course,
                title="模拟已识别元数据",
                content=content,
                content_hash="synthetic-hash",
            )
            db.add(paper)
            db.flush()
            bank.populate_bank(db, uid, course, paper, content, rows)
            saved = db.scalars(
                select(PastQuestion)
                .where(PastQuestion.paper_id == paper.id)
                .order_by(PastQuestion.number)
            ).all()
            assert (
                saved[0].points == 8
                and json.loads(saved[0].bank_data_json)["year"] == 2024
            )
            assert (
                saved[1].points is None
                and json.loads(saved[1].bank_data_json)["year"] == 2023
            )
            db.rollback()


def test_text_ai_only_reads_explicit_source_values_and_scope():
    text = "2023年计算机组成原理试卷\n1. 条件中的2020和100并非年份和分值。\n分值：10分\n年份：2024\n2. 第二题。"
    rows = parse_plain(text)
    assert rows[0]["year"] == 2024 and rows[0]["points"] == 10
    assert rows[1]["year"] == 2023 and rows[1]["points"] is None

    class Fake:
        def structured(self, *args, **kwargs):
            return bank_ai.Extraction(
                questions=[
                    bank_ai.ExtractedQuestion(
                        number="1",
                        type="solution",
                        stem_lines=[2],
                        metadata_lines=[3, 4],
                    ),
                    bank_ai.ExtractedQuestion(
                        number="2", type="solution", stem_lines=[5]
                    ),
                ]
            ), {}

    rows = bank_ai.extract(text, Fake())
    assert (rows[0]["year"], rows[0]["points"]) == (2024, 10)
    assert rows[1]["year"] == 2023 and rows[1]["points"] is None


def test_standard_sample_numeric_values_and_private_demo_values():
    root = Path(__file__).resolve().parents[3]
    rows = parse(
        (root / "frontend/src/features/exams/bankExample.md").read_text(
            encoding="utf-8"
        )
    )
    assert [q["year"] for q in rows] == [2023, 2023, None]
    assert [q["points"] for q in rows] == [2, 6, None]
