"""Tests for the dependency-free GitHub Pages map builder."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "07_Scripts" / "build_interactive_map.py"
SPEC = importlib.util.spec_from_file_location("build_interactive_map", SCRIPT)
builder = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(builder)

SYNC_SCRIPT = ROOT / "07_Scripts" / "sync_pmtiles_manifest.py"
SYNC_SPEC = importlib.util.spec_from_file_location("sync_pmtiles_manifest", SYNC_SCRIPT)
syncer = importlib.util.module_from_spec(SYNC_SPEC)
assert SYNC_SPEC.loader
SYNC_SPEC.loader.exec_module(syncer)


class InteractiveMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog, cls.cores = builder.build_data(
            ROOT, builder.published_catalog_fallback(ROOT))

    def test_public_catalog_has_all_matching_cells(self):
        self.assertGreater(self.catalog["cell_count"], 0)
        self.assertEqual(len(self.cores["features"]), self.catalog["cell_count"])
        ids = [cell["id"] for cell in self.catalog["cells"]]
        feature_ids = [feature["properties"]["cell_id"] for feature in self.cores["features"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), set(feature_ids))
        self.assertTrue(all(cell["locality"] for cell in self.catalog["cells"]))
        self.assertTrue(all(cell["search_terms"] for cell in self.catalog["cells"]))
        cortina = next(cell for cell in self.catalog["cells"] if cell["id"] == "ALP_E144_N084")
        self.assertIn("Tofane", cortina["search_terms"])

    def test_unpublished_cells_have_no_download_urls(self):
        for cell in self.catalog["cells"]:
            if cell["status"] != "published":
                for package in cell["packages"]:
                    self.assertIsNone(package["release_tag"])
                    self.assertIsNone(package["release_url"])
                    self.assertIsNone(package["download_url"])

    def test_published_count_matches_catalogue(self):
        published = [cell["id"] for cell in self.catalog["cells"]
                     if cell["status"] == "published"]
        self.assertEqual(len(published), self.catalog["published_count"])

    def test_published_package_uses_release_asset_url(self):
        records = builder.package_records({
            "edition": "20261021T103247Z",
            "publication": {
                "release_tag": "v0.1.0-beta.1",
                "release_url": "https://github.com/tel-la/TracciaBianca/releases/tag/v0.1.0-beta.1",
                "assets": {
                    "ALP_E140_N084_z12-16.mbtiles":
                        "https://github.com/tel-la/TracciaBianca/releases/download/"
                        "v0.1.0-beta.1/ALP_E140_N084_z12-16.mbtiles",
                },
            },
            "packages": [{
                "file": "ALP_E140_N084_z12-16.mbtiles",
                "bytes": 123456,
                "sha256": "a" * 64,
            }],
        }, "ALP_E140_N084", True)
        self.assertEqual(records[0]["release_tag"],
                         "v0.1.0-beta.1")
        self.assertEqual(
            records[0]["download_url"],
            "https://github.com/tel-la/TracciaBianca/releases/download/"
            "v0.1.0-beta.1/ALP_E140_N084_z12-16.mbtiles",
        )

    def test_public_geojson_contains_only_web_properties(self):
        for feature in self.cores["features"]:
            self.assertEqual(set(feature["properties"]), {"cell_id", "name", "status"})
            self.assertIn(feature["geometry"]["type"], {"Polygon", "MultiPolygon"})

    def test_builder_writes_only_expected_docs_tree(self):
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary) / "TracciaBianca"
            repository.mkdir()
            (repository / ".git").mkdir()
            (repository / "keep.txt").write_text("preserved", encoding="utf-8")
            docs = builder.copy_site(ROOT, repository, self.catalog, self.cores)
            self.assertEqual((repository / "keep.txt").read_text(encoding="utf-8"), "preserved")
            self.assertTrue((docs / "index.html").is_file())
            self.assertTrue((docs / "vendor" / "leaflet" / "leaflet.js").is_file())
            self.assertTrue((docs / "webmap" / "index.html").is_file())
            self.assertTrue((docs / "webmap" / "pmtiles-manifest.json").is_file())
            self.assertTrue((docs / "webmap" / "vendor" / "maplibre-gl" / "maplibre-gl.js").is_file())
            self.assertTrue((docs / "webmap" / "vendor" / "pmtiles" / "pmtiles.js").is_file())
            self.assertFalse((docs / "webmap" / "data").exists())
            self.assertFalse((docs / "webmap" / "assets").exists())
            self.assertFalse(any((docs / "webmap" / "tiles").glob("*.pmtiles")))
            webmap_html = (docs / "webmap" / "index.html").read_text(encoding="utf-8")
            webmap_app = (docs / "webmap" / "app.js").read_text(encoding="utf-8")
            self.assertIn("../data/atlas.json", webmap_app)
            self.assertIn('map.on("moveend", syncRasterToMap)', webmap_app)
            self.assertIn("rasterCellsForViewport", webmap_app)
            self.assertIn("activeRasters", webmap_app)
            self.assertIn('url.searchParams.set("bounded", "1")', webmap_app)
            self.assertIn("SEARCH_BOUNDS_BUFFER_KM = 20", webmap_app)
            manifest = json.loads(
                (docs / "webmap" / "pmtiles-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["schema_version"], 1)
            self.assertIn("ALP_E131_N078", manifest["sheets"])
            self.assertIn("./vendor/maplibre-gl/maplibre-gl.js", webmap_html)
            generated = json.loads((docs / "data" / "atlas.json").read_text(encoding="utf-8"))
            self.assertEqual(generated["cell_count"], self.catalog["cell_count"])
            self.assertNotIn(str(ROOT), (docs / "data" / "atlas.json").read_text(encoding="utf-8"))

            local_pmtiles = docs / "webmap" / "tiles" / "local-test.pmtiles"
            local_pmtiles.write_bytes(b"local development archive")
            builder.copy_site(ROOT, repository, self.catalog, self.cores)
            self.assertEqual(local_pmtiles.read_bytes(), b"local development archive")

    def test_manifest_sync_uses_r2_and_selects_latest_edition(self):
        objects = [
            {
                "Path": "ALP_E143_N084_brixen_20261020T120000Z_01_z12-16.pmtiles",
                "Size": 100,
            },
            {
                "Path": "ALP_E143_N084_brixen_20261022T180730Z_01_z12-16.pmtiles",
                "Size": 200,
            },
            {
                "Path": "ALP_E144_N084_cortina_20261023T132827Z_01_z12-16.pmtiles",
                "Size": 300,
            },
        ]
        sheets, ignored = syncer.build_sheets(
            objects, {"ALP_E143_N084", "ALP_E144_N084"})
        self.assertEqual(set(sheets), {"ALP_E143_N084", "ALP_E144_N084"})
        self.assertEqual(sheets["ALP_E143_N084"]["bytes"], 200)
        self.assertEqual(sheets["ALP_E143_N084"]["minzoom"], 12)
        self.assertEqual(
            ignored,
            ["ALP_E143_N084_brixen_20261020T120000Z_01_z12-16.pmtiles"],
        )

    def test_manifest_sync_rejects_unknown_cells(self):
        objects = [{
            "Path": "ALP_E999_N999_nowhere_20261020T120000Z_01_z12-16.pmtiles",
            "Size": 100,
        }]
        with self.assertRaisesRegex(ValueError, "assente dal catalogo"):
            syncer.build_sheets(objects, {"ALP_E143_N084"})


if __name__ == "__main__":
    unittest.main()
