# SPDX-License-Identifier: Apache-2.0
import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sync_upstreams.py"
SPEC = importlib.util.spec_from_file_location("sync_upstreams", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)

class SyncUpstreamsTests(unittest.TestCase):
    def test_patch_version_bump(self):
        self.assertEqual("0.3.3", module.bump_patch("0.3.2"))
        self.assertEqual("2.10.1", module.bump_patch("2.10.0"))

    def test_rejects_non_semver(self):
        with self.assertRaises(SystemExit):
            module.bump_patch("v0.3.2")
        with self.assertRaises(SystemExit):
            module.bump_patch("0.3")

    def test_expected_sources_are_scoped_to_owned_repositories(self):
        self.assertEqual({"zairenkai-core", "zairenkai-fas", "zairenkai-tuning"}, set(module.EXPECTED))
        self.assertTrue(all(repo.startswith("ZairenkaiPrjctX/") for repo in module.EXPECTED.values()))

if __name__ == "__main__":
    unittest.main()
