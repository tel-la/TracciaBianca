"""Tests for the incremental GitHub Release helper."""

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "07_Scripts" / "prepare_github_release.py"
SPEC = importlib.util.spec_from_file_location("prepare_github_release", SCRIPT)
release = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(release)


class PrepareGithubReleaseTests(unittest.TestCase):
    def test_discovers_only_current_map_sheet_catalogues(self):
        self.assertEqual(release.discover_cells(ROOT), [
            "ALP_E146_N084",
            "ALP_E147_N084",
        ])

    def test_current_cells_are_ready_or_already_published_after_validation(self):
        for cell_id in release.discover_cells(ROOT):
            record = release.inspect_cell(ROOT, cell_id, False)
            self.assertEqual(record["catalog"]["technical_validation"], "passed")
            self.assertIn(record["catalog"]["publication_status"],
                          ("release_ready", "published"))
            self.assertTrue(record["packages"])
            self.assertEqual(record["failures"], [])

    def test_release_tag_policy(self):
        self.assertRegex("v0.1.0-beta.1", release.TAG_PATTERN)
        self.assertRegex("v0.2.0", release.TAG_PATTERN)
        self.assertNotRegex("tile-ALP_E143_N084", release.TAG_PATTERN)


if __name__ == "__main__":
    unittest.main()
