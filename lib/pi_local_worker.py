#!/usr/bin/env python3
"""Install/check only the opt-in native Pi local worker bridge; no runtime/service start."""
from __future__ import annotations

import argparse

from slim_wiring import MEGAI, SOURCE, Plan, destinations, read, safe

ASSETS = ("index.ts", "bridge.mjs", "README.md")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--apply", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    source = SOURCE / "pi-defaults/extensions/megai-local-worker"
    target = destinations()["pi"] / "extensions/megai-local-worker"
    plan = Plan()
    for name in ASSETS:
        data = read(source / name)
        if data is None:
            raise ValueError(f"Missing source asset: {name}")
        plan.asset(target / name, data, False)
    if target.exists():
        unknown = {p.name for p in target.iterdir()} - set(ASSETS)
        if unknown:
            raise ValueError(f"Unknown extension assets preserved: {sorted(unknown)}")
    if not args.apply:
        plan.apply(dry_run=True, verify=args.check)
        print("Local worker assets verified" if args.check else "Scoped preflight passed; use --apply")
        return
    # Share the existing durable wiring lock; Plan also rechecks receipt/file bytes.
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
    print(f"Installed only {target}; reload Pi explicitly to activate. No worker started; settings/auth/sessions untouched.")


if __name__ == "__main__":
    main()
