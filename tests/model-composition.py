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
    "Parent diff review and source-current acceptance apply even to security/data-integrity",
    "Do not add a separate reviewer step",
    "fresh context",
    "Keep existing tests",
    "one focused correction",
    "do not poll running agents",
    "verify the returned identity",
    "no full parent transcript",
    "Never expose credentials, personal/production data or private transcripts",
    "Missing counters stay unknown",
    "TPS alone is not task quality",
    "main promotion needs separate explicit user approval",
):
    assert clause.lower() in policy.lower(), clause
assert "independent review" not in policy.lower(), "retired independent review step restored"
print("PASS: model choice remains user-configured; review and delivery rules retained")
