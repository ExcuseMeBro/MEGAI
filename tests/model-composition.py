#!/usr/bin/env python3
"""Check the maintained model-neutral routing reference."""
from pathlib import Path

policy = (Path(__file__).resolve().parents[1] / "skills/model-composition/routing.md").read_text()
for clause in (
    "System/developer instructions and repository restrictions win",
    "Use direct parent tools for bounded work",
    "Select the user's configured provider/model",
    "MEGAI imposes no GPT-only model scope or provider allowlist",
    "Exactly one writer per checkout",
    "Children never mutate trackers",
    "one fresh independent review for security/data-integrity risks",
    "fresh context",
    "Keep existing tests",
    "one focused correction",
    "do not poll running agents",
    "Check the returned model identity",
    "no full parent transcript",
    "Never expose credentials, personal/production data or private transcripts",
    "Missing counters stay unknown",
    "TPS alone is not task quality",
    "main promotion needs separate explicit user approval",
):
    assert clause.lower() in policy.lower(), clause
print("PASS: model choice remains user-configured; review and delivery rules retained")
