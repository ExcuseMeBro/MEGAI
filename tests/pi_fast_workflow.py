#!/usr/bin/env python3
"""Fast-workflow routing/fallback contracts and retrospective dataset integrity.

Covers current routing and the preserved MEGAI-60 retrospective evidence:

1. The shipped policy text preserves the routing clauses that close the economy
   gap (healthy DeepSeek parent does routine work directly; inherited GPT/Paseo
   parent with the ``economy`` preset routes substantial bounded coding to ONE
   DeepSeek worker; the parent owns scope, validation and guarded review or
   integration; explicit user/task model choices always override; an agent
   team or every role is never required).
2. ``delegation.md`` keeps the verified-launch clause that prefers native
   ``model_change``/``thinking_level_change`` records from the status-provided
   session handle and falls back to the neutral runtime-check prompt only when
   those records are missing, stale, ambiguous, or from a restored agent on a
   different branch; no extra model-based environment prompt is needed once
   the native identity is proven.
3. The frozen sanitized retrospective dataset
   (``docs/audits/pi-task-sample.json``) is the redacted in-repo copy and
   matches the expected shape: three real repository tasks, all-GPT parents,
   arithmetic consistency, honest unknowns (``null`` for child usage,
   provider waits, human interventions, and task58 single-task latency), and
   no fabricated model benchmark.

The tests assert clauses/sections instead of huge literal policy blobs so the
suite survives routine copy edits. The bootstrap baseline and the frozen
sanitized sample are pinned by SHA-256 so the suite is portable and never
hard-codes private filesystem paths or large literal text.
"""
from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADAPTIVE = ROOT / "pi-skill/ADAPTIVE.md"
DELEGATION = ROOT / "pi-skill/delegation.md"
BOOTSTRAP = ROOT / "pi-skill/bootstrap.md"
REPORT = ROOT / "docs/audits/pi-fast-workflow.md"
SAMPLE = ROOT / "docs/audits/pi-task-sample.json"

# Captured once from the private acceptance folder for this refinement; the
# test itself never reads that folder.
FROZEN_SAMPLE_SHA256 = "fa2db80ec37b8e70b24b13f3aabd771be4024871b2a7daccede6e8cc9f78616e"
BOOTSTRAP_BASELINE_SHA256 = "71990f2b0ed685c36000f8f89b8fe66fb18224c381c49caed524efc96cf400b1"

EXPECTED_TASKS = ("provider-progress-58", "megai-59", "megai-60")
EXPECTED_INTERVAL_HASHES = {
    "provider-progress-58": "00f27a1be0d1d79aad7581ab5fd8d73d6889f03631debb9d21ca3c325a7d6d97",
    "megai-59": "75b4fd2c5376e09c4083ae31fd06d90be52ecc13ac155a5c46d557ef5ddfcf4f",
    "megai-60": "b304e36be0273d17f5e4840c08550e5935fc596014ec9f14de5cf93d6efa1516",
}
EXPECTED_FINAL_HASHES = {
    "provider-progress-58": "b60c517cefc2d5cffe31c8db0cc5ffbb7ed94ad2ae31862db9df4c66fa9ef9d5",
    "megai-59": "00967429e3e598d4b7cda8692f40e4dfbc45c016f2eb99a94d1d6cef259b2615",
    "megai-60": "4ce30ee21d1c3eabf3ba1613cfbfb9c83193558b1581b7caeb04b6a065b7c503",
}
EXPECTED_INTERVAL_SECONDS = {
    "provider-progress-58": 2040.109,
    "megai-59": 1306.661,
    "megai-60": 1676.019,
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _section(text: str, heading: str) -> str:
    """Return the body of ``text`` under a ``## heading`` until the next heading."""
    match = re.search(rf"^## {re.escape(heading)}\s*$", text, re.MULTILINE)
    if not match:
        raise AssertionError(f"missing section heading: {heading!r}")
    body = text[match.end():]
    nxt = re.search(r"^## ", body, re.MULTILINE)
    return body if nxt is None else body[:nxt.start()]


_WS = re.compile(r"\s+")


def _normalize(text: str) -> str:
    return _WS.sub(" ", text.lower())


def _clause(text: str, fragment: str) -> None:
    target = _normalize(fragment)
    haystack = _normalize(text)
    if target not in haystack:
        raise AssertionError(f"clause not present: {fragment!r}")


class FastWorkflow(unittest.TestCase):
    def test_adaptive_keeps_economy_routing_clauses_under_char_budget(self):
        text = ADAPTIVE.read_text()
        self.assertLess(len(text), 4500, "ADAPTIVE.md must remain under 4500 chars")
        delegation_section = _section(text, "Delegation and cost")
        for fragment in (
            "Direct parent tools are the default",
            "healthy DeepSeek parent performs its own routine work directly",
            "does not launch a child just to use the same model",
            "inherited GPT/Paseo parent",
            "ONE DeepSeek worker",
            "trivial read-only or single edit may remain direct",
            "parent still owns scope",
            "guarded review or integration",
            "Explicit user/task model choices always override",
            "never silently switch",
            "never require an agent team or every role",
        ):
            with self.subTest(fragment=fragment):
                _clause(delegation_section, fragment)

    def test_adaptive_routine_row_points_at_economy_routing(self):
        text = ADAPTIVE.read_text()
        choose_once = _section(text, "Choose once, escalate on evidence")
        # The Routine row must still say parent implements directly (so the
        # existing regression fragment is preserved) AND must point at the
        # economy routing below for the inherited-parent case.
        _clause(choose_once, "Parent implements directly")
        _clause(choose_once, "Subject to economy routing below")

    def test_adaptive_keeps_guarded_review_and_explicit_overrides_in_reach(self):
        text = ADAPTIVE.read_text()
        choose_once = _section(text, "Choose once, escalate on evidence")
        tight_loop = _section(text, "Tight loop")
        delegation_section = _section(text, "Delegation and cost")
        for fragment in (
            "Routine", "Guarded",
            "source-current PASS", "self-review",
            "missing required reviewer is BLOCKED",
            "explicit user/task model choices always override",
            "GPT is reserved for guarded independent review",
        ):
            with self.subTest(fragment=fragment):
                _clause(choose_once + tight_loop + delegation_section, fragment)

    def test_adaptive_forbids_gpt_parent_direct_only_routing(self):
        text = ADAPTIVE.read_text()
        section = _section(text, "Delegation and cost").lower()
        # The forbidden contradictions are: treating GPT parent as the default
        # implementer under economy, or insisting every GPT delegation must use
        # an agent team / every role.
        for forbidden in (
            "gpt parent implements directly under economy",
            "must launch every role",
            "must always launch a worker for economy",
        ):
            with self.subTest(phrase=forbidden):
                self.assertNotIn(forbidden, section)
        # Required positive clause: substantial GPT-parent work routes to one
        # DeepSeek worker when the preset is economy.
        _clause(section, "substantial bounded implementation to ONE DeepSeek worker")
        _clause(section, "instead of duplicating it in GPT")

    def test_bootstrap_remains_unchanged(self):
        # Bootstrap must remain byte-identical to its pinned baseline; the
        # SHA-256 of the original is the only thing we encode so the suite
        # stays portable and never embeds the full always-loaded text.
        self.assertEqual(_sha256(BOOTSTRAP), BOOTSTRAP_BASELINE_SHA256)

    def test_delegation_prefers_native_records_with_fallback(self):
        text = DELEGATION.read_text()
        verified = _section(text, "Verified launch")
        for fragment in (
            "neutral READY prompt",
            "status-provided session handle",
            "model_change",
            "thinking_level_change",
            "Verify the Paseo harness is `pi` separately from the model provider",
            "same current native session ID",
            "provider-qualified status model",
            "model_change.provider",
            "model_change.modelId",
            "`deepseek/deepseek-flash` means `deepseek` + `deepseek-flash`, not `pi`",
            "thinking_level_change.thinkingLevel",
            "effective thinking reported in status",
            "do not run a second neutral runtime-check model prompt",
            "missing, stale, ambiguous",
            "restored",
            "different branch",
            "fall back to the second neutral runtime-check prompt",
            "PI_PROVIDER",
            "PI_MODEL",
            "PI_REASONING_LEVEL",
            "Paseo labels alone",
            "stop as BLOCKED",
            "on mismatch cancel the child",
            "Re-check restored agents before reuse",
        ):
            with self.subTest(fragment=fragment):
                _clause(verified, fragment)

    def test_report_links_redacted_dataset_and_admits_unknowns(self):
        text = REPORT.read_text()
        for fragment in (
            "docs/audits/pi-task-sample.json",
            "provider-progress-58", "megai-59", "megai-60",
            "openai-codex/gpt-6-astra",
            "task58 single-task latency",
            "child_usage", "provider_wait_seconds", "human_interventions",
            "Every measured parent ran GPT",
            "before/after speedup",
            "no synthetic other-parent benchmark",
            "5.287",
            "8874", "82", "8448",
            "01a0964d-44e7-73f2-b198-5a3f744da6de",
            "READY", "Extra environment model prompts",
            "0",
            "economy",
            "predate the",
            "already-installed",
            "inherited/pinned-session distinction",
            # Honest framing: child_usage null means unknown not zero; the
            # prior delegation policy already allowed either path.
            "not attributed or collected",
            "Sol reviewer",
            "prior delegation policy already allowed either the native metadata path",
            "one parent-chosen redundant prompt",
        ):
            with self.subTest(fragment=fragment):
                _clause(text, fragment)
        # The report must not promise a measured whole-task speedup. It may
        # mention these terms only to negate them; the asserts check the
        # positive claim shapes, not the negation wording.
        for forbidden in (
            "halves latency",
            "guaranteed speedup",
            "MiniMax is faster",
            "X% faster",
            "X% slower",
            "measured end-to-end latency",
            "MiniMax coding quality",
            "proven before/after",
            "established before/after speed regression",
        ):
            with self.subTest(phrase=forbidden):
                self.assertNotIn(forbidden.lower(), text.lower())
        self.assertIn("`01a0964d-44e7-73f2-b198-5a3f744da6de`", text)

    def test_retrospective_dataset_matches_frozen_digest(self):
        self.assertTrue(SAMPLE.is_file(), "pi-task-sample.json must be shipped")
        # Compare against the pinned digest only; this is portable and never
        # touches the private acceptance folder.
        self.assertEqual(_sha256(SAMPLE), FROZEN_SAMPLE_SHA256)

    def test_retrospective_dataset_shape_and_arithmetic(self):
        data = json.loads(SAMPLE.read_text())
        self.assertEqual(data.get("schema"), 1)
        self.assertEqual(data.get("scope"),
                         "Three retrospective repository tasks, not a controlled model/policy benchmark.")
        limitations = data.get("limitations") or []
        for required in (
            "Task58 parent interval includes task57",
            "Parent usage only",
            "No pause subtraction",
            "All measured parents used GPT",
            "Final verification excludes earlier failing attempts",
        ):
            with self.subTest(limitation=required):
                self.assertTrue(any(required in line for line in limitations),
                                f"missing limitation: {required}")
        samples = data.get("samples") or []
        self.assertEqual([s["task"] for s in samples], list(EXPECTED_TASKS))
        self.assertEqual({s["sample_kind"] for s in samples},
                         {"retrospective_real_repository_task"})
        for sample in samples:
            with self.subTest(task=sample["task"]):
                self.assertEqual(sample["parent_assistant_messages"], sample["parent_usage_messages"])
                usage = sample["parent_usage_reported"]
                self.assertEqual(usage["cacheWrite"], 0)
                self.assertEqual(usage["totalTokens"],
                                 usage["input"] + usage["output"] + usage["cacheRead"] + usage["cacheWrite"])
                models = sample["parent_models"]
                self.assertEqual(list(models), ["openai-codex/gpt-6-astra"],
                                 "Only GPT parents are sampled; no MiniMax quality conclusion is supported.")
                self.assertEqual(sum(models.values()), sample["parent_assistant_messages"])
                expected_interval = EXPECTED_INTERVAL_SECONDS[sample["task"]]
                self.assertAlmostEqual(sample["interval_seconds"], expected_interval, places=3)
                self.assertEqual(sample["event_interval_sha256"], EXPECTED_INTERVAL_HASHES[sample["task"]])
                self.assertEqual(sample["final_evidence_sha256"], EXPECTED_FINAL_HASHES[sample["task"]])
                # Final verification equals the sum of accepted-check durations.
                self.assertAlmostEqual(
                    sample["final_verification_seconds"],
                    sum(check["duration_seconds"] for check in sample["checks"]),
                    places=6,
                )
                self.assertEqual(sample["independent_final_verdict"], "PASS")
                # Honest unknowns. null here means "not collected", not zero
                # children; all three samples had reviewers and task60 also
                # had a MiniMax smoke check.
                self.assertIsNone(sample["child_usage"])
                self.assertIsNone(sample["provider_wait_seconds"])
                self.assertIsNone(sample["human_interventions"])
                if sample["task"] == "provider-progress-58":
                    self.assertTrue(sample["contains_other_task_work"])
                    self.assertIsNone(sample["single_task_wall_seconds"])
                else:
                    self.assertFalse(sample["contains_other_task_work"])
                    self.assertAlmostEqual(sample["single_task_wall_seconds"], sample["interval_seconds"], places=3)
                # Each per-check entry has 64-hex receipt and log digests of
                # well-defined shape; their lengths only confirm structure,
                # not authenticity, and they are verified by the JSON parent
                # in production.
                for check in sample["checks"]:
                    with self.subTest(check=check["id"]):
                        self.assertEqual(check["exit_code"], 0)
                        self.assertEqual(len(check["receipt_sha256"]), 64)
                        self.assertEqual(len(check["log_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()