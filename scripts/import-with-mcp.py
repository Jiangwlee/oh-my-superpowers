#!/usr/bin/env python3
"""Import n8n workflow using MCP tools."""

from __future__ import annotations

import json
import subprocess
import sys


def create_mcp_config():
    """Create MCP configuration for n8n-mcp."""
    config = {
        "mcpServers": {
            "n8n-mcp": {
                "command": "npx",
                "args": ["-y", "n8n-mcp"],
                "env": {
                    "MCP_MODE": "stdio",
                    "LOG_LEVEL": "error",
                    "DISABLE_CONSOLE_OUTPUT": "true",
                    "N8N_API_URL": "http://localhost:10003",
                    "N8N_API_KEY": "${N8N_API_KEY}"
                }
            }
        }
    }
    
    # Write to temp file
    with open("/tmp/mcp-config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    return "/tmp/mcp-config.json"


def test_mcp_connection():
    """Test if MCP connection works."""
    try:
        result = subprocess.run(
            ["npx", "-y", "n8n-mcp", "--test"],
            capture_output=True,
            text=True,
            timeout=30
        )
        print("MCP Test Result:")
        print(result.stdout)
        if result.stderr:
            print("Stderr:", result.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"MCP test failed: {e}")
        return False


def import_workflow_via_mcp(workflow_path: str):
    """Import workflow using MCP tools (requires interactive mode)."""
    mcp_config = create_mcp_config()
    
    print("=" * 60)
    print("n8n MCP Workflow Import")
    print("=" * 60)
    print()
    print("To import the workflow, you need to:")
    print()
    print("1. Configure your AI agent/editor to use this MCP config:")
    print(f"   {mcp_config}")
    print()
    print("2. Then use the MCP tool 'n8n-create-workflow' or similar")
    print("   with the following JSON content:")
    print()
    print("-" * 60)
    
    # Read and display workflow
    with open(workflow_path, "r", encoding="utf-8") as f:
        workflow_data = json.load(f)
    
    print(json.dumps(workflow_data, indent=2, ensure_ascii=False))
    print("-" * 60)
    print()
    print("Alternative: Use n8n UI directly")
    print("  - Open: http://localhost:10003")
    print("  - Settings → Import from File")
    print("  - Select: " + workflow_path)
    print()
    print("Done! The workflow is ready to be imported.")


def main():
    workflow_path = sys.argv[1] if len(sys.argv) > 1 else "n8n-workflows/ashare-daily-simple.json"
    
    if not __import__("pathlib").Path(workflow_path).exists():
        print(f"Error: Workflow file not found: {workflow_path}")
        sys.exit(1)
    
    # Test MCP connection first
    print("Testing MCP connection...")
    if test_mcp_connection():
        print("✓ MCP connection successful!")
    else:
        print("⚠ MCP connection failed or requires manual setup")
    
    print()
    import_workflow_via_mcp(workflow_path)


if __name__ == "__main__":
    main()
