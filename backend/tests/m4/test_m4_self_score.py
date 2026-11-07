import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services import question_bank as bank
from tests.m1.test_materialhub import context
from tests.m4.test_question_bank import seed_bank, draw, start


def test_partial_score_range_idempotence_unknown_and_aggregate():
    with TestClient(app) as c:
        h, course = context(c)
        _, topic = seed_bank(
            c,
            h,
            course,
            "1. 有分值题。\n分值：10\n知识标签：综合\n2. 未设分值题。\n知识标签：综合",
        )
        paper = draw(c, h, course, topic, 2)
        known = next(q for q in paper["questions"] if q["points_known"])
        unknown = next(q for q in paper["questions"] if not q["points_known"])
        attempt = start(c, h, paper)
        c.post(f"/api/v1/attempts/{attempt['id']}/submit", headers=h)
        path = f"/api/v1/attempts/{attempt['id']}/self-grades/"
        for value in [-1, 11, 0.5, True]:
            assert (
                c.post(path + known["id"], headers=h, json={"score": value}).status_code
                == 422
            )
        assert (
            c.post(path + known["id"], headers=h, json={"correct": True}).status_code
            == 422
        )
        result = c.post(path + known["id"], headers=h, json={"score": 6})
        assert result.status_code == 200, result.text
        assert result.json()["score"] == 6
        assert result.json()["grading"][known["id"]]["self_correct"] is False
        assert (
            c.post(path + known["id"], headers=h, json={"score": 6}).json()["score"]
            == 6
        )
        assert (
            c.post(path + known["id"], headers=h, json={"score": 7}).status_code == 409
        )
        assert (
            c.post(path + unknown["id"], headers=h, json={"score": 0}).status_code
            == 422
        )
        result = c.post(path + unknown["id"], headers=h, json={"correct": True}).json()
        assert result["score"] == 6 and result["status"] == "SCORED"
        report = c.post(f"/api/v1/courses/{course}/exam-analyses", headers=h).json()
        gaps = c.get(f"/api/v1/exam-analyses/{report['id']}/gaps", headers=h).json()
        assert gaps["topics"][0]["error_count"] == 1


@pytest.mark.parametrize("score", [0, 10])
def test_zero_and_full_self_score(score):
    with TestClient(app) as c:
        h, course = context(c)
        _, topic = seed_bank(c, h, course, "1. 解释。\n分值：10\n知识标签：综合")
        paper = draw(c, h, course, topic, 1)
        attempt = start(c, h, paper)
        submitted = c.post(f"/api/v1/attempts/{attempt['id']}/submit", headers=h).json()
        assert submitted["status"] == "SUBMITTED"
        result = c.post(
            f"/api/v1/attempts/{attempt['id']}/self-grades/{paper['questions'][0]['id']}",
            headers=h,
            json={"score": score},
        ).json()
        assert result["score"] == score and result["status"] == "SCORED"


def test_legacy_bank_placeholder_not_real_points():
    assert not bank.public_question(
        {"id": "old", "source_question_id": "source", "points": 1}
    )["points_known"]
