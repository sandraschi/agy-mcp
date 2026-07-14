"""FastMCP server for Antigravity IDE — skill management, config, agent orchestration."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

log = logging.getLogger(__name__)

_AGENTS_DIR = Path(os.getenv("AGENTS_DIR", os.path.expanduser("~/.agents")))
_SKILLS_DIR = _AGENTS_DIR / "skills"

mcp = FastMCP(
    "agy-mcp",
    instructions="MCP server for Antigravity IDE — manage agent skills, config, and agent orchestration.",
    version="0.1.0",
)

_READ_ONLY = {"readonly": True}
_MUTATING = {}


@mcp.tool(annotations=_READ_ONLY)
async def agy_list_skills(ctx: Any = None) -> dict:
    """List all installed Antigravity agent skills.

    Scans ~/.agents/skills/ for SKILL.md files.

    ## Return Format
    {"skills": [{"name": str, "path": str}], "count": int}
    """
    if not _SKILLS_DIR.is_dir():
        return {"skills": [], "count": 0}
    skills = []
    for entry in sorted(_SKILLS_DIR.iterdir()):
        if entry.is_dir() and (entry / "SKILL.md").is_file():
            skills.append({"name": entry.name, "path": str(entry)})
    return {"skills": skills, "count": len(skills)}


@mcp.tool(annotations=_READ_ONLY)
async def agy_read_skill(skill_name: str, ctx: Any = None) -> dict:
    """Read a skill's SKILL.md content by name.

    ## Return Format
    {"name": str, "content": str}

    ## Examples
    agy_read_skill("python-expert")
    """
    skill_file = _SKILLS_DIR / skill_name / "SKILL.md"
    if not skill_file.is_file():
        return {"error": f"Skill '{skill_name}' not found", "scanned": str(_SKILLS_DIR)}
    return {"name": skill_name, "content": skill_file.read_text(encoding="utf-8")}


@mcp.tool(annotations=_MUTATING)
async def agy_install_skill(skill_name: str, content: str, ctx: Any = None) -> dict:
    """Create or update a skill by writing its SKILL.md.

    ## Return Format
    {"success": bool, "name": str}

    ## Examples
    agy_install_skill("my-skill", "# My Skill\\n\\nInstructions...")
    """
    path = _SKILLS_DIR / skill_name
    path.mkdir(parents=True, exist_ok=True)
    (path / "SKILL.md").write_text(content, encoding="utf-8")
    return {"success": True, "name": skill_name}


@mcp.tool(annotations=_READ_ONLY)
async def agy_config(ctx: Any = None) -> dict:
    """Read Antigravity agent configuration.

    Returns the config.json from the agents directory.

    ## Return Format
    {"config_file": str, "config": dict}
    """
    config_file = _AGENTS_DIR / "config.json"
    if not config_file.is_file():
        return {"config_file": str(config_file), "config": {}}
    try:
        data = json.loads(config_file.read_text(encoding="utf-8"))
        return {"config_file": str(config_file), "config": data}
    except (json.JSONDecodeError, OSError) as e:
        return {"error": f"Failed to read config: {e}"}


@mcp.tool(annotations=_READ_ONLY)
async def agy_help(ctx: Any = None) -> dict:
    """Show available agy-mcp tools and usage."""
    return {
        "tools": [
            {"name": "agy_list_skills", "description": "List installed skills"},
            {"name": "agy_read_skill", "description": "Read a skill's content"},
            {"name": "agy_install_skill", "description": "Create/update a skill"},
            {"name": "agy_config", "description": "Read Antigravity config"},
        ],
        "skills_dir": str(_SKILLS_DIR),
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    mcp.run()


if __name__ == "__main__":
    main()
