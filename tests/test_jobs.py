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