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
    "prompts/rwbrowser.md": "agent/prompts/rwbrowser.md",
    "extensions/tgrep/index.ts": "agent/extensions/tgrep/index.ts",
    "extensions/tgrep/search-policy.mjs": "agent/extensions/tgrep/search-policy.mjs",
    "skills/pi-workflow/context-economy.md": "agent/skills/pi-workflow/context-economy.md",
    "skills/pi-workflow/SKILL.md": "agent/skills/pi-workflow/SKILL.md",
    "extensions/megai-action-boundary/index.ts": "agent/extensions/megai-action-boundary/index.ts",
    "extensions/megai-action-boundary/boundary.mjs": "agent/extensions/megai-action-boundary/boundary.mjs",
    "extensions/megai-action-boundary/README.md": "agent/extensions/megai-action-boundary/README.md",
    "extensions/megai-project-size/index.ts": "agent/extensions/megai-project-size/index.ts",
    "extensions/megai-project-size/measure.mjs": "agent/extensions/megai-project-size/measure.mjs",
    "APPEND_SYSTEM.md": "agent/APPEND_SYSTEM.md",
    "extensions/megai-keep-going/index.ts": "agent/extensions/megai-keep-going/index.ts",
    "extensions/megai-keep-going/keep-going-core.mjs": "agent/extensions/megai-keep-going/keep-going-core.mjs",
    "extensions/megai-keep-going/README.md": "agent/extensions/megai-keep-going/README.md",
    "extensions/megai-lean-prompt/index.ts": "agent/extensions/megai-lean-prompt/index.ts",
    "extensions/megai-lean-prompt/lean-core.mjs": "agent/extensions/megai-lean-prompt/lean-core.mjs",
    "extensions/megai-lean-prompt/config.json": "agent/extensions/megai-lean-prompt/config.json",
    "extensions/megai-lean-prompt/README.md": "agent/extensions/megai-lean-prompt/README.md",
    "skills/diff-security/SKILL.md": "agent/skills/diff-security/SKILL.md",
}
# Codex (GPT) autonomy: global instructions and the keep-going Stop hook only.
# config.toml is deliberately excluded (MCP servers, hook trust state, local paths).
CODEX_SOURCE = HOME / ".codex"
CODEX_FILES = {
    "AGENTS.md": "codex/AGENTS.md",
    "hooks.json": "codex/hooks.json",
    "hooks/megai-keep-going.mjs": "codex/hooks/megai-keep-going.mjs",
    "hooks/keep-going-core.mjs": "codex/hooks/keep-going-core.mjs",
}
SENSITIVE = re.compile(
    r"-----BEGIN (?:OPENSSH|RSA|EC|DSA|PRIVATE) PRIVATE KEY-----|"
    r"\b(?:gh[pousr]_|figd_|xox[abpr]-|sk-[A-Za-z0-9]{20}|AIza[A-Za-z0-9_-]{20})|"
    r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE
)

SECRET_ENV = re.compile(r"TOKEN|SECRET|KEY|PASSWORD|PASS|AUTH|CREDENTIAL|COOKIE", re.IGNORECASE)


def safe_write(rel: str, content: bytes) -> None:
    if SENSITIVE.search(content.decode("utf-8")):
        raise ValueError(f"Possible credential in {rel}; review manually")
    target = DEST / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)


def main() -> None:
    pi_core = (SOURCE / "extensions/megai-keep-going/keep-going-core.mjs").read_bytes()
    if pi_core != (CODEX_SOURCE / "hooks/keep-going-core.mjs").read_bytes():
        raise ValueError("Pi and Codex keep-going-core.mjs differ; copy one over the other first")
    for base, files in ((SOURCE, FILES), (CODEX_SOURCE, CODEX_FILES)):
        for source, output in files.items():
            path = base / source
            if not path.is_file() or path.is_symlink():
                raise ValueError(f"Missing or linked source: {path}")
            safe_write(output, path.read_bytes())

    mcp = json.loads((SOURCE / "mcp.json").read_text())
    for server in mcp["mcpServers"].values():
        if "headers" in server:
            server["headers"] = {key: "<SET_LOCALLY>" for key in server["headers"]}
        if isinstance(server.get("env"), dict):
            server["env"] = {key: "<SET_LOCALLY>" if SECRET_ENV.search(key) else value
                             for key, value in server["env"].items()}
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
    print(f"Snapshot refreshed: {len(FILES) + len(CODEX_FILES)} allowlisted files, MCP template, {len(skills)} skill inventories")


if __name__ == "__main__":
    main()
