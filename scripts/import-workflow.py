#!/usr/bin/env python3
"""Simple script to import n8n workflow via UI webhook or manual steps."""

from __future__ import annotations

import json
import sys
import webbrowser
from pathlib import Path


def open_n8n_import_guide():
    """Open browser with import instructions."""
    guide_url = "file:///home/bruce/Projects/oh-my-superpowers/n8n-workflows/MCP_SETUP.md"
    
    # Create a simple HTML guide for the user
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>n8n Workflow Import Guide</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 40px; line-height: 1.6; }
            .step { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }
            .code { background: #333; color: #0f0; padding: 10px; border-radius: 3px; font-family: monospace; }
            h1 { color: #2c3e50; }
            h2 { color: #3498db; }
            .success { color: #27ae60; font-weight: bold; }
            .warning { color: #e74c3c; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>🚀 n8n Workflow Import Guide</h1>
        
        <div class="step">
            <h2>Step 1: Open n8n</h2>
            <p><span class="success">✓ Done</span> n8n is running at <a href="http://localhost:10003" target="_blank">http://localhost:10003</a></p>
        </div>
        
        <div class="step">
            <h2>Step 2: Get API Key (Optional)</h2>
            <p>If you want to use the automated import:</p>
            <ol>
                <li>Click your avatar (top left) → Settings</li>
                <li>Goto Credentials → API Key section</li>
                <li>Create new API key</li>
                <li>Copy the key</li>
            </ol>
            <p class="code"># Then run:</p>
            <p class="code">export N8N_API_KEY="your_key_here"</p>
            <p class="code">cd /home/bruce/Projects/oh-my-superpowers && ./scripts/deploy-n8n-workflow.sh</p>
        </div>
        
        <div class="step">
            <h2>Step 3: Manual Import (No API Key Needed)</h2>
            <ol>
                <li>In n8n UI, click <strong>Settings</strong> → <strong>Import from File</strong></li>
                <li>Select file: <code>/home/bruce/Projects/oh-my-superpowers/n8n-workflows/ashare-daily-simple.json</code></li>
                <li>Click <strong>Import</strong></li>
                <li>Return to Workflows page</li>
                <li>Find "A 股每日数据采集（简化版）"</li>
                <li>Toggle the switch to <strong>ON</strong></li>
            </ol>
        </div>
        
        <div class="step">
            <h2>Step 4: Verify Configuration</h2>
            <ul>
                <li>Cron Trigger: Weekdays 22:00-22:59 (Beijing time)</li>
                <li>HTTP Request URL: <code>http://task_runner:8000/ashare/collect</code></li>
                <li>Timeout: 600000ms (10 minutes)</li>
                <li>Retry: 3 attempts, 5 min apart</li>
            </ul>
        </div>
        
        <div class="step">
            <h2>Step 5: Test Run</h2>
            <ol>
                <li>Click <strong>Execute Workflow</strong> button (top right)</li>
                <li>Watch the execution log on the right panel</li>
                <li>Check output files:</li>
            </ol>
            <p class="code">ls -la ~/.ashare-assistant/status/</p>
            <p class="code">ls -la ~/.ashare-assistant/logs/</p>
        </div>
        
        <div class="step">
            <h2>Next Steps</h2>
            <ul>
                <li>Wait for next scheduled run (22:00 Beijing time)</li>
                <li>Monitor execution logs in n8n UI</li>
                <li>Set up alert notifications if needed</li>
            </ul>
        </div>
        
        <hr>
        <p style="color: #7f8c8d; font-size: 0.9em;">
            For more details, see <a href="MCP_SETUP.md" target="_blank">MCP_SETUP.md</a> or 
            <a href="DEPLOY_STEPS.md" target="_blank">DEPLOY_STEPS.md</a>
        </p>
    </body>
    </html>
    """
    
    # Save to temp file and open
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        f.write(html_content)
        temp_path = f.name
    
    webbrowser.open(f'file://{temp_path}')
    print(f"✅ Guide opened in browser: {temp_path}")


def check_prerequisites():
    """Check if all prerequisites are met."""
    checks = []
    
    # Check n8n container
    import subprocess
    try:
        result = subprocess.run(
            ['docker', 'ps', '--format', '{{.Names}}'],
            capture_output=True, text=True, check=True
        )
        if 'n8n_app' in result.stdout:
            checks.append(('n8n container', 'Running ✓'))
        else:
            checks.append(('n8n container', 'Not found ✗'))
    except Exception as e:
        checks.append(('n8n container', f'Error: {e} ✗'))
    
    # Check task-runner container
    try:
        result = subprocess.run(
            ['docker', 'ps', '--format', '{{.Names}}'],
            capture_output=True, text=True, check=True
        )
        if 'task_runner' in result.stdout:
            checks.append(('task-runner container', 'Running ✓'))
        else:
            checks.append(('task-runner container', 'Not found ✗'))
    except Exception as e:
        checks.append(('task-runner container', f'Error: {e} ✗'))
    
    # Check workflow file
    workflow_path = Path('/home/bruce/Projects/oh-my-superpowers/n8n-workflows/ashare-daily-simple.json')
    if workflow_path.exists():
        checks.append(('workflow file', 'Found ✓'))
    else:
        checks.append(('workflow file', 'Not found ✗'))
    
    return checks


def main():
    """Main entry point."""
    print("=== n8n Workflow Import Assistant ===\n")
    
    # Check prerequisites
    print("Checking prerequisites...")
    checks = check_prerequisites()
    for name, status in checks:
        print(f"  {name}: {status}")
    
    print("\n" + "="*50 + "\n")
    
    # Open guide
    print("Opening import guide in browser...\n")
    open_n8n_import_guide()
    
    print("\n" + "="*50)
    print("\n📋 Quick Commands:")
    print("  Manual import: Open http://localhost:10003 → Settings → Import from File")
    print("  Auto import:   export N8N_API_KEY='key' && ./scripts/deploy-n8n-workflow.sh")
    print("\n✅ Done! Follow the guide to complete the import.")


if __name__ == "__main__":
    main()
