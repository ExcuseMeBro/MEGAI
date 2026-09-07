#!/usr/bin/env python3
"""GPT/lean profile contract; not an LLM quality or latency benchmark."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELATIVE = Path("skills/model-composition/routing.md")
LUNA = "openai-codex/gpt-5.6-luna"
SOL = "openai-codex/gpt-5.6-sol"
ROUTINE = ("scout", "researcher", "delegate", "worker")
REVIEW = ("reviewer", "debugger", "oracle")
policy = (ROOT / RELATIVE).read_text()
assert len(policy) < 4000
rows = [line for line in policy.splitlines() if line.startswith("| ") and "`" in line]
expected = [
    ["User-facing parent", "openai-codex/gpt-6-astra", "high"],
    ["Bounded discovery/research", LUNA, "medium"],
    ["Scoped implementation, including high-risk work", LUNA, "high"],
    ["Complex debugging, independent review or security advice", SOL, "high"],
]
assert [[c.strip().strip("`") for c in r.strip("|").split("|")] for r in rows] == expected
for clause in (
    "System/developer instructions and repository restrictions win",
    "Use direct parent tools for bounded work",
    "GPT-only: no MiniMax routing or fallback",
    "Use only medium or high thinking",
    "Exactly one writer per checkout",
    "Children never mutate trackers",
    "fresh context",
    "one fresh Sol review for security/data-integrity risks",
    "Keep existing tests",
    "one focused correction",
    "do not poll running agents",
    "Check the returned model identity",
    "no full parent transcript",
    "Never expose credentials, personal/production data or private transcripts",
    "main promotion needs separate explicit user approval",
    "Missing counters stay unknown",
    "TPS alone is not task quality",
):
    assert clause.lower() in policy.lower(), clause
print("GPT-only routing policy PASS (static; no performance claim)")

parser = argparse.ArgumentParser()
parser.add_argument("--live", action="store_true")
parser.add_argument("--settings-backup", type=Path)
args = parser.parse_args()
if args.live:
    home = Path.home()
    agent = home / ".pi/agent"
    installed = home / ".megai" / RELATIVE
    assert installed.read_text() == policy, "Installed policy drift"
    instructions = (agent / "AGENTS.md").read_text()
    assert str(installed) in instructions
    assert "GPT-only for all projects" in instructions
    assert "Use direct tools for bounded tasks" in instructions
    assert "PASEO_AGENT_ID" in instructions
    settings = json.loads((agent / "settings.json").read_text())
    assert settings["defaultProvider"] == "openai-codex"
    assert settings["defaultModel"] == "gpt-6-astra"
    assert settings["defaultThinkingLevel"] == "high"
    sub = settings["subagents"]
    assert sub["defaultModel"] == LUNA
    assert sub["defaultThinking"] == "medium" and sub["maxThinking"] == "high"
    assert not sub.get("agentOverridesByProvider"), "Inspect provider-specific overrides"
    scope = sub["modelScope"]
    assert scope["strict"] is True and scope["enforce"] is True
    assert scope["allow"] == [LUNA, SOL]
    for role in ROUTINE + REVIEW:
        model = SOL if role in REVIEW else LUNA
        assert sub["agentOverrides"][role]["model"] == model, role
        assert sub["agentOverrides"][role]["thinking"] == (
            "medium" if role in ROUTINE[:3] else "high"
        ), role
        assert scope["agents"][role]["allow"] == [model], role
    assert "minimax/" not in json.dumps(sub).lower()
    sources = [p if isinstance(p, str) else p["source"] for p in settings["packages"]]
    assert sources == ["https://github.com/mattpocock/skills", "npm:pi-mcp-adapter"]
    assert settings["packages"][0]["skills"] == ["skills/productivity/writing-for-agents/SKILL.md"]
    assert settings["packages"][1]["skills"] == []
    assert settings["skills"][0] == "!*" and len(settings["skills"]) == 11
    assert all(value.startswith("+") for value in settings["skills"][1:])
    if args.settings_backup:
        before = json.loads(args.settings_backup.read_text())
        # Normalize only this task's requested resource/model changes.
        before["packages"] = settings["packages"]
        before["skills"] = settings["skills"]
        prior = before["subagents"]
        prior["defaultModel"] = LUNA
        prior["modelScope"]["allow"] = [LUNA, SOL]
        for role in ROUTINE:
            prior["agentOverrides"][role]["model"] = LUNA
            prior["modelScope"]["agents"][role]["allow"] = [LUNA]
        assert settings == before, "Unrelated settings changed"
    print("Live GPT-only defaults, lean profile and policy parity PASS; no provider calls")
