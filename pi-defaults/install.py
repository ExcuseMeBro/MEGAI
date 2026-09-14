#!/usr/bin/env python3
"""Install the clean Pi profile; --reset deletes Pi state without backups."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

SOURCE = Path(__file__).resolve().parent
REPO = SOURCE.parent


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
    for relative in ("package.json", "package-lock.json", "workflow.py", "verify.mjs"):
        if not (SOURCE / relative).is_file():
            raise SystemExit(f"Incomplete profile source: {relative}")
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
    if shutil.which("bun"):
        run(
            "bun",
            "add",
            "-g",
            "--ignore-scripts",
            "@earendil-works/pi-coding-agent@0.85.1",
        )
    else:
        run(
            "npm",
            "install",
            "-g",
            "--ignore-scripts",
            "@earendil-works/pi-coding-agent@0.85.1",
        )
    selected = shutil.which("pi")
    if (
        not selected
        or subprocess.check_output([selected, "--version"], text=True).strip()
        != "0.85.1"
    ):
        raise SystemExit(
            "PATH does not select Pi 0.85.1; put the installed Pi binary directory first"
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
        ignore=shutil.ignore_patterns("node_modules", "__pycache__"),
    )
    shutil.copy2(REPO / "lib/plane_mcp_headers.py", defaults / "plane_mcp_headers.py")
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
    # Existing shared search/Headroom installations are independent of Pi state.
    # Reuse their verified installers, with no legacy harness wiring or backups.
    if not (shared / "lib/ui.sh").exists():
        shutil.copytree(REPO / "lib", shared / "lib", dirs_exist_ok=True)
        shutil.copytree(
            REPO / "pi-skill/headroom", shared / "pi-skill/headroom", dirs_exist_ok=True
        )
    os.environ["PATH"] = f"{shared / 'bin'}:{local_bin}:" + os.environ.get("PATH", "")
    env = {**os.environ, "MEGAI_HOME": str(shared), "MEGAI_SOURCE": str(REPO)}
    for name in ("ruff", "codedb", "tgrep", "zvec_grep", "headroom"):
        run("bash", REPO / f"lib/install_{name}.sh", env=env)
    shutil.copytree(
        REPO / "pi-skill/headroom", shared / "pi-skill/headroom", dirs_exist_ok=True
    )
    (shared / "bin").mkdir(exist_ok=True)
    shutil.copy2(REPO / "bin/megai", shared / "bin/megai")
    (shared / "bin/megai").chmod(0o755)
    shutil.copytree(SOURCE / "extensions", agent / "extensions", dirs_exist_ok=True)
    headroom = agent / "extensions/headroom"
    headroom.mkdir(exist_ok=True)
    shutil.copy2(REPO / "pi-skill/headroom/index.ts", headroom / "index.ts")
    shutil.copytree(SOURCE / "skills", agent / "skills", dirs_exist_ok=True)
    shutil.copy2(SOURCE / "AGENTS.md", agent / "AGENTS.md")
    versions = json.loads((SOURCE / "package.json").read_text())["dependencies"]
    packages = []
    for name, version in versions.items():
        if name == "@fission-ai/openspec":
            continue
        entry = {"source": f"npm:{name}@{version}"}
        if name == "@weiping/pi-superpowers":
            # pi-subagents is the single delegation implementation.
            entry["extensions"] = ["extensions/bootstrap.ts"]
        packages.append(entry)
    write_json(
        agent / "settings.json",
        {
            "theme": "dark",
            "defaultThinkingLevel": "high",
            "packages": packages,
            "skills": [f"!{home}/.agents/skills/**"],
            "subagents": {
                "projectRootResolution": "git-root",
                "agentOverrides": {
                    name: {"model": "inherit", "fallbackModels": []}
                    for name in (
                        "backend",
                        "frontend",
                        "security",
                        "tester",
                        "reviewer",
                    )
                },
            },
        },
    )
    write_json(
        agent / "mcp.json",
        {
            "settings": {
                "autoAuth": False,
                "directTools": False,
                "mcpFooterStatus": "compact",
            },
            "mcpServers": {
                "plane": {
                    "url": "https://mcp.plane.so/http/api-key/mcp",
                    "auth": False,
                    "lifecycle": "lazy",
                    "includeTools": [
                        "workitem*",
                        "project",
                        "state",
                        "label",
                        "member",
                        "workspace",
                        "get_pql_reference",
                    ],
                    "requestHeadersCommand": {
                        "command": "python3",
                        "args": [
                            str(defaults / "plane_mcp_headers.py"),
                            "--token-file",
                            str(home / ".config/megai/credentials/plane-api-token"),
                            "--workspace",
                            "brodev",
                        ],
                    },
                },
                "zvec_grep": {
                    "command": shutil.which("zg"),
                    "args": ["server", "--stdio", "--listen", "127.0.0.1:17999"],
                    "lifecycle": "lazy",
                },
            },
        },
    )
    write_json(
        agent / "web-search.json",
        {
            "provider": "exa",
            "workflow": "none",
            "allowBrowserCookies": False,
            "autoOpenBrowser": False,
        },
    )
    # All children inherit the selected model. Restrict the independent reviewer.
    agents = agent / "agents"
    agents.mkdir(exist_ok=True)
    (agents / "reviewer.md").write_text(
        "---\nname: reviewer\ndescription: Independent read-only code and evidence review\ntools: read, grep, find, ls, bash\ncompletionGuard: false\n---\nReview only the assigned scope. Read-only: do not edit, commit, integrate, delegate, or mutate Plane. Use read-only commands; report concrete findings and evidence. Never read credentials.\n"
    )
    local_bin.mkdir(parents=True, exist_ok=True)
    bridge = shared / "bin/megai-headroom"
    bridge.write_text(
        '#!/bin/sh\nexec "$HOME/.megai/venv/headroom/bin/python" -I -B "$HOME/.megai/pi-skill/headroom/bridge.py" "$@"\n'
    )
    bridge.chmod(0o755)
    for name, target in {
        "openspec": npm_root / "node_modules/.bin/openspec",
        "zvec-grep": Path(shutil.which("zg")),
    }.items():
        link = local_bin / name
        if link.exists() or link.is_symlink():
            if link.is_symlink() and link.resolve() == target.resolve():
                continue
            raise SystemExit(
                f"Existing command requires explicit reconciliation: {link}"
            )
        link.symlink_to(target)
    launcher = local_bin / "pi-workflow"
    launcher.write_text(
        '#!/bin/sh\nexec python3 "$HOME/.pi/agent/defaults/workflow.py" "$@"\n'
    )
    launcher.chmod(0o755)
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
        {"schema": 1, "profile": "clean", "pi": "0.85.1", "packages": versions},
    )
    run(
        str(local_bin / "openspec"),
        "config",
        "set",
        "telemetry.enabled",
        "false",
        env={**os.environ, "OPENSPEC_TELEMETRY": "0"},
    )
    with tempfile.TemporaryDirectory(prefix="pi-openspec-") as staging:
        run(
            str(local_bin / "openspec"),
            "init",
            staging,
            "--tools",
            "pi",
            "--profile",
            "core",
            "--no-animation",
            env={**os.environ, "OPENSPEC_TELEMETRY": "0"},
        )
        for resource in ("skills", "prompts"):
            shutil.copytree(
                Path(staging) / ".pi" / resource, agent / resource, dirs_exist_ok=True
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
