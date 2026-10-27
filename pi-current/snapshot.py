#!/usr/bin/env python3
"""Refresh the reviewed, non-secret Pi configuration snapshot from this machine.

Run only after reviewing source files; this script intentionally has a closed allowlist.
It never touches the live Pi configuration.
"""
import hashlib
import json
from pathlib import Path
import re

HOME = Path.home()
SOURCE = HOME / ".pi/agent"
DEST = Path(__file__).resolve().parent
FILES = {
    "AGENTS.md": "agent/AGENTS.md",
    "settings.json": "agent/settings.json",
    "models.json": "agent/models.json",
    "npm/package.json": "agent/npm/package.json",
    "npm/package-lock.json": "agent/npm/package-lock.json",
    "prompts/mdev.md": "agent/prompts/mdev.md",
    "prompts/prdev.md": "agent/prompts/prdev.md",
    "prompts/splane.md": "agent/prompts/splane.md",
    "prompts/rwbrowser.md": "agent/prompts/rwbrowser.md",
    "extensions/tgrep/index.ts": "agent/extensions/tgrep/index.ts",
}
SENSITIVE = re.compile(
    r"-----BEGIN (?:OPENSSH|RSA|EC|DSA|PRIVATE) PRIVATE KEY-----|"
    r"\b(?:gh[pousr]_|sk-[A-Za-z0-9]{20}|AIza[A-Za-z0-9_-]{20})|"
    r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE
)


def safe_write(rel: str, content: bytes) -> None:
    if SENSITIVE.search(content.decode("utf-8")):
        raise ValueError(f"Possible credential in {rel}; review manually")
    target = DEST / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)


def main() -> None:
    for source, output in FILES.items():
        path = SOURCE / source
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Missing or linked source: {source}")
        safe_write(output, path.read_bytes())

    mcp = json.loads((SOURCE / "mcp.json").read_text())
    for server in mcp["mcpServers"].values():
        if "headers" in server:
            server["headers"] = {key: "<SET_LOCALLY>" for key in server["headers"]}
        # The JSON is a template: $HOME must be replaced with the destination home.
        for key in ("command",):
            if isinstance(server.get(key), str):
                server[key] = server[key].replace(str(HOME), "$HOME")
        if isinstance(server.get("args"), list):
            server["args"] = [v.replace(str(HOME), "$HOME") if isinstance(v, str) else v for v in server["args"]]
    mcp.pop("_agentmemoryConnector", None)  # local connector checksum, not configuration
    safe_write("agent/mcp.template.json", (json.dumps(mcp, indent=2, ensure_ascii=False) + "\n").encode())

    skills = []
    root = SOURCE / "skills"
    for skill in sorted(root.iterdir()):
        if not skill.is_dir() or skill.is_symlink():
            raise ValueError(f"Unexpected skill path: {skill.name}")
        files = sorted(f for f in skill.rglob("*") if f.is_file() and not f.is_symlink())
        if any(f.is_symlink() for f in skill.rglob("*")):
            raise ValueError(f"Linked skill file: {skill.name}")
        skills.append({"name": skill.name, "files": [
            {"path": str(f.relative_to(root)), "sha256": hashlib.sha256(f.read_bytes()).hexdigest()}
            for f in files
        ]})
    safe_write("skills-inventory.json", (json.dumps(skills, indent=2) + "\n").encode())
    print(f"Snapshot refreshed: {len(FILES)} allowlisted files, MCP template, {len(skills)} skill inventories")


if __name__ == "__main__":
    main()
