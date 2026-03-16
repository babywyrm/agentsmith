---
name: agentsmith-mcp-server
description: >-
  Start, configure, and use the Agent Smith MCP server from Cursor.
  Use when setting up the MCP server, running scans via MCP tools,
  or integrating Agent Smith into Cursor IDE workflows.
---

# Agent Smith MCP Server

## When to Use

User wants to use Agent Smith as an MCP server from Cursor or another MCP client.

## Starting the Server

```bash
cd ~/agentsmith
source scripts/activate.sh
python3 -m mcp_server
```

Server starts on `http://localhost:2266` with:
- SSE endpoint: `http://localhost:2266/sse`
- HTTP endpoint: `http://localhost:2266/mcp/`

## Cursor Configuration

Already configured in `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "agentsmith": { "url": "http://localhost:2266/mcp/" },
    "agentsmith-sse": { "url": "http://localhost:2266/sse" }
  }
}
```

## Available Tools (10)

| Tool | What it does |
|------|-------------|
| `scan_static` | Run Go static scanner on a repo |
| `scan_hybrid` | Static + AI analysis (the main scan) |
| `scan_mcp` | Scan an MCP server for security issues |
| `scan_file` | Analyze a single file with AI |
| `detect_tech_stack` | Auto-detect languages and frameworks |
| `summarize_results` | Summarize latest scan results |
| `list_findings` | List findings from latest scan |
| `list_presets` | Show available presets and their configs |
| `explain_finding` | Get detailed explanation of a finding |
| `get_fix` | Get fix recommendations for a finding |

## MCP Shell (Interactive)

```bash
./scripts/run_mcp_shell.sh
```

### Common commands:

```
mcp> scan_hybrid preset=quick
mcp> scan_hybrid profile=owasp,flask preset=ctf
mcp> scan_hybrid question="find SQL injection" generate_payloads=true
mcp> scan_static
mcp> scan_mcp 9001
mcp> dvmcp
mcp> summary
mcp> findings 20
mcp> annotations
mcp> payloads
mcp> everything
mcp> help
```

## Key Parameters for scan_hybrid

| Parameter | Default | Description |
|-----------|---------|-------------|
| `repo_path` | current dir | Path to scan |
| `preset` | `mcp` | Preset name |
| `profile` | from preset | AI profiles (comma-separated) |
| `question` | none | Focus question for AI |
| `prioritize_top` | from preset | How many files AI analyzes |
| `top_n` | from preset | How many findings get payloads |
| `generate_payloads` | false | Generate exploit payloads |
| `annotate_code` | false | Add code annotations |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Server won't start | Check `source scripts/activate.sh` first |
| "Module not found" | `uv pip install -e ".[mcp-server]"` |
| Cursor can't connect | Verify server is running on port 2266 |
| Scan timeout | Use `--preset mcp` for fastest results |
