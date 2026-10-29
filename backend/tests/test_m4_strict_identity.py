"""Strict local file completeness, atomic identity review and current progress."""

import io
import json
import zipfile
from uuid import uuid4
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models import PastPaper
from app.services.bank_strict_markdown import parse
from app.services.exam_report_evidence import confirmed_evidence
from app.services.m2_supplements import validate as validate_supplement, KEY
from app.services.bank_identity import validate as validate_identity
from app.workers.materials import drain_jobs
from test_materialhub import context, upload
from test_question_bank import seed_bank
from test_mistake_redo import seed_mistakes

CONTENT = r"""# Hustudy 题库 v1

## 题目 1-1
### 题型
解答题
### 公共条件
已知 $x=2$，请保留公共条件。
### 题干
1. 正文中的普通题号不能拆题。
（2）括号内容也不能遗漏。

| 参数 | 数值 |
| --- | --- |
| 输入 | $x$ |

### 参考答案
$$
\frac{x^2}{2}=2
$$
### 知识标签
综合

## 题目 1-2
### 题型
选择题
### 题干
选择数值。
### 选项
A. $1$
B. $2$
C. $3$
D. $4$
### 参考答案
B
"""


def test_strict_complete_content_and_protected_fences():
    rows = parse(CONTENT)
    assert len(rows) == 2
    assert "（2）" in rows[0]["stem"] and "| 输入 | $x$ |" in rows[0]["stem"]
    assert rows[0]["stem"].startswith("已知 $x=2$")
    assert rows[0]["answer"] == "$$\n\\frac{x^2}{2}=2\n$$"
    assert rows[1]["options"] == ["$1$", "$2$", "$3$", "$4$"]
    source = CONTENT.replace(
        "1. 正文中的普通题号不能拆题。",
        "```markdown\n## 题目 99\n### 题干\n```\n1. 正文中的普通题号不能拆题。",
    )
    assert len(parse(source)) == 2


@pytest.mark.parametrize(
    "text",
    [
        CONTENT.replace("## 题目 1-2", "## 题目 1-1"),
        CONTENT.replace("### 题干", "### 未知字段", 1),
        CONTENT.replace("### 题型", "孤立正文\n### 题型", 1),
        CONTENT.replace("$x=2$", "$x=2"),
        CONTENT.replace("| --- | --- |", "| --- |"),
        CONTENT.replace("### 参考答案", "### 题干", 1),
        CONTENT.replace("\\frac{x^2}{2}", "\\frac{x^2}{2"),
        CONTENT.replace("### 题型\n解答题", "### 题型\n填空题", 1),
    ],
)
def test_strict_invalid_content_is_rejected_without_truncation(text):
    with pytest.raises(HTTPException) as exc:
        parse(text)
    assert exc.value.status_code == 422 and "行" in str(exc.value.detail)


def test_local_upload_zip_preflight_and_ai_preserves_multiformat():
    with TestClient(app) as c:
        h, course = context(c)
        route = f"/api/v1/courses/{course}/question-bank"
        assert (
            c.post(
                route + "/files", headers=h, files={"file": ("bad.pdf", b"bad")}
            ).status_code
            == 422
        )
        assert (
            c.post(
                route + "/files", headers=h, files={"file": ("bad.md", b"1. Legacy")}
            ).status_code
            == 422
        )
        r = c.post(
            route + "/files", headers=h, files={"file": ("good.md", CONTENT.encode())}
        )
        assert r.status_code == 202, r.text
        premature = c.post(
            route + "/import",
            headers=h,
            json={
                "title": "严格题库",
                "version_id": r.json()["resource_id"],
                "strict_markdown": True,
            },
        )
        assert premature.status_code == 409
        drain_jobs()
        imported = c.post(
            route + "/import",
            headers=h,
            json={
                "title": "严格题库",
                "version_id": r.json()["resource_id"],
                "strict_markdown": True,
            },
        )
        assert imported.status_code == 201, imported.text
        imported_rows = imported.json()["questions"]
        assert all(
            q["bank_data"]["source_version_id"] == r.json()["resource_id"]
            for q in imported_rows
        )
        assert all(q["bank_data"]["citations"] for q in imported_rows)
        q = imported_rows[0]
        assert q["answer"] == parse(CONTENT)[0]["answer"]
        assert q["stem"] == parse(CONTENT)[0]["stem"]
        first_citations = q["bank_data"]["citations"]
        assert not any("选择数值" in citation["quote"] for citation in first_citations)
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as z:
            z.writestr("good.md", CONTENT)
            z.writestr("bad.md", "invalid")
        before = c.get(route + "/files", headers=h).json()
        bad = c.post(
            route + "/archives", headers=h, files={"file": ("a.zip", data.getvalue())}
        )
        assert bad.status_code == 422
        assert c.get(route + "/files", headers=h).json() == before
        ai = c.post(
            route + "/files",
            headers=h,
            data={"mode": "ai"},
            files={"file": ("legacy.md", b"1. Explain protocol.")},
        )
        assert ai.status_code == 202, ai.text
        assert (
            c.post(
                f"/api/v1/past-papers/{imported.json()['id']}/confirm", headers=h
            ).status_code
            == 200
        )
        from app.services.question_bank import eligible_questions

        uid = c.get("/api/v1/auth/me", headers=h).json()["id"]
        with SessionLocal() as db:
            assert len(eligible_questions(db, uid, course)) == 2
        version = c.get(f"/api/v1/versions/{r.json()['resource_id']}", headers=h).json()
        assert (
            c.delete(
                f"/api/v1/documents/{version['document_id']}", headers=h
            ).status_code
            == 204
        )
        with SessionLocal() as db:
            assert eligible_questions(db, uid, course) == []


def papers(c, h, course):
    return c.get(f"/api/v1/courses/{course}/question-bank/papers", headers=h).json()


def test_identity_atomic_conflict_idempotency_revocation_and_permissions():
    with TestClient(app) as c:
        h, course = context(c)
        foreign, _ = context(c)
        for n in [1, 2]:
            seed_bank(c, h, course, f"1. 解释概念{n}。\n知识标签：综合")
        route = f"/api/v1/courses/{course}/question-bank/metadata-batch"
        rows = papers(c, h, course)
        source = [
            dict(
                paper_id=p["id"],
                expected_revision=1,
                provenance="本人收集的课程考试试卷",
            )
            for p in rows
        ]
        assert c.post(route, headers=foreign, json={"items": source}).status_code == 404
        assert c.post(route, headers=h, json={"items": source}).status_code == 200
        confirm = [
            dict(
                paper_id=p["id"],
                expected_revision=2,
                exam_identity={"kind": "past_exam", "confirmed": True},
            )
            for p in rows
        ]
        confirm[1]["expected_revision"] = 1
        assert c.post(route, headers=h, json={"items": confirm}).status_code == 409
        assert all(
            not p["metadata"].get("exam_identity", {}).get("confirmed")
            for p in papers(c, h, course)
        )
        confirm[1]["expected_revision"] = 2
        assert c.post(route, headers=h, json={"items": confirm}).status_code == 200
        confirmed = papers(c, h, course)
        assert all(p["metadata"]["exam_identity"]["confirmed"] for p in confirmed)
        retry = [
            dict(
                paper_id=p["id"],
                expected_revision=3,
                exam_identity={"kind": "past_exam", "confirmed": True},
            )
            for p in rows
        ]
        assert c.post(route, headers=h, json={"items": retry}).status_code == 200
        assert papers(c, h, course) == confirmed
        p = confirmed[0]
        r = c.patch(
            f"/api/v1/past-papers/{p['id']}/metadata",
            headers=h,
            json={"expected_revision": 3, "year": 2023},
        )
        assert (
            r.status_code == 200
            and not r.json()["metadata"]["exam_identity"]["confirmed"]
        )
        bad = c.patch(
            f"/api/v1/past-papers/{p['id']}/metadata",
            headers=h,
            json={
                "expected_revision": 4,
                "exam_identity": {"kind": "exercise", "confirmed": True},
            },
        )
        assert bad.status_code == 422


def test_identity_evidence_invalidation_including_reconfirmation():
    with TestClient(app) as c:
        h, course = context(c)
        paper, tid = seed_bank(c, h, course, "1. 解释窗口机制。\n知识标签：综合")
        job = upload(c, h, course, "窗口机制调节发送。")
        drain_jobs()
        chunk = c.get(
            f"/api/v1/versions/{job['resource_id']}/chunks", headers=h
        ).json()[0]
        uid = c.get("/api/v1/auth/me", headers=h).json()["id"]
        scope = [
            dict(
                version_id=job["resource_id"], source_id=chunk["id"], text=chunk["text"]
            )
        ]
        topic = next(
            t
            for t in c.get(f"/api/v1/courses/{course}/topics", headers=h).json()
            if t["id"] == tid
        )
        assert (
            c.put(
                f"/api/v1/topics/{tid}/sources",
                headers=h,
                json={
                    "revision": topic["revision"],
                    "version_id": job["resource_id"],
                    "chunk_id": chunk["id"],
                    "quote": chunk["text"],
                },
            ).status_code
            == 200
        )
        q = paper["questions"][0]
        assert (
            c.post(
                f"/api/v1/courses/{course}/question-bank/batch",
                headers=h,
                json={
                    "question_ids": [q["id"]],
                    "revisions": {q["id"]: q["revision"]},
                    "action": "review_topics",
                },
            ).status_code
            == 200
        )
        with SessionLocal() as db:
            assert confirmed_evidence(db, uid, course, scope) == []
            with pytest.raises(HTTPException):
                confirmed_evidence(db, uid, course, scope, [paper["id"]])
        url = f"/api/v1/past-papers/{paper['id']}/metadata"
        assert (
            c.patch(
                url,
                headers=h,
                json={"expected_revision": 1, "provenance": "课程历年试卷"},
            ).status_code
            == 200
        )
        assert (
            c.patch(
                url,
                headers=h,
                json={
                    "expected_revision": 2,
                    "exam_identity": {"kind": "past_exam", "confirmed": True},
                },
            ).status_code
            == 200
        )
        with SessionLocal() as db:
            evidence = confirmed_evidence(db, uid, course, scope)
            assert len(evidence) == 1
        assert (
            c.patch(
                url,
                headers=h,
                json={
                    "expected_revision": 3,
                    "exam_identity": {"kind": "past_exam", "confirmed": False},
                },
            ).status_code
            == 200
        )
        assert (
            c.patch(
                url,
                headers=h,
                json={
                    "expected_revision": 4,
                    "exam_identity": {"kind": "past_exam", "confirmed": True},
                },
            ).status_code
            == 200
        )
        with SessionLocal() as db:
            assert confirmed_evidence(db, uid, course, scope) != evidence
            saved = [
                {
                    KEY: dict(
                        version=2,
                        automatic_report_sources=True,
                        evidence_scope=scope,
                        teacher_marks=[],
                        exam_evidence=evidence,
                        notes=[],
                    )
                }
            ]
            with pytest.raises(HTTPException):
                validate_supplement(db, uid, course, saved)


@pytest.mark.parametrize(
    "identity",
    [
        {"kind": "exercise", "confirmed": True},
        {"kind": "past_exam", "confirmed": "true"},
        {"kind": "past_exam", "confirmed": True, "revision": -1},
        {"kind": "past_exam", "confirmed": True, "confirmed_at": "invalid"},
    ],
)
def test_backup_identity_validation(identity):
    with pytest.raises(ValueError):
        validate_identity(identity)


def test_current_mastery_is_separate_from_first_attempt():
    with TestClient(app) as c:
        h, course = context(c)
        mistakes, _ = seed_mistakes(c, h, course, 1)
        report = c.post(f"/api/v1/courses/{course}/exam-analyses", headers=h).json()
        gap = f"/api/v1/exam-analyses/{report['id']}/gaps"
        assert c.get(gap, headers=h).json()["topics"][0]["current_pending"] == 1
        path = f"/api/v1/mistakes/{mistakes[0]['id']}/redoes"
        redo = c.post(path, headers=h, json={"request_id": str(uuid4())}).json()
        answer = "ABCD"[redo["question"]["options"].index("甲")]
        assert (
            c.post(
                path + "/" + redo["id"] + "/submit", headers=h, json={"answer": answer}
            ).status_code
            == 200
        )
        row = c.get(gap, headers=h).json()["topics"][0]
        assert (
            row["error_count"] == 1
            and row["current_pending"] == 0
            and row["current_mastered"] == 1
        )


def test_unsupported_formula_rejected_by_actual_katex():
    with pytest.raises(HTTPException) as exc:
        parse(CONTENT.replace(r"\frac", r"\notARealMathCommand"))
    assert "KaTeX" in str(exc.value.detail)


def test_identity_account_backup_preserves_and_course_import_requires_reconfirmation():
    from test_account_backups import exported, restored, empty_account
    from test_portable_packages import all_selection, preview, request_for

    with TestClient(app) as c:
        h, course = context(c)
        paper, _ = seed_bank(c, h, course, "1. 说明传输机制。\n知识标签：综合")
        url = f"/api/v1/past-papers/{paper['id']}/metadata"
        assert (
            c.patch(
                url,
                headers=h,
                json={"expected_revision": 1, "provenance": "自制考试来源声明"},
            ).status_code
            == 200
        )
        assert (
            c.patch(
                url,
                headers=h,
                json={
                    "expected_revision": 2,
                    "exam_identity": {"kind": "past_exam", "confirmed": True},
                },
            ).status_code
            == 200
        )
        catalog = c.get(f"/api/v1/courses/{course}/packages/catalog", headers=h).json()
        raw = c.post(
            "/api/v1/packages/export",
            headers=h,
            json={
                "course_id": course,
                "kind": "course",
                "selection": all_selection(catalog),
            },
        )
        assert raw.status_code == 200, raw.text
        viewed = preview(c, h, raw.content)
        assert viewed.status_code == 200, viewed.text
        assert any("重新确认" in warning for warning in viewed.json()["warnings"])
        imported = c.post(
            "/api/v1/packages/import", headers=h, json=request_for(viewed.json())
        )
        assert imported.status_code == 200, imported.text
        new_course = imported.json()["course_id"]
        rows = papers(c, h, new_course)
        assert rows and all(
            not row["metadata"]["exam_identity"]["confirmed"] for row in rows
        )

        # Account restore intentionally preserves UUIDs and requires a fresh database.
        # Remove only the disposable source user to simulate that boundary.
        from app.models import User

        archive, _ = exported(c, h)
        source_uid = c.get("/api/v1/auth/me", headers=h).json()["id"]
        with SessionLocal() as db:
            db.delete(db.get(User, source_uid))
            db.commit()
        target, _ = empty_account(c)
        state = restored(c, target, archive)
        assert state["job"]["status"] == "SUCCEEDED", state
        with SessionLocal() as db:
            stored = db.get(PastPaper, paper["id"])
            assert (
                json.loads(stored.bank_meta_json)["exam_identity"]["confirmed"] is True
            )
