"""FastMCP server for Antigravity IDE — skills, config, sessions, providers."""

from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

log = logging.getLogger(__name__)

_AGENTS_DIR = Path(os.getenv("AGENTS_DIR", os.path.expanduser("~/.agents")))
_SKILLS_DIR = _AGENTS_DIR / "skills"
_LOCK_FILE = _AGENTS_DIR / ".skill-lock.json"
_CONFIG_FILE = _AGENTS_DIR / "config.json"

mcp = FastMCP(
    "agy-mcp",
    instructions="MCP server for Antigravity IDE — manage skills, config, providers, and agent sessions.",
    version="0.1.0",
)

_READ_ONLY = {"readonly": True}
_MUTATING = {}


def _read_lock() -> dict:
    if not _LOCK_FILE.is_file():
        return {"skills": {}, "version": 0}
    try:
        return json.loads(_LOCK_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"skills": {}, "version": 0}


def _write_lock(data: dict) -> bool:
    try:
        _LOCK_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return True
    except OSError:
        return False


# ── Skills: Read ──────────────────────────────────────────────────────────────


@mcp.tool(annotations=_READ_ONLY)
async def agy_list_skills(ctx: Any = None) -> dict:
    """List all installed Antigravity agent skills with source info.

    Scans ~/.agents/skills/ and merges metadata from .skill-lock.json.

    ## Return Format
    {"skills": [{"name": str, "source": str, "source_type": str}], "count": int}
    """
    if not _SKILLS_DIR.is_dir():
        return {"skills": [], "count": 0}
    lock = _read_lock()
    skills = []
    for entry in sorted(_SKILLS_DIR.iterdir()):
        if entry.is_dir() and (entry / "SKILL.md").is_file():
            meta = lock.get("skills", {}).get(entry.name, {})
            skills.append(
                {
                    "name": entry.name,
                    "source": meta.get("source", ""),
                    "source_type": meta.get("sourceType", "local"),
                }
            )
    return {"skills": skills, "count": len(skills)}


@mcp.tool(annotations=_READ_ONLY)
async def agy_read_skill(skill_name: str, ctx: Any = None) -> dict:
    """Read a skill's full SKILL.md content.

    ## Return Format
    {"name": str, "content": str, "meta": dict}

    ## Examples
    agy_read_skill("python-expert")
    """
    skill_file = _SKILLS_DIR / skill_name / "SKILL.md"
    if not skill_file.is_file():
        return {"error": f"Skill '{skill_name}' not found", "skills_dir": str(_SKILLS_DIR)}
    lock = _read_lock()
    return {
        "name": skill_name,
        "content": skill_file.read_text(encoding="utf-8"),
        "meta": lock.get("skills", {}).get(skill_name, {}),
    }


@mcp.tool(annotations=_READ_ONLY)
async def agy_search_skills(query: str, ctx: Any = None) -> dict:
    """Search across all installed skill names and content.

    ## Return Format
    {"results": [{"name": str, "match": str}], "count": int}

    ## Examples
    agy_search_skills("python")
    agy_search_skills("docker")
    """
    query_lower = query.lower()
    results = []
    if not _SKILLS_DIR.is_dir():
        return {"results": [], "count": 0}
    for entry in sorted(_SKILLS_DIR.iterdir()):
        skill_file = entry / "SKILL.md"
        if not (entry.is_dir() and skill_file.is_file()):
            continue
        if query_lower in entry.name.lower():
            results.append({"name": entry.name, "match": "name"})
            continue
        try:
            content = skill_file.read_text(encoding="utf-8").lower()
            if query_lower in content:
                results.append({"name": entry.name, "match": "content"})
        except OSError:
            pass
    return {"results": results, "count": len(results)}


# ── Skills: Write ─────────────────────────────────────────────────────────────


@mcp.tool(annotations=_MUTATING)
async def agy_install_skill(skill_name: str, content: str, ctx: Any = None) -> dict:
    """Create or update a skill by writing its SKILL.md.

    Also registers the skill in .skill-lock.json as a local skill.

    ## Return Format
    {"success": bool, "name": str}

    ## Examples
    agy_install_skill("my-skill", "# My Skill\\n\\nBe helpful and concise.")
    """
    path = _SKILLS_DIR / skill_name
    path.mkdir(parents=True, exist_ok=True)
    (path / "SKILL.md").write_text(content, encoding="utf-8")
    # Register in lock file
    lock = _read_lock()
    lock["skills"][skill_name] = {
        "source": "local",
        "sourceType": "local",
        "installedAt": str(__import__("datetime").datetime.now().isoformat()),
    }
    _write_lock(lock)
    return {"success": True, "name": skill_name}


@mcp.tool(annotations=_MUTATING)
async def agy_delete_skill(skill_name: str, ctx: Any = None) -> dict:
    """Permanently remove an installed skill.

    ## Return Format
    {"success": bool, "name": str}

    ## Examples
    agy_delete_skill("old-skill")
    """
    path = _SKILLS_DIR / skill_name
    if not path.is_dir():
        return {"success": False, "error": f"Skill '{skill_name}' not found"}
    import shutil

    try:
        shutil.rmtree(path)
        lock = _read_lock()
        lock["skills"].pop(skill_name, None)
        _write_lock(lock)
        return {"success": True, "name": skill_name}
    except OSError as e:
        return {"success": False, "error": str(e)}


# ── Config ────────────────────────────────────────────────────────────────────


@mcp.tool(annotations=_READ_ONLY)
async def agy_get_config(ctx: Any = None) -> dict:
    """Read the full Antigravity configuration.

    ## Return Format
    {"config": dict, "path": str}
    """
    if not _CONFIG_FILE.is_file():
        return {"config": {}, "path": str(_CONFIG_FILE)}
    try:
        data = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
        return {"config": data, "path": str(_CONFIG_FILE)}
    except (json.JSONDecodeError, OSError) as e:
        return {"error": f"Failed to read config: {e}"}


@mcp.tool(annotations=_MUTATING)
async def agy_set_config(key: str, value: str, ctx: Any = None) -> dict:
    """Set a configuration value in Antigravity config.json.

    Creates the config file if it doesn't exist.

    ## Return Format
    {"success": bool, "key": str, "value": any}

    ## Examples
    agy_set_config("default_model", "claude-sonnet-4-6")
    """
    try:
        value_converted: Any = int(value)
    except (ValueError, TypeError):
        try:
            value_converted = float(value)
        except (ValueError, TypeError):
            value_converted = value
    current = {}
    if _CONFIG_FILE.is_file():
        try:
            current = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    current[key] = value_converted
    _CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_FILE.write_text(json.dumps(current, indent=2), encoding="utf-8")
    return {"success": True, "key": key, "value": value_converted}


# ── Provider info ─────────────────────────────────────────────────────────────


@mcp.tool(annotations=_READ_ONLY)
async def agy_list_providers(ctx: Any = None) -> dict:
    """List configured LLM providers from Antigravity config.

    Reads the providers section from config.json.

    ## Return Format
    {"providers": [{"name": str}], "count": int}
    """
    if not _CONFIG_FILE.is_file():
        return {"providers": [], "count": 0}
    try:
        data = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
        providers = data.get("providers", data.get("llm", {}).get("providers", {}))
        if isinstance(providers, dict):
            return {"providers": [{"name": k} for k in providers], "count": len(providers)}
        return {"providers": [], "count": 0}
    except (json.JSONDecodeError, OSError):
        return {"providers": [], "count": 0}


# ── Skill Lock / Marketplace ──────────────────────────────────────────────────


@mcp.tool(annotations=_READ_ONLY)
async def agy_skill_lock_status(ctx: Any = None) -> dict:
    """Read the .skill-lock.json to see installed skill sources and versions.

    ## Return Format
    {"version": int, "skills": [{"name": str, "source": str, "source_type": str}], "count": int}
    """
    lock = _read_lock()
    skills = [{"name": k, **v} for k, v in lock.get("skills", {}).items()]
    return {"version": lock.get("version", 0), "skills": skills, "count": len(skills)}


@mcp.tool(annotations=_MUTATING)
async def agy_install_skill_from_github(repo: str, skill_path: str = "", ctx: Any = None) -> dict:
    """Install a skill directly from a GitHub repository.

    Clones the repo temporarily and extracts the skill directory.

    ## Return Format
    {"success": bool, "repo": str, "skill_name": str}

    ## Examples
    agy_install_skill_from_github("sandraschi/python-expert")
    agy_install_skill_from_github("sandraschi/mcp-central-docs", "skills/fleet-expert")
    """
    import shutil
    import tempfile

    repo_name = repo.split("/")[-1].replace(".git", "")
    skill_name = skill_path.split("/")[-1] if skill_path else repo_name
    dest = _SKILLS_DIR / skill_name

    tmpdir = tempfile.mkdtemp()
    try:
        subprocess.run(
            ["git", "clone", f"https://github.com/{repo}.git", str(tmpdir / "repo")],
            capture_output=True,
            timeout=60,
            check=True,
        )
        src = Path(str(tmpdir / "repo" / skill_path)) if skill_path else Path(str(tmpdir / "repo"))
        src_skill = src / "SKILL.md" if src.is_dir() else src
        if src_skill.is_file():
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src_skill), str(dest / "SKILL.md"))
            lock = _read_lock()
            lock["skills"][skill_name] = {
                "source": repo,
                "sourceType": "github",
                "sourceUrl": f"https://github.com/{repo}.git",
                "installedAt": str(__import__("datetime").datetime.now().isoformat()),
            }
            _write_lock(lock)
            shutil.rmtree(tmpdir, ignore_errors=True)
            return {"success": True, "repo": repo, "skill_name": skill_name}
        shutil.rmtree(tmpdir, ignore_errors=True)
        return {"success": False, "error": f"No SKILL.md found in {repo}/{skill_path}"}
    except Exception as e:
        shutil.rmtree(tmpdir, ignore_errors=True)
        return {"success": False, "error": str(e)}


# ── Version ───────────────────────────────────────────────────────────────────


@mcp.tool(annotations=_READ_ONLY)
async def agy_version(ctx: Any = None) -> dict:
    """Get the installed Antigravity CLI version.

    ## Return Format
    {"version": str, "path": str}
    """
    for candidate in ["agy", "antigravity"]:
        try:
            result = subprocess.run(
                [candidate, "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return {"version": result.stdout.strip(), "path": candidate}
        except FileNotFoundError:
            continue
    return {"version": "unknown", "path": "not found in PATH"}


# ── Help ──────────────────────────────────────────────────────────────────────


@mcp.tool(annotations=_READ_ONLY)
async def agy_help(ctx: Any = None) -> dict:
    """Show all available agy-mcp tools and usage."""
    return {
        "tools": [
            {"name": "agy_list_skills", "description": "List installed skills with source info"},
            {"name": "agy_read_skill", "description": "Read a skill's content"},
            {"name": "agy_search_skills", "description": "Search skill names and content"},
            {"name": "agy_install_skill", "description": "Create or update a skill"},
            {"name": "agy_delete_skill", "description": "Remove a skill"},
            {"name": "agy_get_config", "description": "Read full Antigravity config"},
            {"name": "agy_set_config", "description": "Set a config value"},
            {"name": "agy_list_providers", "description": "List configured LLM providers"},
            {"name": "agy_skill_lock_status", "description": "Read skill lock metadata"},
            {
                "name": "agy_install_skill_from_github",
                "description": "Install skill from GitHub repo",
            },
            {"name": "agy_version", "description": "Get AGY CLI version"},
        ],
        "skills_dir": str(_SKILLS_DIR),
        "config_dir": str(_AGENTS_DIR),
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    mcp.run()


if __name__ == "__main__":
    main()
