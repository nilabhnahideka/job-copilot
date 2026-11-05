JD = "Nimbus AI is hiring a GenAI Engineer. Must have Python and LLM experience. Kubernetes is a plus. " * 2


def _resume(client):
    r = client.post("/api/resumes", data={"text": "Asha Verma - Software Engineer ..."})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_health(client):
    assert client.get("/health").json() == {"ok": True}


def test_full_flow(client):
    rid = _resume(client)

    r = client.post("/api/applications", json={"resume_id": rid, "job_text": JD})
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
        json={"action": "revise", "target": "outreach", "feedback": "less formal"},
    )
    assert r.status_code == 200 and r.json()["awaiting_review"] is True

    r = client.post(f"/api/applications/{aid}/review", json={"action": "approve"})
    assert r.json()["status"] == "ready" and r.json()["awaiting_review"] is False

    # can't review twice
    assert client.post(f"/api/applications/{aid}/review", json={"action": "approve"}).status_code == 409

    r = client.patch(f"/api/applications/{aid}", json={"status": "applied", "notes": "via referral"})
    assert r.json()["status"] == "applied"

    listed = client.get("/api/applications?status=applied").json()
    assert [a["id"] for a in listed] == [aid]

    assert client.delete(f"/api/applications/{aid}").status_code == 204
    assert client.get(f"/api/applications/{aid}").status_code == 404


def test_validation(client):
    assert client.post("/api/resumes").status_code == 422
    assert client.post("/api/applications", json={"resume_id": 999, "job_text": JD}).status_code == 404
    assert client.post("/api/applications", json={"resume_id": 1, "job_text": "too short"}).status_code == 422


def test_revise_requires_target(client):
    rid = _resume(client)
    aid = client.post("/api/applications", json={"resume_id": rid, "job_text": JD}).json()["id"]
    assert client.post(f"/api/applications/{aid}/review", json={"action": "revise"}).status_code == 422


def test_graph_endpoint(client):
    assert "human_review" in client.get("/api/graph").text
