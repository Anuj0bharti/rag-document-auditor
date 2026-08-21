"""Upload and index the synthetic demo documents through the public API.

Usage: python scripts/load_demo.py --api http://localhost:8000/api
"""
import argparse
import time
from pathlib import Path
import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://localhost:8000/api")
    parser.add_argument("--email", default="demo@rag-auditor.example.org")
    parser.add_argument("--password", default="demo-password-123")
    args = parser.parse_args()
    root = Path(__file__).parents[2]
    with httpx.Client(timeout=30) as client:
        response = client.post(f"{args.api}/auth/register", json={"email": args.email, "password": args.password})
        if response.status_code == 409:
            response = client.post(f"{args.api}/auth/login", json={"email": args.email, "password": args.password})
        response.raise_for_status()
        headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
        workspace = client.post(f"{args.api}/workspaces", headers=headers, json={"name": "Synthetic policy audit demo"})
        if workspace.status_code == 201:
            workspace_id = workspace.json()["id"]
        else:
            existing = client.get(f"{args.api}/workspaces", headers=headers).json()
            workspace_id = next(item["id"] for item in existing if item["name"] == "Synthetic policy audit demo")
        for path in (root / "demo_data").iterdir():
            with path.open("rb") as file:
                response = client.post(f"{args.api}/workspaces/{workspace_id}/documents", headers=headers, files={"file": (path.name, file)})
            if response.status_code not in (201, 409): response.raise_for_status()
        for _ in range(30):
            documents = client.get(f"{args.api}/workspaces/{workspace_id}/documents", headers=headers).json()
            if documents and all(item["status"] in ("READY", "FAILED") for item in documents): break
            time.sleep(1)
        audit = client.post(f"{args.api}/workspaces/{workspace_id}/audit", headers=headers); audit.raise_for_status()
        audit_id = audit.json()["id"]
        for _ in range(30):
            result = client.get(f"{args.api}/audits/{audit_id}", headers=headers).json()
            if result["status"] in ("COMPLETED", "FAILED"): break
            time.sleep(1)
        print(f"Demo workspace: {workspace_id}; audit: {audit_id}; status: {result['status']}")


if __name__ == "__main__":
    main()
