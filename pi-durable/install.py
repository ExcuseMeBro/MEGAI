#!/usr/bin/env python3
"""Install only the standalone runtime and its launcher; no existing agent configuration changes."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from launcher import atomic_json, read_json, safe_path, sync_directory

ASSETS = ["package.json", "package-lock.json", "runtime.mjs", "worker.mjs", "launcher.py", "README.md"]


def _install(source, home, bin_dir, apply=False, offline=False):
    source = Path(source).resolve(strict=True)
    home = safe_path(home)
    bin_dir = safe_path(bin_dir)
    hashes = {}
    assets = {}
    for name in ASSETS:
        path = safe_path(source / name)
        if not path.is_file():
            raise ValueError(f"Missing runtime asset: {name}")
        assets[name] = path.read_bytes()
        hashes[name] = hashlib.sha256(assets[name]).hexdigest()
    version = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    target = safe_path(home / "pi-durable/runtime" / version)
    launcher = safe_path(bin_dir / "pi-durable")
    receipt_path = safe_path(home / "pi-durable/install.json")
    previous = read_json(receipt_path) if receipt_path.exists() else None
    if launcher.exists():
        if not previous or previous.get("launcher") != str(launcher) or hashlib.sha256(launcher.read_bytes()).hexdigest() != previous.get("launcherHash"):
            raise ValueError("Custom/changed launcher refused; reconcile before installation")
    if target.exists():
        manifest = read_json(target / "manifest.json")
        if manifest != hashes or any(hashlib.sha256(safe_path(target / name).read_bytes()).hexdigest() != value for name, value in hashes.items()):
            raise ValueError("Existing runtime drift; reconcile before installation")
    if not apply:
        return {"status": "preflight", "runtime": str(target), "launcher": str(launcher), "version": version}
    os.umask(0o077)
    home.mkdir(parents=True, exist_ok=True, mode=0o700)
    bin_dir.mkdir(parents=True, exist_ok=True)
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not target.exists():
        target.mkdir(mode=0o700)
        for name in ASSETS:
            (target / name).write_bytes(assets[name])
            (target / name).chmod(0o600)
        atomic_json(target / "manifest.json", hashes)
    command = ["npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund"]
    if offline:
        command.append("--offline")
    ready = target / "ready.json"
    if not ready.exists():
        subprocess.run(command, cwd=target, check=True, timeout=180)
    elif read_json(ready) != {"version": version}:
        raise ValueError("Runtime readiness marker drift")
    subprocess.run(["node", "--input-type=module", "-e",
                    "if (+process.versions.node.split('.')[0] < 24) throw Error('Node >=24 required'); "
                    "await import('./runtime.mjs'); console.log('standalone imports OK')"],
                   cwd=target, check=True, timeout=30)
    atomic_json(ready, {"version": version})
    # Stable dispatcher: upgrades publish only the private receipt, never replace a destination command.
    dispatch = ('import json,os,sys; r=json.load(open(sys.argv[1])); '
                'os.execv(sys.executable,[sys.executable,r["runtime"]+"/launcher.py",*sys.argv[2:]])')
    content = f"#!/bin/sh\n# MEGAI standalone Pi Durable (managed)\nexec python3 -c '{dispatch}' '{receipt_path}' \"$@\"\n"
    if "'" in str(receipt_path) or "\n" in str(receipt_path):
        raise ValueError("Unsupported install path characters")
    temporary = launcher.with_name(f".pi-durable-{version}")
    if temporary.exists():
        raise ValueError("Prior interrupted launcher publication; reconcile before retry")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o700)
    try:
        os.write(fd, content.encode())
        os.fsync(fd)
    finally:
        os.close(fd)
    # Revalidate the existing launcher immediately before publishing; never overwrite an unowned command.
    if launcher.exists() and (not previous or hashlib.sha256(launcher.read_bytes()).hexdigest() != previous.get("launcherHash")):
        raise ValueError("Launcher changed during installation")
    if previous:
        backup = home / "pi-durable/backups" / version
        backup.mkdir(parents=True, exist_ok=True, mode=0o700)
        if launcher.exists() and not (backup / "launcher").exists():
            shutil.copyfile(launcher, backup / "launcher")
            (backup / "launcher").chmod(0o600)
        if not (backup / "receipt.json").exists():
            atomic_json(backup / "receipt.json", previous)
    if launcher.exists():
        if launcher.read_bytes() != content.encode():
            raise ValueError("Managed launcher format changed; explicit migration required")
        temporary.unlink()
    else:
        # Atomic no-clobber publication: even an uncoordinated publisher cannot be overwritten.
        os.link(temporary, launcher)
        temporary.unlink()
    sync_directory(bin_dir)
    receipt = {"schema": 1, "version": version, "runtime": str(target), "launcher": str(launcher),
               "launcherHash": hashlib.sha256(content.encode()).hexdigest(), "assets": hashes}
    atomic_json(receipt_path, receipt)
    return {"status": "installed", **receipt}


def install(source, home, bin_dir, apply=False, offline=False):
    if not apply:
        return _install(source, home, bin_dir, False, offline)
    scope = safe_path(Path(home) / "pi-durable")
    os.umask(0o077)
    scope.mkdir(parents=True, exist_ok=True, mode=0o700)
    stat = scope.stat()
    if stat.st_uid != os.getuid() or stat.st_mode & 0o077:
        raise ValueError("Install scope must be private and user-owned")
    destination = safe_path(bin_dir)
    destination.mkdir(parents=True, exist_ok=True)
    fd = os.open(safe_path(scope / "install.lock"), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    bin_lock = os.open(safe_path(destination / ".pi-durable-install.lock"), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        # One destination lock coordinates different installation homes targeting this bin directory.
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(bin_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return _install(source, home, bin_dir, True, offline)
    finally:
        os.close(bin_lock)
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--home", default=os.environ.get("MEGAI_HOME", str(Path.home() / ".megai")))
    parser.add_argument("--bin-dir", default=str(Path.home() / ".local/bin"))
    args = parser.parse_args()
    print(json.dumps(install(Path(__file__).parent, args.home, args.bin_dir, args.apply, args.offline)))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(json.dumps({"status": "error", "message": str(error)}))
        sys.exit(1)
