import io
from types import SimpleNamespace
from pydantic import SecretStr
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.models import PastQuestion
from app.core.database import SessionLocal
from app.services import bank_answer_import as service
from test_materialhub import context
from test_question_bank import seed_bank


@pytest.mark.parametrize("image", [False, True])
def test_answer_only_match_fill_missing_images_permissions_and_apply(
    monkeypatch, image
):
    monkeypatch.setattr(
        "app.core.config.get_user_settings",
        lambda _: SimpleNamespace(zhipu_api_key=SecretStr("mock-only")),
    )
    fingerprint = {
        "model": "mock-vision",
        "endpoint": "https://example.invalid",
        "credential_revision": "test",
    }
    monkeypatch.setattr(service.bank_vision, "fingerprint", lambda _: fingerprint)
    monkeypatch.setattr(service.bank_vision, "require_config", lambda _: None)
    with TestClient(app) as client:
        headers, course = context(client)
        paper, _ = seed_bank(
            client,
            headers,
            course,
            "1. 解释事务。\n知识标签：数据库\n2. 解释索引。\n知识标签：数据库\n",
        )
        questions = paper["questions"]
        identity = questions[0]["id"]
        seen = []

        def structured(*args, **kwargs):
            seen.append((args, kwargs))
            return service.Output(
                matches=[
                    service.Match(
                        question_id=identity,
                        answer="事务的原文参考答案",
                        box=[0.1, 0.8, 0.9, 0.9] if image else None,
                        reason="答案页明确标注第一题",
                    )
                ]
            ), {}

        monkeypatch.setattr(
            service.bank_vision,
            "provider",
            lambda *args: SimpleNamespace(structured=structured),
        )
        if image:
            data = io.BytesIO()
            Image.new("RGB", (200, 300), "white").save(data, format="PNG")
            name, raw = "answers.png", data.getvalue()
        else:
            name, raw = "answers.md", "1. 事务的原文参考答案".encode()
        response = client.post(
            f"/api/v1/past-papers/{paper['id']}/answer-imports",
            headers=headers,
            files={"file": (name, raw)},
        )
        assert response.status_code == 201, response.text
        preview = response.json()
        assert not seen
        route = f"/api/v1/answer-imports/{preview['id']}"
        assert (
            client.post(
                route + "/confirm", headers=headers, json={"confirm_remote_send": True}
            ).status_code
            == 200
        )
        assert service.run_once()
        result = client.get(route, headers=headers).json()
        assert result["status"] == "SUCCEEDED", result
        assert len([r for r in result["results"] if r.get("question_id")]) == 2
        assert any(r.get("answer") == "略" for r in result["results"])
        assert "解释事务" in seen[0][0][1][0]["text"]
        if image:
            assert seen[0][1]["images"] and any(
                "![[asset:" in r.get("answer", "") for r in result["results"]
            )
        other, _ = context(client)
        assert client.get(route, headers=other).status_code == 404
        if image:
            import re
            from app.models import Asset
            index=next(i for i,r in enumerate(result["results"]) if "![[asset:" in r.get("answer",""))
            old_answer=result["results"][index]["answer"]
            asset_id=re.search(r"asset:([0-9a-f-]{36})",old_answer)[1]
            crop={"result_index":index,"asset_id":asset_id,"box":[0,0,0.5,0.5],"expected_answer":old_answer}
            assert client.post(route+"/crop",headers=other,json=crop).status_code==404
            cropped=client.post(route+"/crop",headers=headers,json=crop)
            assert cropped.status_code==200,cropped.text
            updated=cropped.json()["results"][index]["answer"]
            assert "事务的原文参考答案" in updated and asset_id not in updated
            cropped_id=re.search(r"asset:([0-9a-f-]{36})",updated)[1]
            with SessionLocal() as db:
                with Image.open(db.get(Asset,cropped_id).storage_path) as saved:
                    assert saved.size==(100,150)
            assert client.post(route+"/crop",headers=headers,json=crop).status_code==409
            recrop={"result_index":index,"asset_id":cropped_id,"source_asset_id":result["sources"][0]["asset_id"],"box":[0,0,0.25,0.25],"expected_answer":updated}
            assert client.post(route+"/crop",headers=headers,json=recrop|{"source_asset_id":"not-in-file"}).status_code==422
            again=client.post(route+"/crop",headers=headers,json=recrop)
            assert again.status_code==200,again.text
            updated=again.json()["results"][index]["answer"]
            cropped_id=re.search(r"asset:([0-9a-f-]{36})",updated)[1]
            with SessionLocal() as db:
                with Image.open(db.get(Asset,cropped_id).storage_path) as saved:
                    assert saved.size==(50,75)
            removal={"result_index":index,"asset_id":cropped_id,"expected_answer":updated}
            assert client.post(route+"/remove-image",headers=other,json=removal).status_code==404
            removed=client.post(route+"/remove-image",headers=headers,json=removal)
            assert removed.status_code==200,removed.text
            answer=removed.json()["results"][index]["answer"]
            assert "![[asset:" not in answer and "事务的原文参考答案" in answer
            assert client.post(route+"/remove-image",headers=headers,json=removal).status_code==409
            added=client.post(route+"/add-images",headers=headers,json={
                "result_index":index,"expected_answer":answer,"images":{cropped_id:asset_id}})
            assert added.status_code==200,added.text
            assert cropped_id in added.json()["results"][index]["answer"]
        payload = {"question_ids": [q["id"] for q in questions], "overwrite": False}
        with SessionLocal() as db:
            changed_question = db.get(PastQuestion, identity)
            changed_question.revision += 1
            db.commit()
        assert (
            client.post(route + "/apply", headers=headers, json=payload).status_code
            == 409
        )
        with SessionLocal() as db:
            changed_question = db.get(PastQuestion, identity)
            changed_question.revision -= 1
            db.commit()
        assert (
            client.post(route + "/apply", headers=headers, json=payload).status_code
            == 200
        )
        assert (
            client.post(route + "/apply", headers=headers, json=payload).status_code
            == 200
        )
        with SessionLocal() as db:
            rows = db.scalars(
                select(PastQuestion).where(PastQuestion.paper_id == paper["id"])
            ).all()
            assert all(q.status == "DRAFT" and q.answer for q in rows)


def test_delete_saved_answer_task(monkeypatch):
    monkeypatch.setattr("app.core.config.get_user_settings", lambda _: SimpleNamespace(zhipu_api_key=SecretStr("mock-only")))
    monkeypatch.setattr(service.bank_vision,"fingerprint",lambda _: {"model":"mock","endpoint":"mock","credential_revision":1})
    with TestClient(app) as client:
        headers,course=context(client)
        paper,_=seed_bank(client,headers,course,"1. 说明。\n知识标签：综合\n")
        preview=client.post(f"/api/v1/past-papers/{paper['id']}/answer-imports",headers=headers,files={"file":("answer.md","参考答案".encode())}).json()
        path=f"/api/v1/answer-imports/{preview['id']}"
        from app.models import BankAnswerImport, ProcessingJob
        with SessionLocal() as db:
            row=db.get(BankAnswerImport,preview["id"])
            job=ProcessingJob(user_id=row.user_id,type="BANK_ANSWERS",resource_id=row.id,status="FAILED")
            db.add(job)
            db.flush()
            row.job_id=job.id
            row.status="FAILED"
            db.commit()
        other,_=context(client)
        assert client.delete(path,headers=other).status_code==404
        assert client.delete(path,headers=headers).status_code==204
        assert client.get(path,headers=headers).status_code==404
        assert client.get(f"/api/v1/past-papers/{paper['id']}/answer-imports",headers=headers).json()==[]
