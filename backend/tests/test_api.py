from conftest import auth_headers


def test_upload_process_audit_and_chat(client):
    headers = auth_headers(client)
    workspace = client.post("/api/workspaces", headers=headers, json={"name": "Policy review"}).json()
    payload = b"# Remote Work\n\nEmployees may work remotely up to 3 days per week.\n\n# Other Rule\n\nEmployees may work remotely up to 2 days per week."
    uploaded = client.post(f"/api/workspaces/{workspace['id']}/documents", headers=headers, files={"file": ("policy.txt", payload, "text/plain")})
    assert uploaded.status_code == 201
    documents = client.get(f"/api/workspaces/{workspace['id']}/documents", headers=headers).json()
    assert documents[0]["status"] == "READY"
    audit = client.post(f"/api/workspaces/{workspace['id']}/audit", headers=headers).json()
    details = client.get(f"/api/audits/{audit['id']}", headers=headers).json()
    assert details["status"] == "COMPLETED"
    findings = client.get(f"/api/audits/{audit['id']}/findings", headers=headers).json()
    assert any(item["type"] == "CONTRADICTION" and item["sources"] for item in findings)
    chat = client.post("/api/chat", headers=headers, json={"workspace_id": workspace["id"], "question": "What is the remote work limit?"})
    assert chat.status_code == 200 and chat.json()["sources"]
