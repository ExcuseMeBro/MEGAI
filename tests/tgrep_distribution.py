"""Integrated profile: same tgrep public contracts on existing Slim fixtures."""
import json
import shutil
import unittest

from slim_distribution import Slim


class Tgrep(Slim):
    def test_tgrep_installer_reuses_pinned_cli_without_network_or_indexing(self):
        self.stub("tgrep", 'test "$*" = "--version" || exit 9\necho "tgrep 1.0.4"\n')
        before = (self.bin / "tgrep").read_bytes()
        self.run_cmd("bash", str(self.megai / "lib/install_tgrep.sh"))
        self.assertEqual((self.bin / "tgrep").read_bytes(), before)
        state = json.loads((self.megai / "state.json").read_text())
        self.assertEqual(state["tools"]["tgrep"]["version"], "tgrep 1.0.4")
        self.assertEqual(state["keep"], {"value": 42})
        calls = (self.home / "calls").read_text() if (self.home / "calls").exists() else ""
        self.assertNotIn("curl", calls)

    def test_tgrep_installer_preserves_unrecognized_cli(self):
        self.stub("tgrep", 'echo "different tgrep"\n')
        before = self.snapshot()
        self.run_cmd("bash", str(self.megai / "lib/install_tgrep.sh"), ok=False)
        self.assertEqual(self.snapshot(), before)

    def test_tgrep_installer_preflights_invalid_state_before_download(self):
        (self.bin / "tgrep").unlink()
        (self.bin / "jq").symlink_to(shutil.which("jq"))
        env = dict(self.env, PATH=f"{self.bin}:/usr/bin:/bin")
        for content in ("{broken", "[]", '{"tools":"custom"}'):
            with self.subTest(state=content):
                (self.megai / "state.json").write_text(content)
                result = self.run_cmd("bash", str(self.megai / "lib/install_tgrep.sh"), ok=False, env=env)
                self.assertIn("state", result.stderr)
                self.assertFalse((self.home / "calls").exists(), "download preceded state preflight")
                self.assertFalse((self.megai / "bin/tgrep").exists())
                self.assertEqual((self.megai / "state.json").read_text(), content)

    def test_tgrep_installer_rejects_corrupt_archive_before_publication(self):
        (self.bin / "tgrep").unlink()
        (self.bin / "jq").symlink_to(shutil.which("jq"))
        self.stub("curl", 'while [ "$#" -gt 0 ]; do if [ "$1" = -o ]; then shift; printf corrupt >"$1"; exit 0; fi; shift; done; exit 8\n')
        env = dict(self.env, PATH=f"{self.bin}:/usr/bin:/bin")
        state = (self.megai / "state.json").read_bytes()
        result = self.run_cmd("bash", str(self.megai / "lib/install_tgrep.sh"), ok=False, env=env)
        self.assertIn("checksum mismatch", result.stderr)
        self.assertFalse((self.megai / "bin/tgrep").exists())
        self.assertEqual(list((self.megai / "bin").glob(".tgrep.*")), [])
        self.assertEqual((self.megai / "state.json").read_bytes(), state)

    def test_tgrep_installer_refuses_symlinked_destination_ancestry(self):
        (self.bin / "tgrep").unlink()
        (self.bin / "jq").symlink_to(shutil.which("jq"))
        outside = self.root / "outside-bin"
        (self.megai / "bin").rename(outside)
        (self.megai / "bin").symlink_to(outside, target_is_directory=True)
        before = self.snapshot()
        env = dict(self.env, PATH=f"{self.bin}:/usr/bin:/bin")
        result = self.run_cmd("bash", str(self.megai / "lib/install_tgrep.sh"), ok=False, env=env)
        self.assertIn("symlinked", result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_tgrep_default_policy_is_lazy_and_keeps_specialists(self):
        self.wire()
        policy = (self.home / ".pi/agent/AGENTS.md").read_text()
        skill = (self.home / ".agents/skills/megai/SKILL.md").read_text()
        self.assertIn("tgrep for literal/regex discovery", policy)
        reference = self.home / ".agents/skills/megai/tgrep.md"
        self.assertEqual(reference.read_bytes(), (self.megai / "pi-skill/tgrep.md").read_bytes())
        for phrase in ("tgrep", "rg", "codedb", "zvec", "freshness", "partial"):
            self.assertIn(phrase, skill)
        calls = (self.home / "calls").read_text() if (self.home / "calls").exists() else ""
        self.assertNotIn("tgrep", calls)


if __name__ == "__main__":
    unittest.main(defaultTest="Tgrep")
