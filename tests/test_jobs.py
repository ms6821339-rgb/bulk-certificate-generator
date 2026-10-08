def test_create_job_returns_202_and_job_id(client, valid_payload):
    response = client.post("/jobs", json=valid_payload)

    assert response.status_code == 202
    body = response.json()
    assert "job_id" in body
    assert body["total"] == 2
    assert body["status_url"] == f"/jobs/{body['job_id']}"



def test_missing_event_name_is_rejected(client, valid_payload):
    del valid_payload["event_name"]

    response = client.post("/jobs", json=valid_payload)

    assert response.status_code == 422


def test_empty_recipient_list_is_rejected(client, valid_payload):
    valid_payload["recipients"] = []

    response = client.post("/jobs", json=valid_payload)

    assert response.status_code == 422


def test_too_many_recipients_is_rejected(client, valid_payload):
    valid_payload["recipients"] = [
        {"name": f"Person {i}", "email": f"p{i}@example.com"} for i in range(5001)
    ]

    response = client.post("/jobs", json=valid_payload)

    assert response.status_code == 422

def test_invalid_recipients_are_marked_failed_with_reason(client, valid_payload):
    valid_payload["recipients"] = [
        {"name": "Asha Rao", "email": "asha@example.com"},
        {"name": "", "email": "ravi@example.com"},
        {"name": "No Email", "email": "not-an-email"},
        {"name": "Asha Again", "email": "asha@example.com"},
    ]

    response = client.post("/jobs", json=valid_payload)
    assert response.status_code == 202

    job = client.get(f"/jobs/{response.json()['job_id']}").json()
    results = {c["recipient_name"]: c for c in job["certificates"]}

    assert results["Asha Rao"]["status"] == "SUCCESS"
    assert results[""]["status"] == "FAILED"
    assert results[""]["error_message"] == "Name is required"
    assert results["No Email"]["error_message"] == "Invalid email address"
    assert results["Asha Again"]["error_message"] == "Duplicate email in this job"



def test_certificate_pdf_is_generated(client, valid_payload):
    from pathlib import Path

    from app.database import SessionLocal
    from app.models import Certificate

    response = client.post("/jobs", json=valid_payload)
    job_id = response.json()["job_id"]

    db = SessionLocal()
    try:
        certs = db.query(Certificate).filter(Certificate.job_id == job_id).all()
        assert len(certs) == 2
        for cert in certs:
            assert cert.status == "SUCCESS"
            path = Path(cert.file_path)
            assert path.exists()
            assert path.read_bytes().startswith(b"%PDF")
    finally:
        db.close()


def test_job_status_all_successful(client, valid_payload):
    response = client.post("/jobs", json=valid_payload)
    job = client.get(f"/jobs/{response.json()['job_id']}").json()

    assert job["status"] == "COMPLETED"
    assert job["total"] == 2
    assert job["succeeded"] == 2
    assert job["failed"] == 0
    assert job["finished_at"] is not None


def test_job_status_with_some_failures(client, valid_payload):
    valid_payload["recipients"].append({"name": "Bad Email", "email": "nope"})

    response = client.post("/jobs", json=valid_payload)
    job = client.get(f"/jobs/{response.json()['job_id']}").json()

    assert job["status"] == "COMPLETED_WITH_ERRORS"
    assert job["total"] == 3
    assert job["succeeded"] == 2
    assert job["failed"] == 1


def test_job_status_all_failed(client, valid_payload):
    valid_payload["recipients"] = [{"name": "Bad", "email": "nope"}]

    response = client.post("/jobs", json=valid_payload)
    job = client.get(f"/jobs/{response.json()['job_id']}").json()

    assert job["status"] == "FAILED"
    assert job["succeeded"] == 0
    assert job["failed"] == 1


def test_unknown_job_returns_404(client):
    response = client.get("/jobs/99999")

    assert response.status_code == 404


def test_one_certificate_failure_does_not_stop_the_others(client, valid_payload, monkeypatch):
    from app.services import generator

    real_generate = generator.generate_certificate

    def flaky_generate(job_id, cert_id, name, event_name, issued_by, issue_date):
        if name == "Ravi Kumar":
            raise RuntimeError("simulated rendering error")
        return real_generate(job_id, cert_id, name, event_name, issued_by, issue_date)

    monkeypatch.setattr(generator, "generate_certificate", flaky_generate)

    valid_payload["recipients"] = [
        {"name": "Asha Rao", "email": "asha@example.com"},
        {"name": "Ravi Kumar", "email": "ravi@example.com"},
        {"name": "Meera Iyer", "email": "meera@example.com"},
    ]

    response = client.post("/jobs", json=valid_payload)
    job = client.get(f"/jobs/{response.json()['job_id']}").json()
    results = {c["recipient_name"]: c for c in job["certificates"]}

    # The crash hit only Ravi
    assert results["Ravi Kumar"]["status"] == "FAILED"
    assert "simulated rendering error" in results["Ravi Kumar"]["error_message"]

    # Everyone else still got a certificate, including the person AFTER the failure
    assert results["Asha Rao"]["status"] == "SUCCESS"
    assert results["Meera Iyer"]["status"] == "SUCCESS"

    # Job totals reflect the mix
    assert job["status"] == "COMPLETED_WITH_ERRORS"
    assert job["succeeded"] == 2
    assert job["failed"] == 1    

