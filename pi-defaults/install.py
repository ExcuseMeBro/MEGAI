#!/usr/bin/env python3
"""Install the clean Pi profile; --reset deletes Pi state without backups."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import shlex
import subprocess
import sys
import tempfile

# The clean profile always installs the newest Pi; the resolved version is recorded
# in the defaults manifest instead of being pinned here.
PI_PACKAGE = "@earendil-works/pi-coding-agent"

SOURCE = Path(__file__).resolve().parent
REPO = SOURCE.parent

# Skills the profile ships in skills/ (provenance in UI-SKILLS.md). install.py copies them
# into Pi's default skills directory, which a blanket "!**" operator filter hides, so
# profile_settings() also names each one explicitly.
def shipped_skills():
    return tuple(sorted(path.parent.name for path in (SOURCE / "skills").glob("*/SKILL.md")))


def run(*args, **kwargs):
    print("+", " ".join(str(a) for a in args), flush=True)
    subprocess.run([str(a) for a in args], check=True, **kwargs)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")
    path.chmod(0o600)


def remove(path):
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def profile_settings(versions, home, current=None):
    packages = []
    retired = ("@fission-ai/openspec", "@dietrichgebert/ponytail", "@weiping/pi-superpowers")
    configured = (current or {}).get("packages", [])
    if not isinstance(configured, list):
        raise ValueError("Pi packages must be a list")
    selected = set()
    for entry in configured:
        source = entry.get("source") if isinstance(entry, dict) else entry
        def matches(name):
            return isinstance(source, str) and (source == f"npm:{name}" or source.startswith(f"npm:{name}@"))
        if source == "./pellet-factory" or any(matches(name) for name in retired):
            continue
        managed = next((name for name in versions if matches(name)), None)
        if managed:
            updated = dict(entry) if isinstance(entry, dict) else {}
            updated["source"] = f"npm:{managed}@{versions[managed]}"
            packages.append(updated)
            selected.add(managed)
        else:
            packages.append(entry)
    packages.extend({"source": f"npm:{name}@{version}"}
                    for name, version in versions.items() if name not in selected)
    # Update managed packages while retaining unrelated packages and resource filters.
    # The provider, model,
    # thinking, timeout and retry choices are the operator's and survive an update.
    settings = dict(current or {})
    settings["packages"] = packages
    settings.setdefault("theme", "dark")
    settings.setdefault("defaultThinkingLevel", "high")
    skills = settings.get("skills")
    skills = list(skills) if isinstance(skills, list) else []
    narrow = f"!{home}/.agents/skills/**"
    if narrow not in skills:
        skills.append(narrow)
    # Explicit includes win over the operator's blanket "!**" exclude; keep them stable
    # and idempotent so repeated installs do not grow the list.
    for name in shipped_skills():
        enabled = f"+skills/{name}/SKILL.md"
        if enabled not in skills:
            skills.append(enabled)
    settings["skills"] = skills
    return settings


def profile_mcp(defaults, home, current=None):
    """Brokan replaces retired task servers; preserve unrelated operator servers."""
    mcp = dict(current or {})
    servers = mcp.get("mcpServers")
    if servers is None:
        servers = {}
    if not isinstance(servers, dict):
        raise SystemExit("Existing mcp.json has a non-object mcpServers; reconcile it before install")
    servers = dict(servers)
    servers.pop("pellet", None)
    servers.pop("plane", None)
    brokan = servers.get("brokan", {})
    if not isinstance(brokan, dict):
        raise SystemExit("Existing Brokan MCP entry is not an object; reconcile it before install")
    brokan = dict(brokan)
    brokan.setdefault("command", "brokan")
    brokan.setdefault("args", ["mcp"])
    brokan["enabled"] = True
    servers["brokan"] = brokan
    mcp["mcpServers"] = servers
    settings = mcp.get("settings")
    if settings is None:
        settings = {}
    if not isinstance(settings, dict):
        raise SystemExit("Existing mcp.json has a non-object settings; reconcile it before install")
    for key, value in (("autoAuth", False), ("directTools", False), ("mcpFooterStatus", "compact")):
        settings.setdefault(key, value)
    mcp["settings"] = settings
    return mcp


def read_object(path):
    """Read an existing JSON object, or nothing when the file is absent.

    An unreadable or non-object file fails the install instead of being replaced:
    these files also carry operator-owned settings.
    """
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except ValueError as exc:
        raise SystemExit(f"Existing {path} is not valid JSON; reconcile it before install") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"Existing {path} is not a JSON object; reconcile it before install")
    return data


def defaults_only(current, profile):
    """Profile values apply only where the operator left the key unset."""
    merged = dict(current or {})
    for key, value in profile.items():
        merged.setdefault(key, value)
    return merged


HEADROOM_BRIDGE = (
    b'#!/usr/bin/env bash\nset -euo pipefail\nroot="${MEGAI_HOME:-$HOME/.megai}"\n'
    b'exec env -i HOME="$HOME" MEGAI_HOME="$root" PATH="${PATH:-/usr/bin:/bin}"'
    b' "$root/venv/headroom/bin/python" -I -B "$root/pi-skill/headroom/bridge.py" "$@"\n'
)


LEGACY_FACTORY_DIGEST = "c8aa7a4d2e81e5c7558fc36e01f9a38de71379bb3d849428444dce14b703618f"


def retire_legacy_factory_prompt(agent, home):
    """Archive only our exact former Plane /factory prompt; never remove an override."""
    candidates = (agent / "prompts/factory.md", agent / "defaults/prompts/factory.md")
    existing = [p for p in candidates if p.exists() or p.is_symlink()]
    for path in existing:
        if (path.is_symlink() or not path.is_file() or
                hashlib.sha256(path.read_bytes()).hexdigest() != LEGACY_FACTORY_DIGEST):
            raise SystemExit(f"Unowned /factory prompt {path}; reconcile before install")
    if not existing:
        return None
    root = home / ".megai/private-backups"
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if root.is_symlink() or root.stat().st_uid != os.getuid() or root.stat().st_mode & 0o077:
        raise SystemExit(f"Factory backup directory must be private and user-owned: {root}")
    backup = root / "factory-plane-prompt"
    index = 0
    while backup.exists() or backup.is_symlink():
        index += 1
        backup = root / f"factory-plane-prompt-{index}"
    backup.mkdir(mode=0o700)
    for path in existing:
        target = backup / ("installed.md" if path.parent == agent / "prompts" else "defaults.md")
        target.write_bytes(path.read_bytes())
        target.chmod(0o600)
        if hashlib.sha256(target.read_bytes()).hexdigest() != LEGACY_FACTORY_DIGEST:
            raise SystemExit(f"Factory prompt backup not verified: {target}")
    for path in existing:
        if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != LEGACY_FACTORY_DIGEST:
            raise SystemExit(f"/factory prompt changed after backup; retained: {path}")
        path.unlink()
    return backup


# Exact installed files from the last verified factory release. Preserve foreign
# overrides and historical receipts; only known factory assets and JIT caches retire.
FACTORY_ASSETS = {
    "extensions/megai-factory/index.ts": "823488d418c1b41bb184971a82ea7683a8c6838439fc90ead07ebbbf6cadb77f",
    "extensions/megai-factory/runner.mjs": "9239b5ca39c546a3bda0d1d249909af3d970192248326aca6319bf51dff9d22b",
    "pellet-factory/package.json": "ffd542aa607217dab54bee203c059aa31303a911f43f7a70af604217046c41b3",
    "pellet-factory/prompts/factory.md": "d84aaa0bdb3fa5cc75b776072683a580680c5a907784dc9a37d48294b140b31d",
    "defaults/FACTORY.md": "e14ccc743056f7dcff4efaeaee448bd441dfc76f90b72d95d981c2e1235147b8",
}
FACTORY_CACHE = re.compile(r"(?:megai-factory-index\.[a-f0-9]{8}|private-backups-factory-reach-1fc1fd07\.probe\.[a-f0-9]{8})\.mjs\Z")


def retire_factory_assets(agent, home):
    """Back up and remove only verified factory assets/cache, never task evidence."""
    paths = {}
    for name, digest in FACTORY_ASSETS.items():
        for candidate in (name, "defaults/" + name) if not name.startswith("defaults/") else (name,):
            path = agent / candidate
            if path.exists() or path.is_symlink():
                paths[path] = digest
    cache = agent / "cache/jiti"
    if cache.exists() or cache.is_symlink():
        if cache.is_symlink() or not cache.is_dir() or cache.stat().st_uid != os.getuid():
            raise SystemExit(f"Unowned factory cache directory: {cache}")
        for path in cache.iterdir():
            if FACTORY_CACHE.fullmatch(path.name):
                paths[path] = None
    for path, digest in paths.items():
        for parent in (path.parent, *path.parents):
            if parent == agent.parent:
                break
            if parent.is_symlink():
                raise SystemExit(f"Symlinked factory asset parent: {parent}")
        if path.is_symlink() or not path.is_file() or path.stat().st_uid != os.getuid():
            raise SystemExit(f"Unowned factory asset: {path}")
        data = path.read_bytes()
        actual = hashlib.sha256(data).hexdigest()
        if digest is not None and actual != digest:
            raise SystemExit(f"Changed factory asset; retained: {path}")
        if digest is None and b"factory_delegate" not in data and b"factory-contract-probe" not in data:
            raise SystemExit(f"Unknown factory cache; retained: {path}")
        paths[path] = actual
    for name in ("extensions/megai-factory", "pellet-factory",
                 "defaults/extensions/megai-factory", "defaults/pellet-factory"):
        directory = agent / name
        if directory.exists() or directory.is_symlink():
            if directory.is_symlink() or not directory.is_dir() or directory.stat().st_uid != os.getuid():
                raise SystemExit(f"Unowned factory directory: {directory}")
            for path in directory.rglob("*"):
                if (path.is_symlink() or (path.is_dir() and path != directory / "prompts")
                        or (path.is_file() and path not in paths)
                        or (not path.is_dir() and not path.is_file())):
                    raise SystemExit(f"Unknown factory directory entry; retained: {path}")
    if not paths:
        return None
    root = home / ".megai/private-backups"
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if root.is_symlink() or root.stat().st_uid != os.getuid() or root.stat().st_mode & 0o077:
        raise SystemExit(f"Factory backup directory must be private and user-owned: {root}")
    backup = Path(tempfile.mkdtemp(prefix="factory-retirement-", dir=root))
    receipt = {}
    for path, digest in paths.items():
        relative = path.relative_to(agent)
        saved = backup / relative
        saved.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        saved.write_bytes(path.read_bytes())
        saved.chmod(0o600)
        if hashlib.sha256(saved.read_bytes()).hexdigest() != digest:
            raise SystemExit(f"Factory retirement backup verification failed: {path}")
        receipt[str(relative)] = digest
    record = backup / "receipt.json"
    record.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    record.chmod(0o600)
    for path, digest in paths.items():
        if (path.is_symlink() or not path.is_file() or
                hashlib.sha256(path.read_bytes()).hexdigest() != digest):
            raise SystemExit(f"Factory asset changed after backup; retained: {path}")
        path.unlink()
    for name in ("extensions/megai-factory", "pellet-factory/prompts", "pellet-factory",
                 "defaults/extensions/megai-factory", "defaults/pellet-factory/prompts",
                 "defaults/pellet-factory"):
        directory = agent / name
        if directory.is_dir() and not directory.is_symlink():
            try:
                directory.rmdir()  # never recurse into foreign resources
            except OSError:
                pass
    return backup


def retire_duplicate_headroom(agent, home):
    """Keep exactly one headroom adapter installed.

    Two adapter names expose headroom_retrieve and headroom_memory twice, and Pi
    refuses one of them. The profile owns extensions/megai-headroom, so the duplicate
    is moved aside, never deleted.
    """
    duplicate = agent / "extensions/headroom"
    if not (duplicate.exists() or duplicate.is_symlink()):
        return None
    root = home / ".pi/backups"
    root.mkdir(parents=True, exist_ok=True)
    target = root / "headroom-duplicate"
    index = 0
    while target.exists() or target.is_symlink():
        index += 1
        target = root / f"headroom-duplicate-{index}"
    shutil.move(str(duplicate), str(target))
    return target


INJECTED_BLOCK = re.compile(
    rb"<!-- megai:[a-z-]+:begin -->.*?<!-- megai:[a-z-]+:end -->", re.S
)


def profile_agents_md(current, source):
    """Keep the MEGAI blocks that other wirings inject into this policy document.

    install.py owns AGENTS.md while lib/slim_wiring.py and the model policy own the
    marked blocks inside it. Writing the file wholesale dropped those blocks together
    with their ownership receipts, so the next wiring check reported stale wiring.
    """
    if not current:
        return source
    kept = [
        block
        for block in INJECTED_BLOCK.findall(current)
        if block.split(b"\n", 1)[0] not in source
    ]
    if not kept:
        return source
    text = source.rstrip(b"\n") + b"\n"
    for block in kept:
        text += b"\n" + block.rstrip(b"\n") + b"\n"
    return text


def apply_pi_policy(repo, env):
    """Apply the Pi policy transaction: owned assets, retirements and model policy.

    MEGAI_PI_POLICY is a deterministic test seam for the policy command. A failure is
    fatal: the profile must not report success while an owned asset, a retirement or
    the workflow policy did not apply.
    """
    seam = os.environ.get("MEGAI_PI_POLICY")
    command = shlex.split(seam) if seam else [sys.executable, str(repo / "lib/pi_model_policy.py")]
    if subprocess.run(command, env=env).returncode:
        raise SystemExit(
            "Pi policy activation failed; inspect the reported conflict and current assets "
            "before retry."
        )


def install(reset=False, remove_omp=False):
    home = Path.home()
    agent = home / ".pi/agent"
    shared = home / ".megai"
    local_bin = home / ".local/bin"
    if sys.version_info < (3, 11):
        raise SystemExit("Python 3.11+ is required before reset")
    for name, expected in (("MEGAI_HOME", shared), ("PI_CODING_AGENT_DIR", agent)):
        if (
            os.environ.get(name)
            and Path(os.environ[name]).expanduser().resolve() != expected.resolve()
        ):
            raise SystemExit(
                f"Custom {name} is unsupported by the clean default profile"
            )
    # Reject redirected config roots before destructive operations.
    for path in (home / ".pi", agent, home / ".omp", local_bin):
        if path.is_symlink():
            raise SystemExit(f"Refusing symlinked configuration destination: {path}")
    if (
        agent.exists()
        and any(agent.iterdir())
        and not (agent / "defaults/manifest.json").exists()
        and not reset
    ):
        raise SystemExit(
            "Existing Pi configuration. Use --reset for the authorized full deletion (no backup)."
        )
    for command in ("node", "npm", "python3", "git", "uv", "jq"):
        if not shutil.which(command):
            raise SystemExit(f"Required command missing: {command}")
    run(
        "node",
        "-e",
        "const [major,minor]=process.versions.node.split('.').map(Number); if(major<22 || (major===22 && minor<22)) {console.error('Node 22.22+ required'); process.exit(1)}",
    )
    for relative in ("package.json", "package-lock.json", "verify.mjs",
                     "AGENTS.md", "policy-contract.mjs"):
        if not (SOURCE / relative).is_file():
            raise SystemExit(f"Incomplete profile source: {relative}")
    # Check the source before --reset or any package/config mutation: a stale
    # template must not replace the current Brokan/delivery instructions.
    run("node", SOURCE / "policy-contract.mjs", SOURCE / "AGENTS.md")
    if not reset:
        run(sys.executable, REPO / "lib/pi_engineering.py", env={
            **os.environ, "MEGAI_HOME": str(shared), "MEGAI_SOURCE": str(REPO),
        })
    if reset:
        remove(home / ".pi")
    if remove_omp:
        executable = shutil.which("omp")
        if executable:
            manager = "bun" if ".bun/" in str(Path(executable).resolve()) else "npm"
            run(
                manager,
                "remove" if manager == "bun" else "uninstall",
                "-g",
                "@oh-my-pi/pi-coding-agent",
            )
        remove(home / ".omp")
        for name in ("omp-agents", "omp-config", "omp-skill"):
            remove(shared / name)
    manager = "bun" if shutil.which("bun") else "npm"
    run(
        manager,
        "add" if manager == "bun" else "install",
        "-g",
        "--ignore-scripts",
        f"{PI_PACKAGE}@latest",
    )
    selected = shutil.which("pi")
    installed = (
        subprocess.check_output([selected, "--version"], text=True).strip()
        if selected
        else ""
    )
    if not re.fullmatch(r"\d+\.\d+\.\d+", installed):
        raise SystemExit(
            "PATH does not select a working Pi binary; put the installed Pi binary directory first"
        )
    agent.mkdir(parents=True, exist_ok=True, mode=0o700)
    agent.chmod(0o700)
    profile_source = shared / "pi-profile"
    if REPO != profile_source.resolve():
        for relative in ("pi-defaults", "lib", "bin", "pi-skill/headroom"):
            shutil.copytree(
                REPO / relative,
                profile_source / relative,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("node_modules", "__pycache__"),
            )
    defaults = agent / "defaults"
    shutil.copytree(
        SOURCE,
        defaults,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(
            "node_modules", "__pycache__", "workflow.py", "orchestrator.py",
            "delivery.py", "ORCHESTRATOR.md", "projects"),
    )
    retire_legacy_factory_prompt(agent, home)
    retire_factory_assets(agent, home)
    npm_root = agent / "npm"
    npm_root.mkdir(exist_ok=True)
    for name in ("package.json", "package-lock.json"):
        shutil.copy2(SOURCE / name, npm_root / name)
    run(
        "npm",
        "ci",
        "--prefix",
        npm_root,
        "--omit=peer",
        "--ignore-scripts",
        "--no-audit",
        "--no-fund",
    )
    # npm ci removes the retired package; remove only this profile's exact old link.
    retired_cli = local_bin / "openspec"
    if retired_cli.is_symlink() and os.readlink(retired_cli) == str(npm_root / "node_modules/.bin/openspec"):
        retired_cli.unlink()
    # Existing shared search/Headroom installations are independent of Pi state.
    # Reuse their verified installers, with no legacy harness wiring or backups.
    if not (shared / "lib/ui.sh").exists():
        shutil.copytree(REPO / "lib", shared / "lib", dirs_exist_ok=True)
        shutil.copytree(
            REPO / "pi-skill/headroom", shared / "pi-skill/headroom", dirs_exist_ok=True
        )
    os.environ["PATH"] = f"{shared / 'bin'}:{local_bin}:" + os.environ.get("PATH", "")
    env = {**os.environ, "MEGAI_HOME": str(shared), "MEGAI_SOURCE": str(REPO)}
    for name in ("ruff", "codedb", "tgrep", "headroom"):
        run("bash", REPO / f"lib/install_{name}.sh", env=env)
    # The policy transaction also retires assets from earlier installs, so it runs on
    # every install, not only on first adoption.
    shutil.copytree(
        REPO / "pi-skill/headroom", shared / "pi-skill/headroom", dirs_exist_ok=True
    )
    (shared / "bin").mkdir(exist_ok=True)
    shutil.copy2(REPO / "bin/megai", shared / "bin/megai")
    (shared / "bin/megai").chmod(0o755)
    shutil.copytree(SOURCE / "extensions", agent / "extensions", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("megai-durable-workflow", "megai-command-receipts",
                                                  "megai-local-worker", "project-rules.ts"))
    headroom = agent / "extensions/megai-headroom"
    headroom.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO / "pi-skill/headroom/index.ts", headroom / "index.ts")
    retire_duplicate_headroom(agent, home)
    # The engineering migration owns these files and checks collisions before writes.
    shutil.copytree(SOURCE / "skills", agent / "skills", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("codebase-design", "diagnosing-bugs", "tdd", "code-review"))
    shutil.copytree(SOURCE / "prompts", agent / "prompts", dirs_exist_ok=True)
    source_md = SOURCE / "AGENTS.md"
    agents_md = agent / "AGENTS.md"
    before_md = agents_md.read_bytes() if agents_md.exists() else None
    if before_md is None:
        agents_md.write_bytes(source_md.read_bytes())
        agents_md.chmod(source_md.stat().st_mode & 0o777)
    # The policy transaction runs after profile-owned skills and AGENTS.md are refreshed,
    # so their exact source bytes cannot be mistaken for unowned legacy conflicts.
    apply_pi_policy(REPO, env)
    versions = json.loads((SOURCE / "package.json").read_text())["dependencies"]
    write_json(
        agent / "settings.json",
        profile_settings(versions, home, read_object(agent / "settings.json")),
    )
    run(sys.executable, REPO / "lib/pi_engineering.py", "--apply", env=env)
    write_json(
        agent / "mcp.json",
        profile_mcp(defaults, home, read_object(agent / "mcp.json")),
    )
    write_json(
        agent / "web-search.json",
        defaults_only(
            read_object(agent / "web-search.json"),
            {
                "provider": "exa",
                "workflow": "none",
                "allowBrowserCookies": False,
                "autoOpenBrowser": False,
            },
        ),
    )
    # Preserve the selected model; no extra Pi agent profiles are installed.
    local_bin.mkdir(parents=True, exist_ok=True)
    bridge = shared / "bin/megai-headroom"
    # One canonical byte string: lib/slim_wiring.py owns this same path and refuses a
    # file that differs from its own asset, so the two installers must agree.
    bridge.write_bytes(HEADROOM_BRIDGE)
    bridge.chmod(0o755)
    launcher = local_bin / "pi-workflow"
    legacy_launcher = b'#!/bin/sh\nexec python3 "$HOME/.pi/agent/defaults/workflow.py" "$@"\n'
    if launcher.is_file() and not launcher.is_symlink():
        if launcher.read_bytes() != legacy_launcher:
            raise SystemExit("Unrecognized pi-workflow launcher; preserve it and reconcile manually")
        launcher.unlink()
    shell_file = (
        home / ".zshrc"
        if os.environ.get("SHELL", "").endswith("zsh")
        else home / ".bashrc"
    )
    shell_text = shell_file.read_text() if shell_file.exists() else ""
    line = 'export PATH="$HOME/.local/bin:$HOME/.megai/bin:$PATH"'
    if line not in shell_text:
        shell_file.write_text(shell_text + "\n# Pi defaults\n" + line + "\n")
    # This marker opts the MEGAI Pi launcher into the new profile, never old wiring.
    write_json(
        defaults / "manifest.json",
        {"schema": 1, "profile": "clean", "pi": installed, "packages": versions},
    )
    print(
        "Installed. Pi authentication was reset when --reset was used: open pi and /login. No backups created."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete ~/.pi including auth and sessions; no backup",
    )
    parser.add_argument(
        "--remove-omp",
        action="store_true",
        help="Uninstall OMP and delete ~/.omp; no backup",
    )
    args = parser.parse_args()
    install(args.reset, args.remove_omp)
