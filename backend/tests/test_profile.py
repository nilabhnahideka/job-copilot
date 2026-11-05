"""Tests for the profile, resume upload/download, prefilling, and saved answers."""

from tests.fakes import make_pdf


def _upload_pdf(client, headers, name="resume.pdf"):
    pdf = make_pdf("Asha Verma Software Engineer Python FastAPI")
    r = client.post("/api/resumes", headers=headers, files={"file": (name, pdf, "application/pdf")})
    assert r.status_code == 201, r.text
    return r.json(), pdf


def test_new_profile_lists_what_is_missing(client, auth):
    p = client.get("/api/profile", headers=auth).json()
    assert p["active_resume"] is None
    assert "Resume" in p["missing"] and "Phone" in p["missing"] and "Expected salary" in p["missing"]
    assert "Email" not in p["missing"]  # filled from sign-up


def test_save_profile_and_read_it_back(client, auth):
    data = client.get("/api/profile", headers=auth).json()["data"]
    data["personal"].update(first_name="Asha", last_name="Verma", phone="+91 98765 43210", city="Pune")
    data["preferences"].update(
        titles=["GenAI Engineer"],
        locations=["Pune", "Bengaluru"],
        work_modes=["remote", "hybrid"],
        job_types=["full_time"],
        experience_level="entry",
        salary_min_lpa=8,
        salary_max_lpa=14,
    )
    data["answers"].update(notice_period_days=30, expected_ctc_lpa=12, willing_to_relocate="yes")
    data["education"]["entries"] = [
        {"degree": "B.Tech", "institution": "NIT Trichy", "end_year": 2023, "grade": "8.4 CGPA"}
    ]

    r = client.put("/api/profile", headers=auth, json=data)
    assert r.status_code == 200, r.text
    saved = client.get("/api/profile", headers=auth).json()
    assert saved["data"]["preferences"]["locations"] == ["Pune", "Bengaluru"]
    assert saved["data"]["education"]["entries"][0]["grade"] == "8.4 CGPA"
    assert saved["missing"] == ["Resume"]  # everything else required is filled


def test_profile_validation(client, auth):
    data = client.get("/api/profile", headers=auth).json()["data"]
    bad_range = {**data, "preferences": {**data["preferences"], "salary_min_lpa": 20, "salary_max_lpa": 10}}
    assert client.put("/api/profile", headers=auth, json=bad_range).status_code == 422
    bad_choice = {**data, "preferences": {**data["preferences"], "work_modes": ["on the moon"]}}
    assert client.put("/api/profile", headers=auth, json=bad_choice).status_code == 422
    bad_notice = {**data, "answers": {**data["answers"], "notice_period_days": -5}}
    assert client.put("/api/profile", headers=auth, json=bad_notice).status_code == 422


def test_upload_pdf_stores_original_file_and_prefills_empty_fields(client, auth):
    # Something typed by the user must never be overwritten by the resume.
    data = client.get("/api/profile", headers=auth).json()["data"]
    data["personal"]["city"] = "Mumbai"
    client.put("/api/profile", headers=auth, json=data)

    resume, pdf = _upload_pdf(client, auth)
    assert resume["has_file"] is True and resume["file_name"] == "resume.pdf"
    assert "First name" in resume["prefilled"] and "Phone" in resume["prefilled"]
    assert "City" not in resume["prefilled"]

    profile = client.get("/api/profile", headers=auth).json()
    personal = profile["data"]["personal"]
    assert personal["first_name"] == "Asha" and personal["last_name"] == "Verma"
    assert personal["phone"] == "+91 98765 43210"
    assert personal["city"] == "Mumbai"  # kept
    assert personal["email"] == "asha@example.com"  # sign-up email kept, not the resume's
    assert profile["data"]["work"]["current_company"] == "Acme"
    assert profile["active_resume"]["id"] == resume["id"]
    assert "Resume" not in profile["missing"]

    download = client.get(f"/api/resumes/{resume['id']}/file", headers=auth)
    assert download.status_code == 200
    assert download.content == pdf  # byte-for-byte the uploaded file
    assert download.headers["content-type"] == "application/pdf"


def test_newest_upload_becomes_active_and_can_be_switched_back(client, auth):
    first, _ = _upload_pdf(client, auth, "old.pdf")
    second, _ = _upload_pdf(client, auth, "new.pdf")
    assert client.get("/api/profile", headers=auth).json()["active_resume"]["id"] == second["id"]

    r = client.put("/api/profile/active-resume", headers=auth, json={"resume_id": first["id"]})
    assert r.json()["active_resume"]["file_name"] == "old.pdf"


def test_upload_rejects_bad_files(client, auth):
    fake = client.post(
        "/api/resumes", headers=auth, files={"file": ("cv.pdf", b"not a pdf", "application/pdf")}
    )
    assert fake.status_code == 422
    word = client.post(
        "/api/resumes", headers=auth, files={"file": ("cv.docx", b"PK..", "application/octet-stream")}
    )
    assert word.status_code == 422
    assert client.post("/api/resumes", headers=auth).status_code == 422


def test_pasted_resume_has_no_file_to_download(client, auth):
    r = client.post("/api/resumes", headers=auth, data={"text": "Asha Verma, Software Engineer, Python"})
    assert r.status_code == 201 and r.json()["has_file"] is False
    assert client.get(f"/api/resumes/{r.json()['id']}/file", headers=auth).status_code == 404


def test_saved_answers_crud_and_dedupe(client, auth):
    a = client.post(
        "/api/profile/answers", headers=auth, json={"question": "Why do you want to join us?", "answer": "v1"}
    )
    assert a.status_code == 201
    # Same question with different case/punctuation updates the existing answer.
    b = client.post(
        "/api/profile/answers", headers=auth, json={"question": "why do you want to join us", "answer": "v2"}
    )
    assert b.json()["id"] == a.json()["id"] and b.json()["answer"] == "v2"

    other = client.post(
        "/api/profile/answers", headers=auth, json={"question": "Notice period?", "answer": "30 days"}
    ).json()
    clash = client.patch(
        f"/api/profile/answers/{other['id']}", headers=auth, json={"question": "Why do you want to join us?"}
    )
    assert clash.status_code == 409

    edited = client.patch(f"/api/profile/answers/{other['id']}", headers=auth, json={"answer": "Immediate"})
    assert edited.json()["answer"] == "Immediate"
    assert len(client.get("/api/profile/answers", headers=auth).json()) == 2

    assert client.delete(f"/api/profile/answers/{other['id']}", headers=auth).status_code == 204
    assert [x["answer"] for x in client.get("/api/profile/answers", headers=auth).json()] == ["v2"]
