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


def pi_root() -> Path:
    return Path(os.environ.get("PI_CODING_AGENT_DIR", HOME / ".pi/agent"))


def paseo_config() -> Path:
    return Path(os.environ.get("PASEO_HOME") or HOME / ".paseo") / "config.json"


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
        """Detach only receipt-proven assets; apply() archives their original bytes."""
        current = read(path)
        if current is not None:
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
            "Keep one canonical Git primary/Paseo project; create managed worktree workspaces with its explicit projectId, never sibling project copies. "
            "Load `megai-acceptance` before implementation and at verification: freeze criteria, capture actual tests/runtime evidence, "
            "require fresh independent Pi review and a source-current PASS before verified handoff. "
            "Missing tools, authorization or evidence are BLOCKED, not PASS. "
            "Security/data-integrity risks require independent review. "
            "Hand off at In Review, never Done. Main promotion requires separate explicit approval.\n"
            "Parents and all delegated agents use Pi only. GPT-only delegation: subagents and reviewers use the Pi harness. "
            "Load `megai` for the Astra/Luna/Sol role map and explicit Paseo model/thinking selection. "
            "Verify the returned harness/model/thinking before task context; no non-GPT or non-Pi fallback. "
            "If Pi is unavailable, stop and report the blocker.\n"
            "Default workflow: load `megai` for coding tasks. Headroom provides local context compression, concise output and explicit persistent memory. "
            "Use tgrep for literal/regex discovery (rg fallback; follow megai's readiness/freshness rules), "
            "codedb for structural lookup and zvec-grep for intent search. "
            "Apply Ruff to changed Python, Headroom recall to relevant prior decisions, and matching Matt Pocock/UI-UX skills to the task. "
            "These are task-appropriate defaults, not mandatory extra calls; index on demand, never at startup. "
            "Keep acceptance tests, exit status and raw review/failure diagnostics authoritative. "
            "Respect explicit resource opt-outs and normal-mode requests; report unavailable tools instead of silently claiming use.\n"
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

    def paseo(self, remove: bool) -> None:
        # A host allowlist, not a model/provider credential rewrite. Never start
        # Paseo or silently re-enable other harnesses on slim uninstall.
        if remove:
            return
        path = paseo_config()
        before = read(path)
        if before is None:
            return
        config = json.loads(before)
        if not isinstance(config, dict):
            raise ValueError(f"expected Paseo config object: {path}")
        agents = config.setdefault("agents", {})
        if not isinstance(agents, dict):
            raise ValueError(f"invalid Paseo agents: {path}")
        providers = agents.setdefault("providers", {})
        if not isinstance(providers, dict):
            raise ValueError(f"invalid Paseo providers: {path}")
        for name, settings in providers.items():
            if not isinstance(settings, dict) or ("enabled" in settings and not isinstance(settings["enabled"], bool)):
                raise ValueError(f"invalid Paseo provider settings for {name}: {path}")
        for name in sorted(set(providers) | {"pi", "codex", "claude", "omp", "opencode", "copilot"}):
            providers.setdefault(name, {})["enabled"] = name == "pi"
        self.stage(path, encoded(config), before)

    def client(self, root: Path, remove: bool) -> None:
        # Only Pi is inspected or mutated. Other harnesses are not dependencies.
        for filename in ("settings.json", "mcp.json"):
            obj = load_json(root / filename)
            if filename == "mcp.json" and not isinstance(obj.get("mcpServers", {}), dict):
                raise ValueError(f"invalid mcpServers: {root / filename}")
            if not remove and "taskflow-" in json.dumps(obj):
                raise ValueError(f"legacy board hooks preserved: {root / filename}; detach manually")
        if not remove:
            if (root / "skills/megai.md").exists():
                raise ValueError(f"legacy MEGAI skill preserved: {root / 'skills/megai.md'}; detach manually")
            for legacy in ("task-flow", "smart-development-orchestrator"):
                old = root / "skills" / legacy
                if old.exists() or old.is_symlink():
                    raise ValueError(f"legacy/custom skill preserved: {old}; detach manually before slim adoption")
        if not remove:
            settings = load_json(root / "settings.json")
            retired = re.compile(r"(?:^|[/@:])(?:rtk|caveman|agent[-_]memory|agentmemory|megai-memory)(?:$|[/@.])", re.I)
            for group in ("skills", "extensions", "packages"):
                entries = settings.get(group, [])
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
        self.policy(root / "AGENTS.md", remove)
        # Pi normally discovers shared skills used by other harnesses. Exclude
        # that directory by default, without touching it. Explicit user filters
        # follow this default, so exact force-includes/opt-outs still win.
        settings_path = root / "settings.json"
        before = read(settings_path)
        settings = load_json(settings_path)
        selections = settings.get("skills", [])
        if not isinstance(selections, list) or not all(isinstance(s, str) for s in selections):
            raise ValueError(f"invalid Pi skill selections: {settings_path}")
        exclusion = "!" + str(HOME / ".agents/skills") + "/**"
        key = str(settings_path) + "#shared-skill-exclusion"
        if remove:
            if self.prior_receipt.get(key) == digest(exclusion.encode()):
                settings["skills"] = [s for s in selections if s != exclusion]
                self.receipt.pop(key, None)
                self.stage(settings_path, encoded(settings), before)
        elif exclusion not in selections:
            settings["skills"] = [exclusion, *selections]
            self.receipt[key] = digest(exclusion.encode())
            self.stage(settings_path, encoded(settings), before)
        for relative, skill in (
            ("task-flow/skills/megai-task-flow/SKILL.md", "megai-task-flow"),
            ("skills/agent-worktree-lifecycle/SKILL.md", "agent-worktree-lifecycle"),
            ("pi-skill/SKILL.md", "megai"),
            ("pi-skill/acceptance/SKILL.md", "megai-acceptance"),
        ):
            skill_root = root / "skills"
            self.asset(skill_root / skill / "SKILL.md", (SOURCE / relative).read_bytes(), remove)
            if skill == "megai":
                self.asset(skill_root / skill / "tgrep.md", (SOURCE / "pi-skill/tgrep.md").read_bytes(), remove)
            if skill == "megai-acceptance":
                for name in ("reference.md", "contract.example.json"):
                    self.asset(skill_root / skill / name, (SOURCE / "pi-skill/acceptance" / name).read_bytes(), remove)
        for retired in ("skills/caveman/SKILL.md", "skills/caveman/LICENSE.md"):
            self.retire(root / retired)
        for name in ("SKILL.md", "LICENSE.md"):
            shared = HOME / ".agents/skills/caveman" / name
            if str(shared) in self.prior_receipt:
                self.retire(shared)  # Unowned shared resources remain excluded, not deleted.
        for relative in ("lib/install_rtk.sh", "lib/install_agent_memory.sh", "lib/install_caveman.sh",
                         "pi-skill/extensions/memory.sh", "skills/caveman/SKILL.md", "skills/caveman/LICENSE.md"):
            self.retire(MEGAI / relative)
        self.retire(MEGAI / "bin/megai-memory")
        self.retire(MEGAI / "bin/rtk")
        for name in ("index.ts", "bridge.py", "assets.py", "persistence.py"):
            self.asset(root / "extensions/megai-headroom" / name,
                       (SOURCE / "pi-skill/headroom" / name).read_bytes(), remove)
        for name in ("index.ts", "identity.mjs"):
            self.asset(root / "extensions/megai-workspace-guard" / name,
                       (SOURCE / "pi-skill/workspace-guard" / name).read_bytes(), remove)
        # Metadata only, never session history or memory databases. Exact retired
        # server identities are pruned; unknown cache shapes fail before writes.
        cache_path = root / "mcp-cache.json"
        cache_before = read(cache_path)
        if cache_before is not None:
            cache = load_json(cache_path)
            cached = cache.get("servers", {})
            if not isinstance(cached, dict):
                raise ValueError(f"invalid MCP cache servers: {cache_path}")
            for name in ("rtk", "caveman", "agent-memory", "agentmemory", "agent_memory"):
                cached.pop(name, None)
            if cache != json.loads(cache_before):
                self.stage(cache_path, encoded(cache), cache_before)
        config_path = root / "mcp.json"
        config_before = read(config_path)
        config = json.loads(config_before) if config_before else {}
        zg = shutil.which("zg")
        servers = config.setdefault("mcpServers", {})
        for name in ("rtk", "caveman", "agent-memory", "agentmemory", "agent_memory"):
            if name in servers:
                raise ValueError(f"retired MCP server preserved: {name}; back up and detach manually")
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("client", choices=("pi", "path"))
    parser.add_argument("--remove", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if not args.remove and (MEGAI / "memory-process.json").exists():
        raise ValueError("legacy daemon receipt remains: verify/stop the owned process and privately archive its receipt before cutover; memory data is preserved")
    plan = Plan()
    if not args.remove:
        state_path = MEGAI / "state.json"
        state_before = read(state_path)
        if state_before is not None:
            state = load_json(state_path)
            for group in ("tools", "ports"):
                entries = state.get(group, {})
                if not isinstance(entries, dict):
                    raise ValueError(f"invalid MEGAI state {group}")
                for retired in ("rtk", "caveman", "agent-memory", "agentmemory", "agent_memory"):
                    entries.pop(retired, None)
            if state != json.loads(state_before):
                plan.stage(state_path, encoded(state), state_before)
    if args.client == "pi":
        plan.client(pi_root(), args.remove)
        plan.paseo(args.remove)
    if args.client != "path":
        bridge = b'#!/usr/bin/env bash\nset -euo pipefail\nroot="${MEGAI_HOME:-$HOME/.megai}"\nexec env -i HOME="$HOME" MEGAI_HOME="$root" PATH="${PATH:-/usr/bin:/bin}" "$root/venv/headroom/bin/python" -I -B "$root/pi-skill/headroom/bridge.py" "$@"\n'
        plan.asset(MEGAI / "bin/megai-headroom", bridge, args.remove)
        codedb_bridge = b'#!/usr/bin/env bash\nexec bash "${MEGAI_HOME:-$HOME/.megai}/pi-skill/extensions/codedb.sh" "$@"\n'
        plan.asset(MEGAI / "bin/megai-codedb", codedb_bridge, args.remove)
        if not args.check and not args.remove and not shutil.which("codedb"):
            raise ValueError("codedb is missing; run megai install before using slim")
    plan.shell_paths(args.remove)
    if not args.check and not args.remove and args.client == "pi" and not shutil.which("zg"):
        raise ValueError("zg is missing; run megai install before using slim")
    plan.apply(args.check or args.verify, args.verify)
    paseo_path = paseo_config()
    if not (args.check or args.verify or args.remove) and paseo_path in plan.changes and plan.changes[paseo_path] != plan.originals[paseo_path]:
        print("Paseo Pi-only allowlist updated; run `paseo reload` for a running daemon. Existing sessions are not stopped.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as error:
        raise SystemExit(f"slim wiring: {error}") from error
