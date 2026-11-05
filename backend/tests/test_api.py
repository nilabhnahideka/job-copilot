"""End-to-end tests of the application flow: analyse, review, track, delete.
Plus the most important rule: users can never see or change each other's data."""

import json

JD = "Nimbus AI is hiring a GenAI Engineer. Must have Python and LLM experience. Kubernetes is a plus. " * 2


def _resume(client, headers) -> int:
    r = client.post("/api/resumes", headers=headers, data={"text": "Asha Verma - Software Engineer ..."})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_health(client):
    assert client.get("/health").json() == {"ok": True}


def test_full_flow(client, auth):
    _resume(client, auth)

    # resume_id is optional: the active resume is used
    r = client.post("/api/applications", headers=auth, json={"job_text": JD})
    assert r.status_code == 201, r.text
    app = r.json()
    assert app["awaiting_review"] is True
    assert app["company"] == "Nimbus AI" and app["title"] == "GenAI Engineer"
    assert app["fit_score"] == 60
    assert app["status"] == "draft"
    assert app["agent"]["cover_letter"]

    aid = app["id"]
    r = client.post(
        f"/api/applications/{aid}/review",
        headers=auth,
        json={"action": "revise", "target": "outreach", "feedback": "less formal"},
    )
    assert r.status_code == 200 and r.json()["awaiting_review"] is True

    r = client.post(f"/api/applications/{aid}/review", headers=auth, json={"action": "approve"})
    assert r.json()["status"] == "ready" and r.json()["awaiting_review"] is False

    # can't review twice
    assert (
        client.post(f"/api/applications/{aid}/review", headers=auth, json={"action": "approve"}).status_code
        == 409
    )

    r = client.patch(
        f"/api/applications/{aid}", headers=auth, json={"status": "applied", "notes": "via referral"}
    )
    assert r.json()["status"] == "applied"

    listed = client.get("/api/applications?status=applied", headers=auth).json()
    assert [a["id"] for a in listed] == [aid]
    assert client.get("/api/applications?status=offer", headers=auth).json() == []

    assert client.delete(f"/api/applications/{aid}", headers=auth).status_code == 204
    assert client.get(f"/api/applications/{aid}", headers=auth).status_code == 404


def test_needs_a_resume_first(client, auth):
    r = client.post("/api/applications", headers=auth, json={"job_text": JD})
    assert r.status_code == 422 and "resume" in r.json()["detail"].lower()


def test_validation(client, auth):
    assert (
        client.post("/api/applications", headers=auth, json={"resume_id": 999, "job_text": JD}).status_code
        == 404
    )
    assert client.post("/api/applications", headers=auth, json={"job_text": "too short"}).status_code == 422


def test_revise_requires_target(client, auth):
    _resume(client, auth)
    aid = client.post("/api/applications", headers=auth, json={"job_text": JD}).json()["id"]
    assert (
        client.post(f"/api/applications/{aid}/review", headers=auth, json={"action": "revise"}).status_code
        == 422
    )


def test_stream_emits_node_events_then_done(client, auth):
    _resume(client, auth)
    with client.stream("POST", "/api/applications/stream", headers=auth, json={"job_text": JD}) as r:
        assert r.status_code == 200
        events = [json.loads(line[6:]) for line in r.iter_lines() if line.startswith("data: ")]

    assert events[0]["type"] == "created"
    nodes = [e["node"] for e in events if e["type"] == "node"]
    assert nodes[:2] == ["parse_job", "match_resume"]
    assert {"tailor_bullets", "check_grounding", "draft_cover_letter", "draft_outreach"} <= set(nodes)
    done = events[-1]
    assert done["type"] == "done"
    assert done["application"]["awaiting_review"] is True
    assert done["application"]["fit_score"] == 60


def test_users_cannot_see_or_change_each_others_data(client, signup):
    asha = signup("asha@example.com")
    ravi = signup("ravi@example.com")

    resume_id = _resume(client, asha)
    aid = client.post("/api/applications", headers=asha, json={"job_text": JD}).json()["id"]
    answer = client.post("/api/profile/answers", headers=asha, json={"question": "Q?", "answer": "A"}).json()

    # Ravi sees nothing in his lists...
    assert client.get("/api/applications", headers=ravi).json() == []
    assert client.get("/api/resumes", headers=ravi).json() == []
    assert client.get("/api/profile/answers", headers=ravi).json() == []
    assert client.get("/api/profile", headers=ravi).json()["data"]["personal"]["email"] == "ravi@example.com"

    # ...and gets 404 for every one of Asha's ids, exactly like ids that don't exist.
    assert client.get(f"/api/applications/{aid}", headers=ravi).status_code == 404
    assert (
        client.patch(f"/api/applications/{aid}", headers=ravi, json={"status": "rejected"}).status_code == 404
    )
    assert (
        client.post(f"/api/applications/{aid}/review", headers=ravi, json={"action": "approve"}).status_code
        == 404
    )
    assert client.delete(f"/api/applications/{aid}", headers=ravi).status_code == 404
    assert client.get(f"/api/resumes/{resume_id}", headers=ravi).status_code == 404
    assert client.get(f"/api/resumes/{resume_id}/file", headers=ravi).status_code == 404
    assert (
        client.post(
            "/api/applications", headers=ravi, json={"resume_id": resume_id, "job_text": JD}
        ).status_code
        == 404
    )
    assert (
        client.put("/api/profile/active-resume", headers=ravi, json={"resume_id": resume_id}).status_code
        == 404
    )
    assert (
        client.patch(f"/api/profile/answers/{answer['id']}", headers=ravi, json={"answer": "x"}).status_code
        == 404
    )
    assert client.delete(f"/api/profile/answers/{answer['id']}", headers=ravi).status_code == 404

    # Asha's application is untouched.
    assert client.get(f"/api/applications/{aid}", headers=asha).json()["status"] == "draft"


def test_graph_endpoint(client):
    assert "human_review" in client.get("/api/graph").text
