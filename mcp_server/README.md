# Agent Smith MCP Server

Model Context Protocol (MCP) server that exposes Agent Smith's security scanning and AI analysis tools over HTTP. Supports both **SSE** and **Streamable HTTP** transports.

## Quick Start

```bash
# Install MCP dependencies
pip install -r mcp_server/requirements.txt

# Start the server (dev mode, no auth)
python3 -m mcp_server --no-auth

# Start with authentication (production)
export AGENTSMITH_MCP_TOKEN=your-secret-token
python3 -m mcp_server
```

The server starts on **port 2266** by default with both SSE and Streamable HTTP transports.

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check (no auth required) |
| `/ready` | GET | Readiness check — verifies scanner binary (no auth required) |
| `/sse` | GET | SSE transport for MCP clients |
| `/messages/` | POST | SSE message handler |
| `/mcp/` | POST | Streamable HTTP transport for MCP clients |

## Available Tools

### Static Analysis (no API key needed)

| Tool | Description |
|------|-------------|
| `scan_static` | Scan a whole repository with 70+ OWASP rules |
| `scan_file` | Scan a single file — ideal for checking the file you're editing |
| `detect_tech_stack` | Detect languages, frameworks, entry points, and security risks |
| `list_presets` | List available scan preset configurations |

### Results & Filtering

| Tool | Description |
|------|-------------|
| `summarize_results` | Summarize existing scan results with severity counts, cost, and artifacts |
| `list_findings` | Browse findings filtered by severity, source, with pagination |

### AI-Powered (requires `CLAUDE_API_KEY` or Bedrock)

| Tool | Description |
|------|-------------|
| `scan_hybrid` | Full hybrid scan combining static + AI analysis with payloads and annotations |
| `explain_finding` | Deep-dive explanation of a vulnerability: attack scenarios, CWE, OWASP category |
| `get_fix` | AI-generated code fix with before/after code, explanation, and test suggestion |

## Connecting Clients

### Cursor IDE

Add to `.cursor/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "agentsmith": {
      "url": "http://localhost:2266/mcp/"
    }
  }
}
```

Or use the SSE transport:

```json
{
  "mcpServers": {
    "agentsmith": {
      "url": "http://localhost:2266/sse"
    }
  }
}
```

Reload Cursor after editing (Cmd+Shift+P → "Developer: Reload Window").

### Other MCP Clients

Any MCP-compatible client can connect via:
- **Streamable HTTP**: `POST http://localhost:2266/mcp/`
- **SSE**: `GET http://localhost:2266/sse`

## Test Client

The built-in test client validates the server and provides an interactive REPL.

```bash
# Run automated test suite
python3 -m mcp_server.test_client test

# Include AI-powered tools (needs CLAUDE_API_KEY)
python3 -m mcp_server.test_client test --all

# Test a single tool
python3 -m mcp_server.test_client test --tool scan_file

# Interactive REPL — call tools manually
python3 -m mcp_server.test_client interact

# List all tools with full schemas
python3 -m mcp_server.test_client list

# Benchmark latency
python3 -m mcp_server.test_client benchmark

# JSON output for CI/CD
python3 -m mcp_server.test_client test --json

# Point at a different repo
python3 -m mcp_server.test_client test --repo /path/to/repo
```

## Configuration

All configuration via environment variables:

### Required (Production)

| Variable | Description |
|----------|-------------|
| `AGENTSMITH_MCP_TOKEN` | Bearer token for authentication |

### AI Provider

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENTSMITH_PROVIDER` | `anthropic` | AI provider: `anthropic` or `bedrock` |
| `CLAUDE_API_KEY` | — | API key (when provider is `anthropic`) |
| `CLAUDE_MODEL` | `haiku` | Model to use: `opus`, `sonnet`, `haiku`, or full ID |
| `AWS_REGION` | `us-east-1` | AWS region (when provider is `bedrock`) |

### Server

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENTSMITH_MCP_HOST` | `0.0.0.0` | Host to bind to |
| `AGENTSMITH_MCP_PORT` | `2266` | Port to listen on |
| `AGENTSMITH_ALLOWED_PATHS` | cwd | Comma-separated allowed scan paths |
| `AGENTSMITH_CORS_ORIGINS` | `http://localhost:*` | CORS allowed origins |

### Path Security

By default, the server only allows scanning files under the **current working directory** where it was started. To scan other directories:

```bash
# Allow scanning multiple directories
export AGENTSMITH_ALLOWED_PATHS="/home/user/projects,/home/user/repos"

# Allow everything under home
export AGENTSMITH_ALLOWED_PATHS="/home/user"

python3 -m mcp_server --no-auth
```

## CLI Options

```
python3 -m mcp_server [options]

Options:
  --port PORT          Port to listen on (default: 2266)
  --host HOST          Host to bind to (default: 0.0.0.0)
  --transport MODE     Transport: sse, http, or both (default: both)
  --no-auth            Disable bearer token auth (dev only)
  --debug              Enable debug logging
```

## Security

- **Bearer token auth**: All non-health endpoints require `Authorization: Bearer <token>`. Server refuses to start without `AGENTSMITH_MCP_TOKEN` unless `--no-auth` is used.
- **Path validation**: All `repo_path` and `file_path` parameters are resolved and checked against `AGENTSMITH_ALLOWED_PATHS`. Directory traversal via `..` is blocked.
- **File size limits**: Single-file operations limited to 1 MB. AI context limited to 100 KB.
- **Input limits**: String parameters have max length enforcement. Findings capped at 500 per request.
- **No open-by-default**: Auth is mandatory in production mode.

## Architecture

```
MCP Client (Cursor, Claude Desktop, custom)
    │
    ├── Streamable HTTP (/mcp/)
    │   └── StreamableHTTPSessionManager
    │
    ├── SSE (/sse + /messages/)
    │   └── SseServerTransport
    │
    v
mcp_server/server.py  (Starlette + uvicorn)
    │
    ├── auth.py          Bearer token middleware
    ├── config.py         Environment-based configuration
    └── tools.py          9 tool definitions + handlers
            │
            ├── scan_static       → Go scanner binary (70+ OWASP rules)
            ├── scan_file         → Go scanner (single file)
            ├── scan_hybrid       → orchestrator.py (static + AI)
            ├── detect_tech_stack → lib/universal_detector.py
            ├── summarize_results → output/ JSON files
            ├── list_findings     → output/ JSON files
            ├── list_presets      → lib/config.py
            ├── explain_finding   → Claude AI (detailed vulnerability explanation)
            └── get_fix           → Claude AI (code fix generation)
```

## Examples

### Health Check

```bash
curl http://localhost:2266/health
# {"status":"healthy","service":"agentsmith-mcp","tools":9}
```

### Scan a Single File via curl + MCP

```bash
# Via Streamable HTTP
curl -X POST http://localhost:2266/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"curl","version":"1.0"}}}'
```

### Interactive Testing

```bash
python3 -m mcp_server.test_client interact

mcp> scan_file {"file_path": "/path/to/file.py"}
mcp> explain_finding {"file_path": "/path/to/file.py", "description": "SQL injection", "line_number": 42}
mcp> get_fix {"file_path": "/path/to/file.py", "description": "hardcoded password on line 15"}
```

### Bedrock Provider

```bash
AGENTSMITH_PROVIDER=bedrock \
AWS_REGION=us-east-1 \
AGENTSMITH_MCP_TOKEN=secret \
python3 -m mcp_server
```
