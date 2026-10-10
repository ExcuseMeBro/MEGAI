#!/usr/bin/env python3
"""Install/check only the durable Pi extension, with existing ownership/backups."""
from __future__ import annotations

import argparse

from slim_wiring import MEGAI, SOURCE, Plan, destinations, read, safe

ASSETS = ("index.ts", "store.mjs", "README.md")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--apply", action="store_true", help="Apply scoped changes")
    group.add_argument("--check", action="store_true", help="Verify exact installed assets")
    args = parser.parse_args()
    source = SOURCE / "pi-defaults/extensions/megai-durable-workflow"
    target = destinations()["pi"] / "extensions/megai-durable-workflow"
    plan = Plan()
    for name in ASSETS:
        data = read(source / name)
        if data is None:
            raise ValueError(f"Missing source asset: {name}")
        plan.asset(target / name, data, False)
    # Never claim an existing directory containing unknown implementation files.
    if target.exists():
        unknown = {p.name for p in target.iterdir()} - set(ASSETS)
        if unknown:
            raise ValueError(f"Unknown extension assets preserved: {sorted(unknown)}")
    if not args.apply:
        plan.apply(dry_run=True, verify=args.check)
        print("Durable Pi assets verified" if args.check else "Scoped preflight passed; use --apply")
        return
    lock = MEGAI / "durable-install.lock"
    safe(lock / ".preflight")
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        lock.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise ValueError("Installer busy/interrupted; reconcile owner before retry") from exc
    try:
        plan.apply(dry_run=False)
    finally:
        lock.rmdir()
    print(f"Installed only {target}; reload Pi to activate. Settings/auth/sessions untouched.")


if __name__ == "__main__":
    main()
