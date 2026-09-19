"""Integrated profile: the optional jevcache CLI installs alone, or not at all.

These cases pin the offline behaviour the safety story rests on — the pinned digest,
the state preflight, and never failing a profile install. A machine that already has
jevcache on PATH must not change the outcome, so every case but reuse runs with a
restricted PATH. The success path needs the real release and is covered by the live
run recorded in the task evidence.
"""
import json
import shutil
import unittest

from slim_distribution import Slim


class Jevcache(Slim):
    def isolated(self):
        """A PATH with this sandbox's stubs only, so no host jevcache can short-circuit."""
        if not (self.bin / "jq").exists():
            (self.bin / "jq").symlink_to(shutil.which("jq"))
        return dict(self.env, PATH=f"{self.bin}:/usr/bin:/bin")

    def test_reuses_an_existing_cli_without_network_or_state_write(self):
        self.stub("jevcache", 'echo stub\n')
        before = (self.bin / "jevcache").read_bytes()
        state = (self.megai / "state.json").read_bytes()
        result = self.run_cmd("bash", str(self.megai / "lib/install_jevcache.sh"))
        self.assertIn("already installed", result.stdout)
        self.assertEqual((self.bin / "jevcache").read_bytes(), before)
        self.assertEqual((self.megai / "state.json").read_bytes(), state)
        self.assertFalse((self.home / "calls").exists(), "curl ran for an existing CLI")

    def test_rejects_a_download_that_does_not_match_the_pin(self):
        self.stub("curl", 'while [ "$#" -gt 0 ]; do if [ "$1" = -o ]; then shift; printf corrupt >"$1"; exit 0; fi; shift; done; exit 8\n')
        state = (self.megai / "state.json").read_bytes()
        result = self.run_cmd("bash", str(self.megai / "lib/install_jevcache.sh"), env=self.isolated())
        self.assertIn("checksum mismatch", result.stderr)
        self.assertFalse((self.megai / "bin/jevcache").exists())
        self.assertEqual(list((self.megai / "bin").glob(".jevcache.*")), [])
        self.assertEqual((self.megai / "state.json").read_bytes(), state)

    def test_download_failure_never_fails_the_profile_install(self):
        self.stub("curl", 'exit 28\n')
        result = self.run_cmd("bash", str(self.megai / "lib/install_jevcache.sh"), env=self.isolated())
        self.assertIn("download failed", result.stderr)
        self.assertFalse((self.megai / "bin/jevcache").exists())

    def test_preflights_invalid_state_before_download(self):
        for content in ("{broken", "[]", '{"tools":"custom"}'):
            with self.subTest(state=content):
                (self.megai / "state.json").write_text(content)
                result = self.run_cmd("bash", str(self.megai / "lib/install_jevcache.sh"), env=self.isolated())
                self.assertIn("state", result.stderr)
                self.assertFalse((self.home / "calls").exists(), "download preceded state preflight")
                self.assertFalse((self.megai / "bin/jevcache").exists())
                self.assertEqual((self.megai / "state.json").read_text(), content)

    def test_leaves_an_existing_destination_untouched(self):
        (self.megai / "bin").mkdir(parents=True, exist_ok=True)
        (self.megai / "bin/jevcache").write_text("user copy\n")
        self.stub("curl", 'exit 8\n')
        result = self.run_cmd("bash", str(self.megai / "lib/install_jevcache.sh"), env=self.isolated())
        self.assertIn("left untouched", result.stdout)
        self.assertEqual((self.megai / "bin/jevcache").read_text(), "user copy\n")
        self.assertEqual(list((self.megai / "bin").glob(".jevcache.*")), [])
        self.assertEqual(json.loads((self.megai / "state.json").read_text())["tools"], {})


if __name__ == "__main__":
    unittest.main(defaultTest="Jevcache")
