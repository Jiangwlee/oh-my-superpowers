#!/usr/bin/env python3
"""Import n8n workflow JSON file into running n8n instance."""

from __future__ import annotations

import json
import sys
import urllib.request
import urllib.error


def import_workflow(
    workflow_path: str,
    n8n_url: str = "http://localhost:10003",
    api_key: str | None = None,
) -> dict:
    """Import workflow to n8n.

    Args:
        workflow_path: Path to workflow JSON file.
        n8n_url: n8n API base URL.
        api_key: Optional API key for authentication.

    Returns:
        Workflow import result.
    """
    # Read workflow file
    with open(workflow_path, "r", encoding="utf-8") as f:
        workflow_data = json.load(f)

    # Prepare request
    url = f"{n8n_url}/rest/workflows"
    headers = {
        "Content-Type": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    data = json.dumps(workflow_data).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            print(f"✓ Workflow imported successfully!")
            print(f"  Name: {result.get('name', 'Unknown')}")
            print(f"  ID: {result.get('id', 'N/A')}")
            print(f"  Active: {result.get('active', False)}")
            return result
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"✗ Import failed: {e.code}")
        print(f"  Error: {error_body}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Import failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import-n8n-workflow.py <workflow.json> [n8n_url]")
        sys.exit(1)

    workflow_path = sys.argv[1]
    n8n_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:10003"

    import_workflow(workflow_path, n8n_url)
