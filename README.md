# agy-mcp

MCP server for [Antigravity IDE](https://antigravity.google/) — skill management, config bridge, and agent orchestration.

Wraps Antigravity's local `~/.agents/` directory (skills, `.skill-lock.json`, `config.json`) as MCP tools, so an assistant can list, read, install, and search Antigravity skills, and read or write Antigravity configuration, without shelling out manually.

## Status

Single-file server (`src/agy_mcp/server.py`, ~380 lines) exposing 11 tools plus `agy_help`. No automated test suite — this wraps JSON files and directory scans rather than anything with complex state, but treat it as unverified until you've exercised the specific tools you plan to rely on.

## Tools

| Tool | Description |
|------|-------------|
| `agy_list_skills` | List installed skills from `~/.agents/skills/`, merged with lock metadata |
| `agy_read_skill` | Read a skill's full `SKILL.md` |
| `agy_search_skills` | Search skill names and content |
| `agy_install_skill` | Write or update a skill's `SKILL.md`, register it in the lock file |
| `agy_delete_skill` | Remove an installed skill |
| `agy_install_skill_from_github` | Clone a GitHub repo, pull a `SKILL.md` out of it, install as a skill |
| `agy_get_config` / `agy_set_config` | Read/write Antigravity's `config.json` |
| `agy_list_providers` | List configured LLM providers from config |
| `agy_skill_lock_status` | Read `.skill-lock.json` (sources, versions) |
| `agy_version` | Report the installed Antigravity CLI version |
| `agy_help` | List all tools |

## Quick start

```powershell
cd D:\Dev\repos\agy-mcp
uv sync
uv run agy-mcp
```

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "agy-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "D:\\Dev\\repos\\agy-mcp", "agy-mcp"]
    }
  }
}
```

By default it reads and writes `~/.agents/` — override with the `AGENTS_DIR` environment variable.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- FastMCP 3.4+
