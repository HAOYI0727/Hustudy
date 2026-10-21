import pytest
from app.services.bank_markdown import normalize, table
from app.services import bank_vision, bank_ai
from fastapi.testclient import TestClient
from app.main import app
from test_materialhub import context
from test_bank_pdf_ocr import FIXTURES


def test_explicit_tables_keep_cells_math_unicode_and_code_literal():
    t = "项目\t表达式\n逻辑\t$D_8 \\oplus D_7$\n范围\t∑ ≤ x|y"
    md = normalize(t)
    assert "| 项目 | 表达式 |" in md and "| --- | --- |" in md
    assert r"$D_8 \oplus D_7$" in md and r"x\|y" in md
    assert normalize(md) == md
    assert normalize("```text\na\tb\nc\td\n```") == "```text\na\tb\nc\td\n```"
    assert normalize("$$\na\tb\nc\td\n$$") == "$$\na\tb\nc\td\n$$"
    assert "| 输入 | 输出 |" in normalize("输入 | 输出\n0 | ≤ 2")
    assert normalize("$x | y$\n$x | z$") == "$x | y$\n$x | z$"
    html = "<table><tr><th>输入</th><th>输出</th></tr><tr><td>1</td><td>≤ 2</td></tr></table>"
    assert normalize(html) == "| 输入 | 输出 |\n| --- | --- |\n| 1 | ≤ 2 |"
    assert "```html" in normalize('<table><tr><td colspan="2">合并</td></tr></table>')
    with pytest.raises(ValueError):
        table(["a", "b"], [["1"]])


def test_vision_structured_table_becomes_markdown_and_bad_shape_rejected():
    class Fake:
        def __init__(self, bad=False):
            self.bad = bad

        def structured(self, *a, **kw):
            rows = [["1", r"$x_1 \oplus x_2$"]] if not self.bad else [["1"]]
            return bank_vision.Page.model_validate(
                {
                    "blocks": [
                        {
                            "number": "一",
                            "kind": "solution",
                            "stem": "根据下表计算。\n[[table:1]]",
                            "tables": [
                                {
                                    "marker": "[[table:1]]",
                                    "headers": ["编号", "条件"],
                                    "rows": rows,
                                }
                            ],
                        }
                    ],
                    "empty": False,
                }
            ), {}

    r = bank_vision.transcribe(FIXTURES / "question_bank_scan_demo.png", adapter=Fake())
    assert (
        "[[table:" not in r["blocks"][0]["stem"]
        and "| 编号 | 条件 |" in r["blocks"][0]["stem"]
    )
    with pytest.raises(ValueError):
        bank_vision.transcribe(
            FIXTURES / "question_bank_scan_demo.png", adapter=Fake(True)
        )


def test_markdown_is_persisted_downloaded_without_answers_and_owner_checked():
    with TestClient(app) as client:
        h, c = context(client)
        r = client.post(
            f"/api/v1/courses/{c}/question-bank/import",
            headers=h,
            json={
                "title": "Markdown表格",
                "content": "1. 根据表格解释。\n输入\t输出\n0\t$D_8$\n1\t≤ 2\n答案：不应在题目下载中出现",
            },
        )
        assert r.status_code == 201, r.text
        q = r.json()["questions"][0]
        assert q["bank_data"]["content_format"] == "markdown"
        assert "| 输入 | 输出 |" in q["stem"]
        r = client.get(f"/api/v1/past-questions/{q['id']}/markdown", headers=h)
        assert r.status_code == 200 and "text/markdown" in r.headers["content-type"]
        assert "| 输入 | 输出 |" in r.text and "不应在题目下载中出现" not in r.text
        other, _ = context(client)
        assert (
            client.get(
                f"/api/v1/past-questions/{q['id']}/markdown", headers=other
            ).status_code
            == 404
        )


def test_legacy_model_preview_refused_after_model_switch():
    assert bank_ai.MODEL == bank_vision.MODEL == "glm-5.3-flash"
