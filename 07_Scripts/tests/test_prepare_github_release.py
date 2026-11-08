"""Tests for the incremental GitHub Release helper."""

import importlib.util
import hashlib
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "07_Scripts" / "prepare_github_release.py"
SPEC = importlib.util.spec_from_file_location("prepare_github_release", SCRIPT)
release = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(release)


class PrepareGithubReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        for cell_id in ("ALP_E134_N083", "APP_E148_N069"):
            folder = self.root / "##_aree" / cell_id / "output" / "mbtiles"
            folder.mkdir(parents=True)
            package = folder / f"{cell_id}.mbtiles"
            package.write_bytes(b"test MBTiles fixture")
            elevation = folder / f"{cell_id}_DEM_HGT1.zip"
            elevation.write_bytes(b"test HGT archive fixture")
            (folder / "catalogo_mbtiles.json").write_text(json.dumps({
                "technical_validation": "passed",
                "publication_status": "release_ready",
                "edition": "20261029T120000Z",
                "packages": [{"file": package.name, "bytes": package.stat().st_size,
                              "sha256": hashlib.sha256(package.read_bytes()).hexdigest()}],
                "elevation_package": {"file": elevation.name, "bytes": elevation.stat().st_size,
                                      "sha256": hashlib.sha256(elevation.read_bytes()).hexdigest()},
                "sources": [{"id": "dem-test", "license": "CC0-1.0"}],
            }), encoding="utf-8")

    def tearDown(self):
        self.temporary.cleanup()

    def test_discovers_alpine_and_apennine_catalogues(self):
        self.assertEqual(release.discover_cells(self.root), [
            "ALP_E134_N083", "APP_E148_N069",
        ])

    def test_both_regions_can_be_inspected_for_release(self):
        for cell_id in release.discover_cells(self.root):
            record = release.inspect_cell(self.root, cell_id, True)
            self.assertEqual(record["catalog"]["technical_validation"], "passed")
            self.assertIn(record["catalog"]["publication_status"],
                          ("release_ready", "published"))
            self.assertTrue(record["packages"])
            self.assertIsNotNone(record["elevation_package"])
            self.assertEqual(len(release.record_assets(record)), 2)
            self.assertEqual(record["failures"], [])

    def test_release_tag_policy(self):
        self.assertRegex("v0.1.0-beta.1", release.TAG_PATTERN)
        self.assertRegex("v0.2.0", release.TAG_PATTERN)
        self.assertNotRegex("tile-ALP_E143_N084", release.TAG_PATTERN)

    def test_unresolved_dem_license_blocks_raw_elevation_release(self):
        cell_id = "ALP_E134_N083"
        path = release.catalog_path(self.root, cell_id)
        catalog = json.loads(path.read_text(encoding="utf-8"))
        catalog["sources"][0]["license"] = "da verificare nei metadati"
        path.write_text(json.dumps(catalog), encoding="utf-8")
        record = release.inspect_cell(self.root, cell_id, True)
        self.assertTrue(any("license unresolved" in item for item in record["failures"]))


if __name__ == "__main__":
    unittest.main()
