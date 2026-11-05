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


def test_stream_emits_node_events_then_done(client):
    import json

    rid = _resume(client)
    with client.stream("POST", "/api/applications/stream", json={"resume_id": rid, "job_text": JD}) as r:
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


def test_graph_endpoint(client):
    assert "human_review" in client.get("/api/graph").text
