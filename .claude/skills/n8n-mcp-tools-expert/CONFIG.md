# n8n API Configuration

## API Credentials

```
N8N_API_URL=https://xhs.adpilot.club
N8N_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2Mjk0ZjI4ZC1kNjRjLTQ3NzMtOTMwZi1hMTc4MTllNTU3NjgiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY2MTI0MTEwLCJleHAiOjE3Njg3MTI0MDB9.toVHMtX8isEYZERDKcxrAUvUxi2m4Z1ZvImd7A-Jt9k
```

## Server Details

| Property | Value |
|----------|-------|
| URL | https://xhs.adpilot.club |
| Health Check | https://xhs.adpilot.club/healthz |
| API Version | Public API v1 |
| Token Expires | 2026-01-18 (UTC) |

## Usage in API Calls

```bash
# Health check
curl -s "https://xhs.adpilot.club/healthz"

# List workflows
curl -s "https://xhs.adpilot.club/api/v1/workflows" \
  -H "X-N8N-API-KEY: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2Mjk0ZjI4ZC1kNjRjLTQ3NzMtOTMwZi1hMTc4MTllNTU3NjgiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY2MTI0MTEwLCJleHAiOjE3Njg3MTI0MDB9.toVHMtX8isEYZERDKcxrAUvUxi2m4Z1ZvImd7A-Jt9k"

# Create workflow
curl -X POST "https://xhs.adpilot.club/api/v1/workflows" \
  -H "X-N8N-API-KEY: <API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Workflow", "nodes": [...], "connections": {...}}'
```

## MCP Server Configuration

To use n8n-mcp with this API, configure in `.mcp.json`:

```json
{
  "mcpServers": {
    "n8n-mcp": {
      "command": "npx",
      "args": ["-y", "@peyanski/n8n-mcp"],
      "env": {
        "N8N_API_URL": "https://xhs.adpilot.club",
        "N8N_API_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2Mjk0ZjI4ZC1kNjRjLTQ3NzMtOTMwZi1hMTc4MTllNTU3NjgiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY2MTI0MTEwLCJleHAiOjE3Njg3MTI0MDB9.toVHMtX8isEYZERDKcxrAUvUxi2m4Z1ZvImd7A-Jt9k"
      }
    }
  }
}
```

## Available API Endpoints

With valid API key, these tools become available:
- `n8n_create_workflow` - Create new workflows
- `n8n_update_partial_workflow` - Edit existing workflows
- `n8n_validate_workflow` - Validate workflow by ID
- `n8n_list_workflows` - List all workflows
- `n8n_get_workflow` - Get workflow details
- `n8n_trigger_webhook_workflow` - Trigger webhook workflows
