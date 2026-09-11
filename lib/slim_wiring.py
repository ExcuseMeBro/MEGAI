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
import re
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
    def __init__(self) -> None:
        self.receipt_before = read(RECEIPT)
        self.receipt = json.loads(self.receipt_before) if self.receipt_before else {}
        if not isinstance(self.receipt, dict):
            raise ValueError("invalid slim ownership receipt")
        self.prior_receipt = dict(self.receipt)
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

    def retire(self, path: Path) -> None:
        """Remove only a previously receipted MEGAI asset; archive it in apply()."""
        current = read(path)
        if current is None:
            self.receipt.pop(str(path), None)
            return
        if not self.owned(path, current):
            raise ValueError(f"unowned retired asset preserved: {path}; reconcile manually")
        self.stage(path, None, current)
        self.receipt.pop(str(path), None)

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
            "Keep one canonical Git primary/Paseo project; use distinct managed task workspaces and return to one primary workspace after verified delivery. "
            "On Pi, load `megai-acceptance` before implementation: freeze criteria, capture actual tests/runtime evidence, "
            "require fresh independent Pi review and a source-current PASS before verified handoff. "
            "Missing tools, authorization or evidence are BLOCKED, not PASS. "
            "Security/data-integrity risks require independent review. "
            "Hand off at In Review, never Done. Main promotion requires separate explicit approval.\n"
            "Headroom provides local context compression, concise output and explicit persistent memory. "
            "Use tgrep for literal/regex discovery first, and only when a task-owned index is ready; its status is a readiness hint, not a freshness certificate. "
            "If tgrep is absent, fails, has no ready index, or differs from required semantics, use rg with the intended flags; a failed search is diagnostic, not zero matches. "
            "After edits, branch switches, ignore-rule changes or watcher warnings, use rg until a completed rebuild and restart is known to cover the current tree. "
            "Use codedb for structure and zvec-grep for intent. Confirm absence and exhaustive impact claims with native rg. "
            "Use Headroom recall for relevant prior decisions, and save only when persistence is requested. "
            "These are task-appropriate defaults, not mandatory extras; index on demand, never at startup. "
            "Preserve the chosen provider, model and thinking level; report unavailable tools instead of silently claiming use. "
            "Raw acceptance tests and diagnostics remain authoritative.\n"
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

    def configure_pi_resources(self, root: Path, remove: bool) -> None:
        """Keep Pi local resources authoritative and exclude shared duplicates."""
        from pi_model_policy import stage_model_policy

        stage_model_policy(self, root, SOURCE, remove)
        path = root / "settings.json"
        before = read(path)
        settings = load_json(path)
        skills = settings.get("skills", [])
        legacy_enable = None
        if isinstance(skills, dict):
            legacy = skills
            allowed = {"customDirectories", "enableSkillCommands"}
            unknown = set(legacy) - allowed
            if unknown:
                raise ValueError(f"unsupported legacy Pi skills keys: {sorted(unknown)}")
            skills = legacy.get("customDirectories")
            if not isinstance(skills, list) or any(not isinstance(item, str) for item in skills):
                raise ValueError(f"malformed legacy Pi customDirectories: {path}")
            if "enableSkillCommands" in legacy:
                legacy_enable = legacy["enableSkillCommands"]
                if not isinstance(legacy_enable, bool):
                    raise ValueError(f"malformed legacy Pi enableSkillCommands: {path}")
        if not isinstance(skills, list) or any(not isinstance(item, str) for item in skills):
            raise ValueError(f"expected Pi skills to be a string array: {path}")
        exclusion = "!" + str(HOME / ".agents/skills") + "/**"
        key = str(path) + "#shared-skill-exclusion"
        if remove:
            if self.prior_receipt.get(key) == digest(exclusion.encode()) and exclusion in skills:
                settings["skills"] = [item for item in skills if item != exclusion]
                self.receipt.pop(key, None)
                self.stage(path, encoded(settings), before)
        else:
            desired = skills if exclusion in skills else [exclusion, *skills]
            settings["skills"] = desired
            if legacy_enable is not None:
                settings["enableSkillCommands"] = legacy_enable
            if encoded(settings) != before:
                self.stage(path, encoded(settings), before)
            self.receipt[key] = digest(exclusion.encode())
        # Existing user filters, including an explicit Headroom opt-out, win.
        if not remove:
            for group in ("extensions", "packages"):
                entries = settings.get(group, [])
                if not isinstance(entries, list):
                    raise ValueError(f"invalid Pi {group} selections: {path}")
            legacy_skill = root / "skills/megai.md"
            if legacy_skill.exists() or legacy_skill.is_symlink():
                raise ValueError(f"legacy MEGAI skill preserved: {legacy_skill}; detach it manually")
        for relative in ("index.ts", "bridge.py", "assets.py", "persistence.py"):
            self.asset(root / "extensions/megai-headroom" / relative,
                       (SOURCE / "pi-skill/headroom" / relative).read_bytes(), remove)
        for relative in ("index.ts", "identity.mjs"):
            self.asset(root / "extensions/megai-workspace-guard" / relative,
                       (SOURCE / "pi-skill/workspace-guard" / relative).read_bytes(), remove)
        for relative in ("SKILL.md", "reference.md", "contract.example.json"):
            self.asset(root / "skills/megai-acceptance" / relative,
                       (SOURCE / "pi-skill/acceptance" / relative).read_bytes(), remove)
        skill = "appllama-app-design-skill"
        for relative in ("SKILL.md", "PROVENANCE.md", "upstream/SKILL.md", "upstream/LICENSE",
                         "upstream/references/image-assets.md", "upstream/references/motion.md",
                         "upstream/references/native-controls.md", "upstream/references/performance.md",
                         "upstream/references/simulator-loop.md"):
            self.asset(root / "skills" / skill / relative,
                       (SOURCE / "skills" / skill / relative).read_bytes(), remove)

    def retire_legacy_pi_assets(self, root: Path, remove: bool) -> None:
        """Retire only receipt-owned legacy Pi bridges and extension resources."""
        for path in (MEGAI / "bin/megai-memory", MEGAI / "pi-skill/extensions/memory.sh",
                     root / "extensions/megai-memory/index.ts"):
            self.retire(path)

    def retire_tree(self, path: Path, remove: bool) -> None:
        if not path.exists() and not path.is_symlink():
            return
        if path.is_symlink():
            raise ValueError(f"symlinked retired resource preserved: {path}; reconcile manually")
        if path.is_file():
            self.retire(path)
            return
        for child in path.iterdir():
            self.retire_tree(child, remove)
        # Stage only receipt-owned files. Retain directories: planning/checks
        # must never mutate them, and empty directories are not active skills.

    def client(self, name: str, root: Path, remove: bool) -> None:
        # Validate configs without changing credentials, parent models, packages or hooks.
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
        shared_caveman = HOME / ".agents/skills/caveman"
        # Empty directories retained by removal are inert and allow reinstall.
        shared_content = shared_caveman.is_symlink() or (
            shared_caveman.exists() and (
                not shared_caveman.is_dir() or any(
                    child.is_symlink() or not child.is_dir()
                    for child in shared_caveman.rglob("*")
                )
            )
        )
        if shared_content:
            if not remove:
                raise ValueError(f"shared legacy skill preserved: {shared_caveman}; detach manually")
            self.retire_tree(shared_caveman, remove)
        if not remove:
            for legacy in ("task-flow", "smart-development-orchestrator", "rtk", "agent-memory", "agentmemory", "megai-memory"):
                shared = HOME / ".agents/skills" / legacy
                if shared.exists() or shared.is_symlink():
                    raise ValueError(f"shared legacy skill preserved: {shared}; detach manually")
            if name == "pi" and (root / "skills/megai.md").exists():
                raise ValueError(f"legacy MEGAI skill preserved: {root / 'skills/megai.md'}; detach manually")
            for legacy in ("task-flow", "smart-development-orchestrator", "caveman", "rtk", "agent-memory", "agentmemory", "megai-memory"):
                if name == "pi" and legacy == "caveman":
                    continue
                old = root / "skills" / legacy
                if old.exists() or old.is_symlink():
                    raise ValueError(f"legacy/custom skill preserved: {old}; detach manually before slim adoption")
            for legacy in ("caveman", "rtk", "agent-memory", "agentmemory", "megai-memory"):
                old = root / "extensions" / legacy
                if old.exists() or old.is_symlink():
                    raise ValueError(f"legacy/custom extension preserved: {old}; detach manually before slim adoption")
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
            skill_root = root / "skills" if name == "pi" else HOME / ".agents/skills" if name == "codex" else root / "skills"
            self.asset(skill_root / skill / "SKILL.md", (SOURCE / relative).read_bytes(), remove)
            if skill == "megai":
                self.asset(skill_root / skill / "tgrep.md", (SOURCE / "pi-skill/tgrep.md").read_bytes(), remove)
                self.asset(skill_root / skill / "delegation.md", (SOURCE / "pi-skill/delegation.md").read_bytes(), remove)
        if name == "pi":
            if not remove:
                settings = load_json(root / "settings.json")
                retired = re.compile(r"(?:^|[/@:])(?:rtk|caveman|agent[-_]memory|agentmemory|megai-memory)(?:$|[/@.])", re.I)
                for group in ("skills", "extensions", "packages"):
                    entries = settings.get(group, [])
                    if group == "skills" and isinstance(entries, dict):
                        # The legacy object is validated and promoted below.
                        continue
                    if not isinstance(entries, list):
                        raise ValueError(f"invalid Pi {group} selections")
                    for entry in entries:
                        source = entry.get("source", "") if isinstance(entry, dict) else entry
                        if isinstance(source, str) and not source.startswith(("!", "-")) and retired.search(source):
                            raise ValueError(f"explicit retired Pi resource preserved: {source}; reconcile manually")
                old_style = root / "skills/caveman"
                if old_style.exists():
                    for child in old_style.iterdir():
                        if child.name not in ("SKILL.md", "LICENSE.md"):
                            raise ValueError(f"custom retired skill contents preserved: {child}")
                        if not self.owned(child, read(child) or b""):
                            raise ValueError(f"unowned retired skill preserved: {child}; reconcile manually")
            self.configure_pi_resources(root, remove)
            self.retire_legacy_pi_assets(root, remove)
            for retired_path in (root / "skills/caveman/SKILL.md", root / "skills/caveman/LICENSE.md"):
                self.retire(retired_path)
            cache_path = root / "mcp-cache.json"
            cache_before = read(cache_path)
            if cache_before is not None:
                cache = load_json(cache_path)
                servers_cache = cache.get("servers", {})
                if not isinstance(servers_cache, dict):
                    raise ValueError(f"invalid MCP cache servers: {cache_path}")
                for retired_name in ("rtk", "caveman", "agent-memory", "agentmemory", "agent_memory"):
                    servers_cache.pop(retired_name, None)
                if cache != json.loads(cache_before):
                    self.stage(cache_path, encoded(cache), cache_before)
            config_path = root / "mcp.json"
            config_before = read(config_path)
            config = json.loads(config_before) if config_before else {}
            zg = shutil.which("zg")
            servers = config.setdefault("mcpServers", {})
            if not isinstance(servers, dict):
                raise ValueError(f"invalid mcpServers: {config_path}")
            if not remove:
                for retired_name in ("rtk", "caveman", "agent-memory", "agentmemory", "agent_memory"):
                    if retired_name in servers:
                        raise ValueError(f"retired MCP server preserved: {retired_name}; back up and detach manually")
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
        modes = {str(path): path.stat().st_mode & 0o777 for path, data in originals.items() if data is not None}
        (recovery / "modes.json").write_bytes(encoded(modes))
        (recovery / "modes.json").chmod(0o600)
        for index, (path, data) in enumerate(originals.items()):
            name = str(index)
            if data is not None:
                (recovery / name).write_bytes(data)
                (recovery / name).chmod(0o600)
            manifest[str(path)] = name if data is not None else None
        (recovery / "manifest.json").write_bytes(encoded(manifest))
        (recovery / "manifest.json").chmod(0o600)
        # Publish the journal only after every recovery byte and manifest exist.
        journal = os.environ.get("MEGAI_TRANSACTION_LOG")
        if journal:
            log = Path(journal)
            safe(log)
            record = {"recovery": str(recovery), "after": {
                str(path): digest(data) if data is not None else None for path, data in changes.items()
            }}
            fd = os.open(log, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "a") as stream:
                stream.write(json.dumps(record) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
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
                # A concurrent writer owns the new bytes; never overwrite them.
                if read(path) != changes[path]:
                    continue
                atomic_write(path, originals[path])
                if originals[path] is not None:
                    path.chmod(modes[str(path)])
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


def legacy_memory_store_paths() -> tuple[Path, ...]:
    return (MEGAI / "memory", MEGAI / "memory.db", MEGAI / "agent-memory",
            HOME / ".agentmemory", HOME / ".config/agentmemory")


def check_legacy_memory_stores() -> None:
    for path in legacy_memory_store_paths():
        if path.is_symlink():
            raise ValueError(f"legacy memory store is symlinked; preserve and reconcile manually: {path}")
        if path.is_file() and path.stat().st_size:
            raise ValueError(f"nonempty legacy memory store preserved; migration is unsupported: {path}")
        if path.is_dir() and any(path.iterdir()):
            raise ValueError(f"nonempty legacy memory store preserved; migration is unsupported: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("client", choices=("all", "cc", "codex", "pi", "omp", "path"))
    parser.add_argument("--remove", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    plan = Plan()
    if not args.remove:
        check_legacy_memory_stores()
    if not args.remove and (MEGAI / "memory-process.json").exists():
        raise ValueError("legacy daemon receipt remains; verify/stop the owned process and privately archive its receipt before cutover; memory data is preserved")
    if not args.remove:
        state_path = MEGAI / "state.json"
        state_before = read(state_path)
        if state_before is not None:
            state = load_json(state_path)
            for group in ("tools", "ports"):
                entries = state.get(group, {})
                if not isinstance(entries, dict):
                    raise ValueError(f"invalid MEGAI state {group}")
                for retired_name in ("rtk", "caveman", "agent-memory", "agentmemory", "agent_memory"):
                    entries.pop(retired_name, None)
            if state != json.loads(state_before):
                plan.stage(state_path, encoded(state), state_before)
    for name, root in destinations().items():
        if args.client in ("all", name):
            plan.client(name, root, args.remove)
    bridge = b'#!/usr/bin/env bash\nset -euo pipefail\nroot="${MEGAI_HOME:-$HOME/.megai}"\nexec env -i HOME="$HOME" MEGAI_HOME="$root" PATH="${PATH:-/usr/bin:/bin}" "$root/venv/headroom/bin/python" -I -B "$root/pi-skill/headroom/bridge.py" "$@"\n'
    if args.client != "path":
        plan.asset(MEGAI / "bin/megai-headroom", bridge, args.remove)
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
