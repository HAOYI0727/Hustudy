from pathlib import Path
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.services import question_bank as bank, exam_analysis
from app.services.bank_strict_markdown import parse
from test_materialhub import context


def test_duplicates_preserved_except_analysis_and_blueprint_scope():
    with TestClient(app) as client:
        h, course = context(client)
        url = f"/api/v1/courses/{course}/question-bank/import"
        payload = {"title":"重复内容", "content":"1. 完全相同题干。\n知识标签：综合\n2. 完全相同题干。\n知识标签：综合"}
        one = client.post(url,headers=h,json=payload).json()
        two = client.post(url,headers=h,json=payload).json()
        assert one["id"] != two["id"]
        for p in [one,two]:
            assert len(p["questions"]) == 2
            assert client.post(f"/api/v1/past-papers/{p['id']}/confirm",headers=h).status_code == 200
        uid=client.get('/api/v1/auth/me',headers=h).json()['id']
        with SessionLocal() as db:
            assert len(bank.eligible_questions(db,uid,course)) == 4
            assert len(bank.eligible_questions(db,uid,course,deduplicate=True)) == 1
            assert len(exam_analysis.inputs(db,uid,course)[2]) == 1
        draw=client.post(f"/api/v1/courses/{course}/question-bank/draw",headers=h,json={"request_id":str(uuid4()),"count":4,"topic_ids":[]})
        assert draw.status_code == 201, draw.text
        assert len(draw.json()["questions"]) == 4
        request_id=str(uuid4())
        three=client.post(url,headers=h,json=payload|{"request_id":request_id}).json()
        assert client.post(url,headers=h,json=payload|{"request_id":request_id}).json()["id"] == three["id"]
        assert client.post(url,headers=h,json=payload|{"request_id":request_id,"title":"变参"}).status_code == 409


def test_downloadable_complete_markdown_is_valid_and_has_all_sections():
    raw=(Path(__file__).resolve().parents[2]/'frontend/src/features/exams/bankExample.md').read_text(encoding='utf-8')
    rows=parse(raw)
    assert len(rows) == 3
    assert '| --- |' in raw and '\\oplus' in raw and '∑' in raw and '```text' in raw
    assert rows[-1]['answer'] is None
