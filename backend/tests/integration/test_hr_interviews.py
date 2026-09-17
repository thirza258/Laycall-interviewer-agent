import json
from uuid import uuid4

import pytest
from sqlalchemy import select, update

from app.db.models.hr_interview import HrInterview
from app.llm.exceptions import OpenRouterAPIError, OpenRouterTimeoutError
from app.llm.models import LLMResponse


PROFILE = {
    "name": "Alex Morgan", "role": "Backend engineer", "level": "senior",
    "skills": ["Python", "SQL"], "background": "Built a scheduling service at a startup.",
}
FEEDBACK = {
    "summary": "You asked for concrete examples but could explore the candidate's decisions more deeply.",
    "question_quality": 8, "follow_up_quality": 6,
    "strengths": ["Asked about a specific Python project."],
    "improvements": ["Follow up on the candidate's personal contribution."],
    "covered_skills": ["python", "Invented skill"],
    "suggested_questions": ["How did you measure the result of that change?"],
}


def completion(payload):
    return LLMResponse(content=json.dumps(payload), model="test/candidate", finish_reason="stop")


async def create(client, **overrides):
    response = await client.post("/api/v1/hr-interviews", json={"profile": {**PROFILE, **overrides}})
    assert response.status_code == 201, response.text
    return response.json()


def question(text="Tell me about a Python project.", count=0, request_id=None):
    return {"question": text, "expected_turn_count": count, "request_id": str(request_id or uuid4())}


async def test_hr_conversation_and_feedback_are_saved_and_resumable(test_client, fake_llm_client, db_session):
    session = await create(test_client)
    base = f"/api/v1/hr-interviews/{session['id']}"
    assert session["turns"] == []
    assert session["max_turns"] == 30
    fake_llm_client.generate_completion.assert_not_called()

    fake_llm_client.generate_completion.return_value = completion({"answer": "I built a Python scheduling service and owned its queue implementation."})
    first = await test_client.post(base + "/questions", json=question())
    assert first.status_code == 200
    assert len(first.json()["turns"]) == 1

    fake_llm_client.generate_completion.return_value = completion({"answer": "I chose a queue so temporary failures could be retried without losing a job."})
    second = await test_client.post(base + "/questions", json=question("Why did you choose a queue?", 1))
    assert second.status_code == 200
    request = fake_llm_client.generate_completion.call_args.args[0]
    assert "ALWAYS the candidate" in request.messages[0]["content"]
    assert json.loads(request.messages[1]["content"].split("\n", 1)[1]) == PROFILE
    assert request.messages[-3]["content"] == "Tell me about a Python project."
    assert "queue implementation" in request.messages[-2]["content"]
    assert request.messages[-1]["content"] == "Why did you choose a queue?"

    reloaded = await test_client.get(base)
    assert reloaded.json() == second.json()
    fake_llm_client.generate_completion.return_value = completion(FEEDBACK)
    finished = await test_client.post(base + "/finish")
    assert finished.status_code == 200
    report = finished.json()
    assert report["status"] == "completed"
    assert report["feedback"]["covered_skills"] == ["Python"]
    assert report["feedback"]["question_quality"] == 8
    request = fake_llm_client.generate_completion.call_args.args[0]
    assert "HUMAN INTERVIEWER" in request.messages[0]["content"]
    assert len(json.loads(request.messages[1]["content"])["transcript"]) == 2
    assert (await test_client.get(base)).json() == report
    assert (await test_client.post(base + "/finish")).json() == report
    assert fake_llm_client.generate_completion.call_count == 3
    assert (await test_client.post(base + "/questions", json=question(count=2))).status_code == 409
    persisted = (await db_session.execute(select(HrInterview))).scalar_one()
    assert persisted.status == "completed"
    assert len(persisted.turns) == 2


async def test_creation_and_question_retries_are_idempotent(test_client, fake_llm_client):
    session_id = str(uuid4())
    payload = {"id": session_id, "profile": PROFILE}
    first = await test_client.post("/api/v1/hr-interviews", json=payload)
    assert (await test_client.post("/api/v1/hr-interviews", json=payload)).json() == first.json()
    assert (await test_client.post("/api/v1/hr-interviews", json={**payload, "profile": {**PROFILE, "role": "Other role"}})).status_code == 409
    base = f"/api/v1/hr-interviews/{session_id}"
    fake_llm_client.generate_completion.return_value = completion({"answer": "I worked on a Python service."})
    payload = question()
    response = await test_client.post(base + "/questions", json=payload)
    assert response.status_code == 200
    assert (await test_client.post(base + "/questions", json=payload)).json() == response.json()
    assert fake_llm_client.generate_completion.call_count == 1
    assert (await test_client.post(base + "/questions", json={**payload, "question": "A different question?"})).status_code == 409
    assert (await test_client.post(base + "/questions", json=question())).status_code == 409
    assert fake_llm_client.generate_completion.call_count == 1


@pytest.mark.parametrize("bad_profile", [
    {"skills": []}, {"skills": [" "]}, {"skills": ["x" * 61]},
    {"skills": [f"skill{i}" for i in range(13)]}, {"role": " "},
    {"name": " "}, {"level": "expert"}, {"background": "x" * 2001},
])
async def test_invalid_profiles_are_rejected(test_client, bad_profile):
    response = await test_client.post("/api/v1/hr-interviews", json={"profile": {**PROFILE, **bad_profile}})
    assert response.status_code == 422


async def test_skills_are_trimmed_and_deduplicated(test_client):
    session = await create(test_client, skills=[" Python ", "python", "SQL"])
    assert session["profile"]["skills"] == ["Python", "SQL"]


@pytest.mark.parametrize("payload", [
    question(" "), question("x" * 2001), question(count=-1), question(count=31),
    {"question": "Hello?", "expected_turn_count": 0},
])
async def test_invalid_questions_do_not_call_model(test_client, fake_llm_client, payload):
    session = await create(test_client)
    response = await test_client.post(f"/api/v1/hr-interviews/{session['id']}/questions", json=payload)
    assert response.status_code == 422
    fake_llm_client.generate_completion.assert_not_called()


@pytest.mark.parametrize("failure,status", [
    (OpenRouterAPIError("provider secret", 503), 503), (OpenRouterTimeoutError("slow"), 504),
    (TimeoutError(), 504), (completion({"answer": " "}), 503),
])
async def test_failed_generation_can_be_retried_without_losing_history(test_client, fake_llm_client, failure, status):
    session = await create(test_client)
    base = f"/api/v1/hr-interviews/{session['id']}"
    if isinstance(failure, Exception):
        fake_llm_client.generate_completion.side_effect = failure
    else:
        fake_llm_client.generate_completion.return_value = failure
    payload = question()
    response = await test_client.post(base + "/questions", json=payload)
    assert response.status_code == status
    assert "provider secret" not in response.text
    assert (await test_client.get(base)).json()["turns"] == []
    fake_llm_client.generate_completion.side_effect = None
    fake_llm_client.generate_completion.return_value = completion({"answer": "I built a Python application."})
    assert (await test_client.post(base + "/questions", json=payload)).status_code == 200
    fake_llm_client.generate_completion.return_value = completion({"summary": "bad"})
    assert (await test_client.post(base + "/finish")).status_code == 503
    current = (await test_client.get(base)).json()
    assert current["status"] == "in_progress"
    assert len(current["turns"]) == 1
    fake_llm_client.generate_completion.return_value = completion(FEEDBACK)
    assert (await test_client.post(base + "/finish")).status_code == 200


async def test_missing_empty_and_full_sessions(test_client, fake_llm_client, db_session):
    missing = f"/api/v1/hr-interviews/{uuid4()}"
    assert (await test_client.get(missing)).status_code == 404
    assert (await test_client.post(missing + "/questions", json=question())).status_code == 404
    assert (await test_client.post(missing + "/finish")).status_code == 404
    assert (await test_client.get("/api/v1/hr-interviews/invalid")).status_code == 422
    session = await create(test_client)
    base = f"/api/v1/hr-interviews/{session['id']}"
    assert (await test_client.post(base + "/finish")).status_code == 409
    interview = await db_session.get(HrInterview, session["id"])
    interview.turns = [{"request_id": str(uuid4()), "question": "Hello", "answer": "Hi", "created_at": "2026-09-17T00:00:00Z"} for _ in range(30)]
    await db_session.commit()
    assert (await test_client.post(base + "/questions", json=question(count=30))).status_code == 409
    fake_llm_client.generate_completion.assert_not_called()


async def test_concurrent_update_does_not_overwrite_another_response(test_client, fake_llm_client, db_session):
    session = await create(test_client)
    base = f"/api/v1/hr-interviews/{session['id']}"
    winning_turn = {"request_id": str(uuid4()), "question": "A question from another tab", "answer": "Already saved", "created_at": "2026-09-17T00:00:00Z"}

    async def simultaneous_response(_request):
        await db_session.execute(update(HrInterview).where(HrInterview.id == session["id"]).values(revision=1, turns=[winning_turn]))
        await db_session.commit()
        return completion({"answer": "This answer must not overwrite the other tab."})

    fake_llm_client.generate_completion.side_effect = simultaneous_response
    assert (await test_client.post(base + "/questions", json=question())).status_code == 409
    assert (await test_client.get(base)).json()["turns"][0]["answer"] == "Already saved"


async def test_finishing_does_not_drop_a_concurrent_question(test_client, fake_llm_client, db_session):
    session = await create(test_client)
    base = f"/api/v1/hr-interviews/{session['id']}"
    fake_llm_client.generate_completion.return_value = completion({"answer": "I built a Python service."})
    await test_client.post(base + "/questions", json=question())

    async def simultaneous_question(_request):
        interview = await db_session.get(HrInterview, session["id"])
        interview.turns = [*interview.turns, {"request_id": str(uuid4()), "question": "How?", "answer": "With Python", "created_at": "2026-09-17T00:00:00Z"}]
        interview.revision += 1
        await db_session.commit()
        return completion(FEEDBACK)

    fake_llm_client.generate_completion.side_effect = simultaneous_question
    assert (await test_client.post(base + "/finish")).status_code == 409
    reloaded = (await test_client.get(base)).json()
    assert reloaded["status"] == "in_progress"
    assert len(reloaded["turns"]) == 2
