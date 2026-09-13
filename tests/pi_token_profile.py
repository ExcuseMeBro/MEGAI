#!/usr/bin/env python3
"""Offline token-profile installer acceptance in a disposable HOME.

Reuses the Slim fixtures (disposable HOME, stubs, ownership snapshots) but runs
only this class so the inherited distribution suite is not repeated.
"""
from __future__ import annotations

import json
import os
import sys
import unittest

from slim_distribution import ROOT, Slim


class TokenProfile(Slim):
    def profile(self, *args, ok=True, env=None):
        return self.run_cmd(sys.executable, str(self.megai / "lib/pi_token_profile.py"),
                            *args, ok=ok, env=env)

    def wire_pi(self, *args, ok=True):
        return self.run_cmd(sys.executable, str(self.megai / "lib/slim_wiring.py"), "pi", *args, ok=ok)

    def test_preflight_apply_idempotent_verify_remove(self):
        agent = self.home / ".pi/agent"
        before = self.snapshot()
        result = self.profile("--check")
        self.assertIn("preflight ready", result.stdout)
        self.assertEqual(self.snapshot(), before, "preflight must not write")
        self.profile("--apply")
        for skill in ("caveman", "ponytail"):
            for name in ("SKILL.md", "LICENSE.md"):
                self.assertEqual((agent / "skills" / skill / name).read_bytes(),
                                 (ROOT / "pi-skill/token-profile" / skill / name).read_bytes())
        self.assertEqual((agent / "megai-token-profile.json").read_text(),
                         '{\n  "schema": 1,\n  "profile": "max"\n}\n')
        self.assertEqual((agent / "extensions/megai-headroom/index.ts").read_bytes(),
                         (ROOT / "pi-skill/headroom/index.ts").read_bytes())
        self.assertEqual((agent / "AGENTS.md").read_text().count("megai:token-profile:begin"), 1)
        self.assertFalse((self.home / ".agents").exists(), "no shared skill writes")
        after = self.snapshot()
        self.profile("--apply")
        self.assertEqual(self.snapshot(), after, "reapply must be idempotent")
        self.profile("--verify")
        self.profile("--remove")
        self.assertFalse((agent / "skills/caveman/SKILL.md").exists())
        self.assertFalse((agent / "skills/ponytail/SKILL.md").exists())
        self.assertFalse((agent / "megai-token-profile.json").exists())
        self.assertNotIn("megai:token-profile", (agent / "AGENTS.md").read_text())
        self.profile("--remove")
        self.profile("--apply")
        self.assertTrue((agent / "skills/caveman/SKILL.md").is_file())

    def test_preserves_user_config_credentials_and_megai_markers(self):
        agent = self.home / ".pi/agent"
        settings = {"defaultProvider": "keep", "defaultModel": "keep", "defaultThinkingLevel": "high",
                    "packages": ["npm:user"], "skills": ["!/shared/skills/**"], "extensions": ["!custom/**"]}
        self.write(agent / "settings.json", json.dumps(settings))
        self.write(agent / "auth.json", '{"synthetic":"untouched"}')
        self.write(agent / "models.json", '{"test":"unchanged"}')
        self.write(agent / "megai-roles.json", '{"schema":1,"keep":true}')
        self.write(agent / "AGENTS.md",
                   "Local user instruction stays.\n\n"
                   "<!-- megai:slim:begin -->\nkept slim block\n<!-- megai:slim:end -->\n\n"
                   "<!-- megai:subagent-models:begin -->\nkept model block\n<!-- megai:subagent-models:end -->\n")
        self.profile("--apply")
        self.assertEqual(json.loads((agent / "settings.json").read_text()), settings)
        self.assertEqual((agent / "auth.json").read_text(), '{"synthetic":"untouched"}')
        self.assertEqual((agent / "models.json").read_text(), '{"test":"unchanged"}')
        self.assertEqual((agent / "megai-roles.json").read_text(), '{"schema":1,"keep":true}')
        text = (agent / "AGENTS.md").read_text()
        for kept in ("Local user instruction stays.", "kept slim block", "kept model block"):
            self.assertIn(kept, text)
        self.assertLess(text.index("megai:slim:begin"), text.index("megai:token-profile:begin"))
        self.profile("--remove")
        text = (agent / "AGENTS.md").read_text()
        self.assertIn("kept slim block", text)
        self.assertIn("kept model block", text)
        self.assertNotIn("megai:token-profile", text)

    def test_marker_ownership_never_adopts_user_edits(self):
        import hashlib

        agent = self.home / ".pi/agent"
        initial = "Local user instruction stays.\n"
        self.write(agent / "AGENTS.md", initial)
        receipt_path = self.megai / "slim-wiring.json"
        receipt_path.write_text(json.dumps({
            str(agent / "AGENTS.md"): hashlib.sha256(initial.encode()).hexdigest()}))
        self.profile("--apply")
        receipt = json.loads(receipt_path.read_text())
        self.assertIn(str(agent / "AGENTS.md") + "#token-profile", receipt)
        owned = receipt[str(agent / "AGENTS.md")]
        self.assertNotEqual(owned, hashlib.sha256(initial.encode()).hexdigest())
        self.assertIn("Local user instruction stays.", (agent / "AGENTS.md").read_text())
        with open(agent / "AGENTS.md", "a", encoding="utf-8") as stream:
            stream.write("User addition.\n")
        self.profile("--apply")
        self.assertEqual(json.loads(receipt_path.read_text())[str(agent / "AGENTS.md")], owned)
        receipt.pop(str(agent / "AGENTS.md") + "#token-profile")
        receipt_path.write_text(json.dumps(receipt))
        before = self.snapshot()
        self.profile("--remove", ok=False)
        self.assertEqual(self.snapshot(), before)

    def test_malformed_reversed_duplicate_and_custom_markers_refuse(self):
        agent = self.home / ".pi/agent"
        cases = (
            "<!-- megai:token-profile:begin -->\nx\n<!-- megai:token-profile:begin -->\n<!-- megai:token-profile:end -->\n",
            "<!-- megai:token-profile:end -->\nx\n<!-- megai:token-profile:begin -->\n",
            "<!-- megai:token-profile:begin -->\ncustom unowned\n<!-- megai:token-profile:end -->\n",
        )
        for text in cases:
            with self.subTest(text=text):
                self.write(agent / "AGENTS.md", text)
                before = self.snapshot()
                self.profile("--apply", ok=False)
                self.assertEqual(self.snapshot(), before)
                self.assertEqual((agent / "AGENTS.md").read_text(), text)

    def test_unowned_assets_and_symlinks_refuse_without_writes(self):
        agent = self.home / ".pi/agent"
        self.write(agent / "skills/caveman/SKILL.md", "user caveman\n")
        before = self.snapshot()
        self.profile("--apply", ok=False)
        self.assertEqual(self.snapshot(), before)
        (agent / "skills/caveman/SKILL.md").unlink()
        external = self.write(self.root / "external", "external\n")
        (agent / "skills/ponytail").symlink_to(external)
        before = self.snapshot()
        self.profile("--apply", ok=False)
        self.assertEqual(self.snapshot(), before)
        (agent / "skills/ponytail").unlink()
        self.write(agent / "megai-token-profile.json", '{"schema":1,"profile":"lite"}\n')
        before = self.snapshot()
        self.profile("--apply", ok=False)
        self.assertEqual(self.snapshot(), before)

    def test_missing_or_broken_rtk_blocks_apply(self):
        env = dict(self.env, RTK_BIN=str(self.root / "missing-rtk"))
        before = self.snapshot()
        result = self.profile("--check", env=env, ok=False)
        self.assertIn("preflight BLOCKED", result.stdout)
        self.profile("--apply", ok=False, env=env)
        self.assertEqual(self.snapshot(), before)
        broken = self.write(self.root / "not-executable", "#!/bin/sh\nexit 0\n")
        before = self.snapshot()
        self.profile("--apply", ok=False, env=dict(self.env, RTK_BIN=str(broken)))
        self.assertEqual(self.snapshot(), before)

    def test_bootstrap_guidance_present_without_savings_claims(self):
        agent = self.home / ".pi/agent"
        self.profile("--apply")
        text = (agent / "AGENTS.md").read_text()
        for clause in ("RTK_TELEMETRY_DISABLED=1", "Never re-filter", "three-step flow",
                       "missing evidence is BLOCKED", "genuine uncertainty", "normal prose"):
            self.assertIn(clause, text)
        self.assertNotIn("65%", text)
        self.assertNotIn("90%", text)
        self.assertEqual(set(json.loads((agent / "megai-token-profile.json").read_text())),
                         {"schema", "profile"})

    def test_reports_activation_gap_without_clobbering_filters(self):
        agent = self.home / ".pi/agent"
        exclusion = "!" + str(agent / "skills/caveman") + "/**"
        settings = {"skills": [exclusion], "packages": ["npm:user"]}
        self.write(agent / "settings.json", json.dumps(settings))
        result = self.profile("--apply")
        self.assertIn("activation gap", result.stderr)
        self.assertIn("installed-with-gap", result.stdout)
        self.assertIn("caveman", result.stderr)
        self.assertEqual(json.loads((agent / "settings.json").read_text()), settings)

    def test_positive_skill_paths_are_additive(self):
        agent = self.home / ".pi/agent"
        settings = {"skills": ["/opt/shared/skills/caveman/SKILL.md"]}
        self.write(agent / "settings.json", json.dumps(settings))
        result = self.profile("--apply")
        self.assertNotIn("activation gap", result.stderr)
        self.assertIn("installed", result.stdout)
        self.profile("--verify")
        self.assertEqual(json.loads((agent / "settings.json").read_text()), settings)

    def test_verify_blocks_on_core_exclusion(self):
        agent = self.home / ".pi/agent"
        exclusion = "!" + str(agent / "skills/ponytail") + "/**"
        self.write(agent / "settings.json", json.dumps({"skills": [exclusion]}))
        self.profile("--apply")
        before = self.snapshot()
        result = self.profile("--verify", ok=False)
        self.assertIn("BLOCKED", result.stderr)
        self.assertIn("ponytail", result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_malformed_settings_type_is_reported_without_crashing(self):
        agent = self.home / ".pi/agent"
        self.write(agent / "settings.json", "[]")
        result = self.profile("--apply")
        self.assertIn("activation gap", result.stderr)
        self.assertIn("JSON object", result.stderr)
        self.assertTrue((agent / "skills/caveman/SKILL.md").is_file())
        self.assertEqual((agent / "settings.json").read_text(), "[]")
        self.profile("--verify", ok=False)

    def test_owned_profile_survives_pi_wire_source_current(self):
        agent = self.home / ".pi/agent"
        self.wire_pi()
        self.profile("--apply")
        self.wire_pi()
        for skill in ("caveman", "ponytail"):
            for name in ("SKILL.md", "LICENSE.md"):
                self.assertEqual((agent / "skills" / skill / name).read_bytes(),
                                 (ROOT / "pi-skill/token-profile" / skill / name).read_bytes())
        self.assertEqual((agent / "megai-token-profile.json").read_text(),
                         '{\n  "schema": 1,\n  "profile": "max"\n}\n')
        self.assertIn("megai:token-profile:begin", (agent / "AGENTS.md").read_text())
        after = self.snapshot()
        self.wire_pi()
        self.assertEqual(self.snapshot(), after)
        self.profile("--verify")

    def test_pi_wire_still_blocks_unowned_caveman(self):
        agent = self.home / ".pi/agent"
        self.write(agent / "skills/caveman/SKILL.md", "user caveman\n")
        before = self.snapshot()
        self.wire_pi(ok=False)
        self.assertEqual(self.snapshot(), before)

    def test_pi_wire_blocks_companion_file_with_profile(self):
        agent = self.home / ".pi/agent"
        self.wire_pi()
        self.profile("--apply")
        self.write(agent / "skills/caveman/companion.md", "extra\n")
        before = self.snapshot()
        self.wire_pi(ok=False)
        self.assertEqual(self.snapshot(), before)

    def test_pi_wire_refuses_present_invalid_sidecar(self):
        import hashlib

        agent = self.home / ".pi/agent"
        self.wire_pi()
        self.profile("--apply")
        receipt_path = self.megai / "slim-wiring.json"
        sidecar = agent / "megai-token-profile.json"
        receipt = json.loads(receipt_path.read_text())
        receipt.pop(str(sidecar))
        receipt_path.write_text(json.dumps(receipt))
        before = self.snapshot()
        self.wire_pi(ok=False)
        self.assertEqual(self.snapshot(), before)
        receipt[str(sidecar)] = hashlib.sha256(b"{not json\n").hexdigest()
        receipt_path.write_text(json.dumps(receipt))
        sidecar.write_text("{not json\n")
        before = self.snapshot()
        self.wire_pi(ok=False)
        self.assertEqual(self.snapshot(), before)
        receipt[str(sidecar)] = hashlib.sha256(b'{"schema":1,"profile":"max"}\n').hexdigest()
        receipt_path.write_text(json.dumps(receipt))
        sidecar.write_text('{"schema":1,"profile":"lite"}\n')
        before = self.snapshot()
        self.wire_pi(ok=False)
        self.assertEqual(self.snapshot(), before)
        self.assertTrue((agent / "skills/caveman/SKILL.md").is_file())
        # An absent, receipted profile cleans up in the same Plan.
        sidecar.unlink()
        self.wire_pi()
        self.assertFalse((agent / "skills/caveman/SKILL.md").exists())

    def test_slim_wire_remove_keeps_unowned_profile_files(self):
        agent = self.home / ".pi/agent"
        self.wire_pi()
        self.profile("--apply")
        self.write(agent / "skills/caveman/companion.md", "user file\n")
        self.wire_pi("--remove")
        self.assertFalse((agent / "skills/caveman/SKILL.md").exists())
        self.assertFalse((agent / "megai-token-profile.json").exists())
        self.assertEqual((agent / "skills/caveman/companion.md").read_text(), "user file\n")

    def test_check_reports_native_exclusion_semantics(self):
        agent = self.home / ".pi/agent"
        self.profile("--apply")
        self.write(agent / "settings.json", json.dumps({"skills": ["!caveman"]}))
        result = self.profile("--check", ok=False)
        self.assertIn("caveman", result.stdout + result.stderr)
        # `-caveman` is exact-path-only in native Pi and does not disable the core.
        self.write(agent / "settings.json", json.dumps({"skills": ["-caveman"]}))
        self.profile("--check")
        # Plain positive paths are additive and never disable a core.
        self.write(agent / "settings.json", json.dumps({"skills": ["/opt/shared/skills/caveman/SKILL.md"]}))
        self.profile("--check")

    @unittest.skipUnless(os.environ.get("PI_PACKAGE_ROOT"), "native verifier needs PI_PACKAGE_ROOT")
    def test_verify_delegates_to_fresh_native_activation(self):
        agent = self.home / ".pi/agent"
        self.profile("--apply")
        env = dict(self.env, PATH=os.environ["PATH"])
        self.profile("--verify", env=env)
        cases = (
            ("relative parent-name exclusion", {"skills": ["!caveman"]}),
            ("relative ponytail exclusion", {"skills": ["!ponytail"]}),
            ("wildcard caveman exclusion", {"skills": ["!" + str(agent / "skills/caveman") + "/**"]}),
            ("exact force-exclude of the ponytail dir", {"skills": ["-" + str(agent / "skills/ponytail")]}),
            ("excluded Headroom extension",
             {"extensions": ["-" + str(agent / "extensions/megai-headroom/index.ts")]}),
        )
        for label, settings in cases:
            with self.subTest(label=label):
                self.write(agent / "settings.json", json.dumps(settings))
                result = self.profile("--verify", ok=False, env=env)
                self.assertIn("BLOCKED", result.stderr)
        self.write(agent / "settings.json", json.dumps({"skills": ["-caveman"]}))
        self.profile("--verify", env=env)
        self.write(agent / "settings.json", json.dumps({"skills": ["/opt/shared/skills/caveman/SKILL.md"]}))
        self.profile("--verify", env=env)

    def test_missing_sidecar_cleans_owned_profile(self):
        agent = self.home / ".pi/agent"
        self.wire_pi()
        self.profile("--apply")
        settings = {"defaultModel": "keep", "packages": ["npm:user"],
                    "skills": ["!" + str(self.home / ".agents/skills") + "/**"]}
        self.write(agent / "settings.json", json.dumps(settings))
        self.write(agent / "skills/user-skill/SKILL.md", "---\nname: user-skill\ndescription: user\n---\n")
        (agent / "megai-token-profile.json").unlink()
        self.wire_pi()
        for skill in ("caveman", "ponytail"):
            self.assertFalse((agent / "skills" / skill / "SKILL.md").exists())
            self.assertFalse((agent / "skills" / skill / "LICENSE.md").exists())
        self.assertNotIn("megai:token-profile", (agent / "AGENTS.md").read_text())
        receipt = json.loads((self.megai / "slim-wiring.json").read_text())
        for skill in ("caveman", "ponytail"):
            for name in ("SKILL.md", "LICENSE.md"):
                self.assertNotIn(str(agent / "skills" / skill / name), receipt)
        self.assertNotIn(str(agent / "megai-token-profile.json"), receipt)
        self.assertNotIn(str(agent / "AGENTS.md") + "#token-profile", receipt)
        actual = json.loads((agent / "settings.json").read_text())
        self.assertEqual(actual["defaultModel"], "keep")
        self.assertEqual(actual["packages"], ["npm:user"])
        self.assertTrue((agent / "skills/user-skill/SKILL.md").is_file())
        after = self.snapshot()
        self.wire_pi()
        self.assertEqual(self.snapshot(), after)

    def test_missing_sidecar_blocks_modified_core(self):
        agent = self.home / ".pi/agent"
        self.wire_pi()
        self.profile("--apply")
        (agent / "megai-token-profile.json").unlink()
        with open(agent / "skills/caveman/SKILL.md", "a", encoding="utf-8") as stream:
            stream.write("\nuser edit\n")
        before = self.snapshot()
        self.wire_pi(ok=False)
        self.assertEqual(self.snapshot(), before)
        self.assertIn("user edit", (agent / "skills/caveman/SKILL.md").read_text())

    def test_missing_sidecar_blocks_modified_marker(self):
        agent = self.home / ".pi/agent"
        self.wire_pi()
        self.profile("--apply")
        (agent / "megai-token-profile.json").unlink()
        text = (agent / "AGENTS.md").read_text().replace("MEGAI token profile", "MEGAI token profile edited")
        (agent / "AGENTS.md").write_text(text)
        before = self.snapshot()
        self.wire_pi(ok=False)
        self.assertEqual(self.snapshot(), before)

    def test_stage_profile_is_staging_only(self):
        script = (
            "import sys\n"
            f"sys.path.insert(0, {str(self.megai / 'lib')!r})\n"
            "from pathlib import Path\n"
            "import os\n"
            "from slim_wiring import Plan, SOURCE\n"
            "from pi_token_profile import stage_profile\n"
            "root = Path(os.environ['PI_CODING_AGENT_DIR'])\n"
            "plan = Plan()\n"
            "stage_profile(plan, root, SOURCE, False)\n"
            "assert not (root / 'megai-token-profile.json').exists()\n"
            "assert not (root / 'AGENTS.md').exists()\n"
            "assert not (root / 'skills/caveman/SKILL.md').exists()\n"
            "plan.apply(False)\n"
            "assert (root / 'AGENTS.md').is_file()\n"
            "assert (root / 'megai-token-profile.json').is_file()\n"
            "assert (root / 'skills/caveman/SKILL.md').is_file()\n"
        )
        self.run_cmd(sys.executable, "-c", script)


def load_tests(loader, tests, pattern):
    # Run only this class's cases; the inherited Slim distribution suite stays out of scope.
    suite = unittest.TestSuite()
    for name in loader.getTestCaseNames(TokenProfile):
        if getattr(TokenProfile, name).__qualname__.startswith("Slim."):
            continue
        suite.addTest(TokenProfile(name))
    return suite


if __name__ == "__main__":
    unittest.main()
