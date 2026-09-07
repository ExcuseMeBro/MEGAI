#!/usr/bin/env python3
"""Install slim policies and a lazy search proxy; preserve ambiguous prior assets.

Preflight all selected destinations before writing. Receipt hashes prove ownership;
legacy/custom collisions require manual migration, never name-based deletion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import shutil
import tempfile
import tomllib
from pathlib import Path

HOME = Path.home()
MEGAI = Path(os.environ.get("MEGAI_HOME", HOME / ".megai"))
SOURCE = Path(os.environ.get("MEGAI_SOURCE", MEGAI))
RECEIPT = MEGAI / "slim-wiring.json"
BEGIN = "<!-- megai:slim:begin -->"
END = "<!-- megai:slim:end -->"


def safe(path: Path) -> None:
    for part in (path, *path.parents):
        if part.is_symlink() and part not in (Path("/tmp"), Path("/var")):
            raise ValueError(f"symlinked path: {part}; use a regular destination")
    if path.exists() and (not path.is_file() or path.stat().st_uid != os.getuid()):
        raise ValueError(f"not an owned regular file: {path}")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read(path: Path) -> bytes | None:
    safe(path)
    return path.read_bytes() if path.exists() else None


def load_json(path: Path) -> dict:
    data = read(path)
    obj = json.loads(data) if data is not None else {}
    if not isinstance(obj, dict):
        raise ValueError(f"expected JSON object: {path}")
    return obj


def encoded(obj: dict) -> bytes:
    return (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode()


def destinations() -> dict[str, Path]:
    profile = os.environ.get("OMP_PROFILE", os.environ.get("PI_PROFILE", ""))
    if profile and (profile in (".", "..") or "/" in profile or "\\" in profile):
        raise ValueError("OMP profile must be a single directory name")
    return {
        "cc": HOME / ".claude",
        "codex": Path(os.environ.get("CODEX_HOME", HOME / ".codex")),
        "pi": Path(os.environ.get("PI_CODING_AGENT_DIR", HOME / ".pi/agent")),
        "omp": HOME / ".omp" / (f"profiles/{profile}/agent" if profile else "agent"),
    }


class Plan:
    def __init__(self, allow_missing_caveman: bool = False) -> None:
        self.receipt_before = read(RECEIPT)
        self.receipt = json.loads(self.receipt_before) if self.receipt_before else {}
        if not isinstance(self.receipt, dict):
            raise ValueError("invalid slim ownership receipt")
        self.prior_receipt = dict(self.receipt)
        self.allow_missing_caveman = allow_missing_caveman
        load_json(MEGAI / "state.json")
        self.changes: dict[Path, bytes | None] = {}
        self.originals: dict[Path, bytes | None] = {}

    def stage(self, path: Path, data: bytes | None, before: bytes | None) -> None:
        self.changes[path] = data
        self.originals.setdefault(path, before)

    def owned(self, path: Path, data: bytes) -> bool:
        return self.prior_receipt.get(str(path)) == digest(data)

    def asset(self, path: Path, data: bytes, remove: bool) -> None:
        current = read(path)
        if current is not None and current != data and not self.owned(path, current):
            raise ValueError(f"custom/legacy asset preserved: {path}; back up and detach it manually")
        if remove:
            if current is not None and self.owned(path, current):
                self.stage(path, None, current)
                self.receipt.pop(str(path), None)
        else:
            self.stage(path, data, current)
            self.receipt[str(path)] = digest(data)

    def policy(self, path: Path, remove: bool) -> None:
        before = read(path)
        current = before or b""
        text = current.decode()
        if text.count(BEGIN) != text.count(END) or text.count(BEGIN) > 1:
            raise ValueError(f"ambiguous slim policy markers: {path}")
        block = (
            BEGIN + "\n# MEGAI slim\n"
            "Before project changes, the parent loads `megai-task-flow` and starts the linked Plane item. "
            "Plane is the only execution tracker. Reuse the identity through refinements; children never mutate it. "
            "Use `agent-worktree-lifecycle` for isolated writes and the agreed delivery target. "
            "Verify task acceptance with actual tests and review; security/data-integrity risks require independent review. "
            "Hand off at In Review, never Done. Main promotion requires separate explicit approval.\n"
            + END + "\n"
        )
        if BEGIN in text:
            start = text.index(BEGIN)
            finish = text.index(END) + len(END)
            if finish < start:
                raise ValueError(f"reversed slim markers: {path}")
            if text[finish:finish + 1] == "\n":
                finish += 1
            if text[start:finish] != block and not self.owned(path, current):
                raise ValueError(f"custom slim policy preserved: {path}")
            outside = text[:start] + text[finish:]
            updated = text[:start] + ("" if remove else block) + text[finish:]
        else:
            outside = text
            updated = text + ("\n" if text and not text.endswith("\n") else "") + ("" if remove else block)
        if not remove and any(term in outside for term in (
            ".todos", "taskflow-", "## MEGAI task flow", "## MEGAI Plane flow",
            "<!-- plane-workflow:begin -->", "<!-- asana-workflow:begin -->",
            "<!-- megai:task-flow:begin -->", "smart-development-orchestrator",
        )):
            raise ValueError(f"legacy/custom task policy preserved: {path}; reconcile it manually before slim adoption")
        if updated != text:
            self.stage(path, updated.encode(), before)
        if not remove:
            self.receipt[str(path)] = digest(updated.encode())
        else:
            self.receipt.pop(str(path), None)

    def shell_paths(self, remove: bool) -> None:
        paths = [HOME / name for name in (".bashrc", ".zshrc", ".profile")
                 if (HOME / name).exists() or (HOME / name).is_symlink()]
        if not paths and not remove:
            shell = Path(os.environ.get("SHELL", "")).name
            paths = [HOME / (".zshrc" if shell == "zsh" else ".bashrc" if shell == "bash" else ".profile")]
        begin = "# >>> megai-managed (do not edit) >>>"
        end = "# <<< megai-managed <<<"
        line = f'export PATH={shlex.quote(str(MEGAI / "bin"))}:"$PATH"'
        block = f"{begin}\n{line}\n{end}\n"
        legacy = f'{begin}\nexport PATH="{MEGAI}/bin:$PATH"\n{end}\n'
        for path in paths:
            before = read(path)
            text = (before or b"").decode()
            if text.count(begin) != text.count(end) or text.count(begin) > 1:
                raise ValueError(f"ambiguous PATH markers: {path}")
            if begin in text:
                start = text.index(begin)
                finish = text.index(end) + len(end)
                if finish < start:
                    raise ValueError(f"reversed PATH markers: {path}")
                if text[finish:finish + 1] == "\n":
                    finish += 1
                if text[start:finish] not in (block, legacy) and not self.owned(path, before or b""):
                    raise ValueError(f"custom PATH block preserved: {path}")
                updated = text[:start] + ("" if remove else block) + text[finish:]
            else:
                updated = text if remove else text + ("\n" if text and not text.endswith("\n") else "") + block
            if updated != text:
                self.stage(path, updated.encode(), before)
            if remove:
                self.receipt.pop(str(path), None)
            else:
                self.receipt[str(path)] = digest(updated.encode())

    def configure_pi_caveman(self, root: Path, remove: bool) -> None:
        """Select only the core Caveman skill while preserving unrelated settings."""
        if remove:
            # Uninstall must not guess which existing skill filters were user-owned.
            self.receipt.pop(str(root / "settings.json"), None)
            return
        path = root / "settings.json"
        before = read(path)
        key = str(path)
        if before is not None and key in self.prior_receipt and not self.owned(path, before):
            raise ValueError(f"custom Pi settings preserved: {path}; reconcile it manually")
        settings = load_json(path)
        skills = settings.get("skills", [])
        if isinstance(skills, dict):
            legacy = skills
            allowed = {"customDirectories", "enableSkillCommands"}
            unknown = set(legacy) - allowed
            if unknown:
                raise ValueError(f"unsupported legacy Pi skills keys: {sorted(unknown)}")
            if "customDirectories" not in legacy or not isinstance(legacy["customDirectories"], list):
                raise ValueError(f"malformed legacy Pi customDirectories: {path}")
            if any(not isinstance(item, str) for item in legacy["customDirectories"]):
                raise ValueError(f"malformed legacy Pi customDirectories: {path}")
            if "enableSkillCommands" in legacy:
                if not isinstance(legacy["enableSkillCommands"], bool):
                    raise ValueError(f"malformed legacy Pi enableSkillCommands: {path}")
                if "enableSkillCommands" not in settings:
                    settings["enableSkillCommands"] = legacy["enableSkillCommands"]
            skills = legacy["customDirectories"]
        if not isinstance(skills, list) or any(not isinstance(item, str) for item in skills):
            raise ValueError(f"expected Pi skills to be a string array: {path}")
        core_path = HOME / ".agents/skills/caveman/SKILL.md"
        core = "+" + str(core_path)
        if (
            os.environ.get("MEGAI_CAVEMAN", "1") == "1"
            and not core_path.is_file()
            and not self.allow_missing_caveman
        ):
            raise ValueError(f"Caveman core skill missing: {core_path}; run megai install")
        skills = [item for item in skills if item != core]
        for exclusion in ("!caveman*", "!cavecrew"):
            if exclusion not in skills:
                skills.append(exclusion)
        if os.environ.get("MEGAI_CAVEMAN", "1") == "1":
            skills.append(core)
        settings["skills"] = skills
        updated = encoded(settings)
        if updated != before:
            self.stage(path, updated, before)
            self.receipt[key] = digest(updated)

    def client(self, name: str, root: Path, remove: bool) -> None:
        # Validate configs without changing credentials, models, packages or hooks.
        for filename in ("settings.json", "mcp.json") if name != "codex" else ():
            obj = load_json(root / filename)
            if filename == "mcp.json" and not isinstance(obj.get("mcpServers", {}), dict):
                raise ValueError(f"invalid mcpServers: {root / filename}")
            if not remove and "taskflow-" in json.dumps(obj):
                raise ValueError(f"legacy board hooks preserved: {root / filename}; detach manually")
        if name == "codex":
            data = read(root / "config.toml")
            if data is not None:
                tomllib.loads(data.decode()) # existing MCP entries remain user-owned
        if not remove:
            for legacy in ("task-flow", "smart-development-orchestrator"):
                shared = HOME / ".agents/skills" / legacy
                if shared.exists() or shared.is_symlink():
                    raise ValueError(f"shared legacy skill preserved: {shared}; detach manually")
            if name == "pi" and (root / "skills/megai.md").exists():
                raise ValueError(f"legacy MEGAI skill preserved: {root / 'skills/megai.md'}; detach manually")
            for legacy in ("task-flow", "smart-development-orchestrator"):
                old = root / "skills" / legacy
                if old.exists() or old.is_symlink():
                    raise ValueError(f"legacy/custom skill preserved: {old}; detach manually before slim adoption")
            if name == "omp":
                agents = root / "agents"
                if agents.exists() and any("minimax" in p.name or p.name == "smart-router.md" for p in agents.iterdir()):
                    raise ValueError(f"legacy routing agents preserved: {agents}; detach manually")
        self.policy(root / ("CLAUDE.md" if name == "cc" else "RULES.md" if name == "omp" else "AGENTS.md"), remove)
        for relative, skill in (
            ("task-flow/skills/megai-task-flow/SKILL.md", "megai-task-flow"),
            ("skills/agent-worktree-lifecycle/SKILL.md", "agent-worktree-lifecycle"),
            ("pi-skill/SKILL.md", "megai"),
        ):
            skill_root = HOME / ".agents/skills" if name in ("codex", "pi") else root / "skills"
            self.asset(skill_root / skill / "SKILL.md", (SOURCE / relative).read_bytes(), remove)
        if name == "pi":
            self.configure_pi_caveman(root, remove)
            config_path = root / "mcp.json"
            config_before = read(config_path)
            config = json.loads(config_before) if config_before else {}
            zg = shutil.which("zg")
            servers = config.setdefault("mcpServers", {})
            key = str(config_path) + "#zvec_grep"
            entry = servers.get("zvec_grep")
            owned = entry is not None and self.prior_receipt.get(key) == digest(encoded(entry))
            if not remove and entry is not None and not owned:
                raise ValueError(f"unowned zvec_grep MCP preserved: {config_path}; reconcile manually")
            if remove:
                if owned:
                    del servers["zvec_grep"]
                    self.receipt.pop(key, None)
                    self.stage(config_path, encoded(config), config_before)
            elif zg and (entry is None or owned):
                servers["zvec_grep"] = {"command": zg, "args": ["server", "--stdio"], "lifecycle": "lazy"}
                self.receipt[key] = digest(encoded(servers["zvec_grep"]))
                self.stage(config_path, encoded(config), config_before)
        if name == "cc":
            load_json(HOME / ".claude.json")  # Existing MCP entries remain byte-identical.

    def apply(self, dry_run: bool, verify: bool = False) -> None:
        self.stage(RECEIPT, encoded(self.receipt), self.receipt_before)
        for path, before in self.originals.items():
            if read(path) != before:
                raise ValueError(f"destination changed during preflight: {path}")
        changes = {p: v for p, v in self.changes.items() if self.originals[p] != v}
        if verify and changes:
            raise ValueError("slim wiring is missing/stale; run megai wire for the selected harness")
        if dry_run or not changes:
            return
        backup_root = MEGAI / "backups"
        safe(backup_root / ".preflight")
        backup_root.mkdir(parents=True, exist_ok=True)
        recovery = Path(tempfile.mkdtemp(prefix="slim-wiring-", dir=backup_root))
        originals = {p: self.originals[p] for p in changes}
        manifest = {}
        for index, (path, data) in enumerate(originals.items()):
            name = str(index)
            if data is not None:
                (recovery / name).write_bytes(data)
                (recovery / name).chmod(0o600)
            manifest[str(path)] = name if data is not None else None
        (recovery / "manifest.json").write_bytes(encoded(manifest))
        (recovery / "manifest.json").chmod(0o600)
        applied = []
        try:
            for path, data in changes.items():
                # Refuse concurrent edits between preflight and publication.
                if read(path) != originals[path]:
                    raise ValueError(f"destination changed during install: {path}")
                atomic_write(path, data)
                applied.append(path)
        except BaseException:
            for path in reversed(applied):
                atomic_write(path, originals[path])
            raise
        print(f"slim wiring backup: {recovery}")


def atomic_write(path: Path, data: bytes | None) -> None:
    if data is None:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        if data.startswith(b"#!/"):
            tmp.chmod(0o700)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("client", choices=("all", "cc", "codex", "pi", "omp", "path"))
    parser.add_argument("--remove", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--install-preflight", action="store_true")
    args = parser.parse_args()
    if args.install_preflight and (not args.check or args.verify):
        parser.error("--install-preflight requires --check and cannot be combined with --verify")
    plan = Plan(allow_missing_caveman=args.install_preflight)
    for name, root in destinations().items():
        if args.client in ("all", name):
            plan.client(name, root, args.remove)
    bridge = b'#!/usr/bin/env bash\nexec bash "${MEGAI_HOME:-$HOME/.megai}/pi-skill/extensions/memory.sh" "$@"\n'
    if args.client != "path":
        plan.asset(MEGAI / "bin/megai-memory", bridge, args.remove)
        codedb_bridge = b'#!/usr/bin/env bash\nexec bash "${MEGAI_HOME:-$HOME/.megai}/pi-skill/extensions/codedb.sh" "$@"\n'
        plan.asset(MEGAI / "bin/megai-codedb", codedb_bridge, args.remove)
        if not args.check and not args.remove and not shutil.which("codedb"):
            raise ValueError("codedb is missing; run megai install before using slim")
    if args.client in ("all", "path"):
        plan.shell_paths(args.remove)
    if not args.check and not args.remove and args.client in ("all", "pi") and not shutil.which("zg"):
        raise ValueError("zg is missing; run megai install before using slim")
    plan.apply(args.check or args.verify, args.verify)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as error:
        raise SystemExit(f"slim wiring: {error}") from error
