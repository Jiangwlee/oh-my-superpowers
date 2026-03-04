#!/bin/bash
# Deploy n8n workflow to local instance

set -e

WORKFLOW_FILE="${1:-n8n-workflows/ashare-daily-simple.json}"
N8N_URL="${2:-http://localhost:10003}"

echo "=== n8n Workflow Deployment ==="
echo "Workflow file: $WORKFLOW_FILE"
echo "n8n URL: $N8N_URL"
echo ""

# Check if workflow file exists
if [ ! -f "$WORKFLOW_FILE" ]; then
    echo "Error: Workflow file not found: $WORKFLOW_FILE"
    exit 1
fi

# Validate JSON
echo "Validating JSON..."
if ! python -c "import json; json.load(open('$WORKFLOW_FILE'))"; then
    echo "Error: Invalid JSON in workflow file"
    exit 1
fi
echo "✓ JSON validation passed"

# Check n8n container
echo "Checking n8n container..."
if ! docker ps --format '{{.Names}}' | grep -q "^n8n_app$"; then
    echo "Warning: n8n container not running"
    echo "Please start it with: cd ~/Dockers/N8N && docker compose up -d"
    exit 1
fi
echo "✓ n8n container is running"

# Get n8n API credentials (prompt user)
echo ""
echo "To import the workflow, you need n8n API credentials."
echo "Get them from: n8n UI → Settings → Credentials → API Key"
echo ""
read -p "Enter n8n API key (or press Enter for manual import): " API_KEY

if [ -z "$API_KEY" ]; then
    echo ""
    echo "=== Manual Import Instructions ==="
    echo "1. Open n8n: http://localhost:10003"
    echo "2. Go to Settings → Import from File"
    echo "3. Select: $WORKFLOW_FILE"
    echo "4. Click Import"
    echo "5. Activate the workflow by toggling the switch"
    echo ""
    echo "Done! You can now close this terminal."
else
    # Import via API
    echo ""
    echo "Importing workflow via API..."
    
    WORKFLOW_NAME=$(python -c "import json; print(json.load(open('$WORKFLOW_FILE'))['name'])")
    
    RESPONSE=$(curl -s -X POST \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d @"$WORKFLOW_FILE" \
        "$N8N_URL/rest/workflows")
    
    if echo "$RESPONSE" | grep -q '"status":"error"'; then
        echo "✗ Import failed:"
        echo "$RESPONSE" | python -m json.tool
        exit 1
    fi
    
    echo "✓ Workflow imported successfully!"
    echo "  Name: $(echo "$RESPONSE" | python -c 'import sys,json; print(json.load(sys.stdin)["name"])')"
    echo "  ID: $(echo "$RESPONSE" | python -c 'import sys,json; print(json.load(sys.stdin)["id"])')"
    echo ""
    echo "Next steps:"
    echo "1. Activate the workflow in n8n UI"
    echo "2. Test with Execute Workflow button"
    echo "3. Monitor execution logs"
fi
