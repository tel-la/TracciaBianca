#!/usr/bin/env python3
"""Build the standalone TracciaBianca GitHub Pages map.

This builder deliberately has no QGIS dependency and never modifies the atlas
catalogues it reads.  It writes only the ``docs`` directory of an explicit
checkout of https://github.com/tel-la/TracciaBianca.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import shutil
import tempfile
from pathlib import Path
from urllib.parse import quote


REPOSITORY = "tel-la/TracciaBianca"
REPOSITORY_URL = f"https://github.com/{REPOSITORY}"
GENERATED_FILES = ("index.html", "app.css", "app.js", "assets", "data", "vendor", "webmap")

# Geographic terms that are commonly used for a map sheet but are not its
# reference locality. Keep this small and editorially explicit: the client
# never sends a visitor's query to a third-party geocoding service.
SEARCH_ALIASES = {
    "ALP_E144_N084": ("Tofane", "Tofanes"),
}


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Required input does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def keyed_features(collection: dict, path: Path) -> dict[str, dict]:
    if collection.get("type") != "FeatureCollection" or not isinstance(collection.get("features"), list):
        raise ValueError(f"Expected a GeoJSON FeatureCollection in {path}")
    result: dict[str, dict] = {}
    for feature in collection["features"]:
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise ValueError(f"Malformed feature in {path}")
        properties = feature.get("properties") or {}
        cell_id = properties.get("cell_id")
        if not isinstance(cell_id, str) or not cell_id:
            raise ValueError(f"Feature without cell_id in {path}")
        if cell_id in result:
            raise ValueError(f"Duplicate cell_id {cell_id} in {path}")
        if not feature.get("geometry"):
            raise ValueError(f"Feature {cell_id} has no geometry in {path}")
        result[cell_id] = feature
    return result


def bounds_of_geometry(geometry: dict) -> list[list[float]]:
    points: list[tuple[float, float]] = []

    def visit(value: object) -> None:
        if isinstance(value, list):
            if len(value) >= 2 and all(isinstance(item, (int, float)) for item in value[:2]):
                lon, lat = float(value[0]), float(value[1])
                if math.isfinite(lon) and math.isfinite(lat):
                    points.append((lon, lat))
            else:
                for item in value:
                    visit(item)

    visit(geometry.get("coordinates"))
    if not points:
        raise ValueError("Geometry has no finite coordinates")
    return [[min(p[1] for p in points), min(p[0] for p in points)],
            [max(p[1] for p in points), max(p[0] for p in points)]]


def union_bounds(bounds: list[list[list[float]]]) -> list[list[float]]:
    return [[min(item[0][0] for item in bounds), min(item[0][1] for item in bounds)],
            [max(item[1][0] for item in bounds), max(item[1][1] for item in bounds)]]


def rounded_geometry(geometry: dict) -> dict:
    def rounded(value: object) -> object:
        if isinstance(value, list):
            return [rounded(item) for item in value]
        if isinstance(value, float):
            return round(value, 6)
        return value

    return {"type": geometry["type"], "coordinates": rounded(geometry["coordinates"])}


def validate_package(package: dict, cell_id: str) -> dict:
    missing = [key for key in ("file", "bytes", "sha256") if key not in package]
    if missing:
        raise ValueError(f"Package for {cell_id} is missing: {', '.join(missing)}")
    filename = Path(str(package["file"])).name
    byte_count = package["bytes"]
    digest = str(package["sha256"]).lower()
    if not filename or not isinstance(byte_count, int) or byte_count <= 0:
        raise ValueError(f"Invalid package name or size for {cell_id}")
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise ValueError(f"Invalid SHA-256 for {cell_id}: {filename}")
    return {"file": filename, "bytes": byte_count, "sha256": digest}


def package_records(catalog: dict, cell_id: str, published: bool) -> list[dict]:
    packages = catalog.get("packages", [])
    if not isinstance(packages, list):
        raise ValueError(f"packages must be a list for {cell_id}")
    if published and not packages:
        raise ValueError(f"Published cell {cell_id} has no package")
    publication = catalog.get("publication") or {}
    tag = publication.get("release_tag") if published else None
    release_url = publication.get("release_url") if published else None
    asset_urls = publication.get("assets") if published else {}
    if published:
        if not isinstance(tag, str) or not tag:
            raise ValueError(f"Published cell {cell_id} has no Release tag")
        if not isinstance(release_url, str) or not release_url.startswith(f"{REPOSITORY_URL}/releases/tag/"):
            raise ValueError(f"Published cell {cell_id} has no valid Release URL")
        if not isinstance(asset_urls, dict):
            raise ValueError(f"Published cell {cell_id} has no Release asset map")
    result = []
    for raw in packages:
        item = validate_package(raw, cell_id)
        if published:
            expected = (f"{REPOSITORY_URL}/releases/download/"
                        f"{quote(tag, safe='-_.~')}/{quote(item['file'], safe='-_.~')}")
            download_url = asset_urls.get(item["file"])
            if download_url != expected:
                raise ValueError(f"Published cell {cell_id} has an invalid asset URL for {item['file']}")
            item.update({
                "release_tag": tag,
                "release_url": release_url,
                "download_url": download_url,
            })
        else:
            item.update({"release_tag": None, "release_url": None, "download_url": None})
        result.append(item)
    return result


def elevation_record(catalog: dict, cell_id: str, published: bool) -> dict | None:
    raw = catalog.get("elevation_package")
    if raw is None:
        return None
    derived = dict(catalog)
    derived["packages"] = [raw]
    return package_records(derived, cell_id, published)[0]


def published_catalog_fallback(repository: Path) -> dict[str, dict]:
    """Preserve published cells whose heavy local workspace was archived."""
    path = repository / "docs" / "data" / "atlas.json"
    if not path.is_file():
        return {}
    catalog = load_json(path)
    result = {}
    for cell in catalog.get("cells", []):
        if not isinstance(cell, dict) or cell.get("status") != "published":
            continue
        packages = cell.get("packages") or []
        if not packages:
            continue
        result[cell["id"]] = {
            "edition": cell.get("edition"),
            "settings": {
                "minzoom": (cell.get("zoom") or [None, None])[0],
                "maxzoom": (cell.get("zoom") or [None, None])[1],
            },
            "publication_status": "published",
            "publication": {
                "release_tag": packages[0].get("release_tag"),
                "release_url": packages[0].get("release_url"),
                "assets": {
                    **{package["file"]: package.get("download_url") for package in packages},
                    **({cell["elevation_package"]["file"]:
                        cell["elevation_package"].get("download_url")}
                       if cell.get("elevation_package") else {}),
                },
            },
            "packages": [{key: package[key] for key in ("file", "bytes", "sha256")}
                         for package in packages],
            "elevation_package": ({key: cell["elevation_package"][key]
                                   for key in ("file", "bytes", "sha256")}
                                  if cell.get("elevation_package") else None),
        }
    return result


def build_data(project_root: Path, fallback_catalogs: dict[str, dict] | None = None) -> tuple[dict, dict]:
    atlas_dir = project_root / "08_Atlante"
    cores_path = atlas_dir / "nuclei.geojson"
    places_path = atlas_dir / "localita.geojson"
    analyses_path = atlas_dir / "celle_analisi.geojson"
    catalog_path = atlas_dir / "catalogo.json"

    cores = keyed_features(load_json(cores_path), cores_path)
    places = keyed_features(load_json(places_path), places_path)
    analyses = keyed_features(load_json(analyses_path), analyses_path)
    catalog = load_json(catalog_path)
    raw_cells = catalog.get("cells")
    if not isinstance(raw_cells, list):
        raise ValueError(f"cells must be a list in {catalog_path}")
    catalog_cells = {}
    for cell in raw_cells:
        cell_id = cell.get("id") if isinstance(cell, dict) else None
        if not cell_id:
            raise ValueError(f"Catalog cell without id in {catalog_path}")
        if cell_id in catalog_cells:
            raise ValueError(f"Duplicate cell id {cell_id} in {catalog_path}")
        catalog_cells[cell_id] = cell

    id_sets = {"cores": set(cores), "places": set(places), "analyses": set(analyses),
               "catalog": set(catalog_cells)}
    if not catalog_cells:
        raise ValueError("Atlas catalogue contains no map sheets")
    if len({frozenset(ids) for ids in id_sets.values()}) != 1:
        reference = id_sets["catalog"]
        details = [f"{name}: missing={sorted(reference - ids)}, extra={sorted(ids - reference)}"
                   for name, ids in id_sets.items() if ids != reference]
        raise ValueError("Cell IDs do not match across inputs; " + "; ".join(details))

    public_cells = []
    public_features = []
    core_bounds = []
    published_count = 0
    for cell_id in sorted(catalog_cells):
        source_cell = catalog_cells[cell_id]
        place_properties = places[cell_id].get("properties") or {}
        locality = place_properties.get("name")
        if not isinstance(locality, str) or not locality.strip():
            raise ValueError(f"Missing locality name for {cell_id}")
        locality = locality.strip()
        search_terms = [cell_id, locality, str(source_cell.get("display_name") or "")]
        for key in ("area_name", "sector"):
            value = place_properties.get(key)
            if isinstance(value, str):
                search_terms.append(value)
        search_terms.extend(SEARCH_ALIASES.get(cell_id, ()))
        search_terms = list(dict.fromkeys(term.strip() for term in search_terms
                                          if isinstance(term, str) and term.strip()))

        area_catalog_path = project_root / "##_aree" / cell_id / "output" / "mbtiles" / "catalogo_mbtiles.json"
        area_catalog = (load_json(area_catalog_path) if area_catalog_path.exists()
                        else (fallback_catalogs or {}).get(cell_id, {}))
        published = area_catalog.get("publication_status") == "published"
        if published:
            published_count += 1
            status = "published"
        elif area_catalog:
            status = ("release_ready" if area_catalog.get("technical_validation") == "passed"
                      else "validation_pending")
        else:
            status = str(source_cell.get("status") or "planned")
        packages = package_records(area_catalog, cell_id, published) if area_catalog else []
        elevation = elevation_record(area_catalog, cell_id, published) if area_catalog else None
        settings = area_catalog.get("settings") or {}
        edition = area_catalog.get("edition")
        cell_core_bounds = bounds_of_geometry(cores[cell_id]["geometry"])
        analysis_bounds = bounds_of_geometry(analyses[cell_id]["geometry"])
        core_bounds.append(cell_core_bounds)
        public_cells.append({
            "id": cell_id,
            "locality": locality,
            "display_name": str(source_cell.get("display_name") or locality),
            "search_terms": search_terms,
            "status": status,
            "edition": edition,
            "zoom": [settings.get("minzoom"), settings.get("maxzoom")] if area_catalog else None,
            "bytes": sum(item["bytes"] for item in packages),
            "analysis_bounds": analysis_bounds,
            "packages": packages,
            "elevation_package": elevation,
        })
        public_features.append({
            "type": "Feature",
            "properties": {"cell_id": cell_id, "name": locality, "status": status},
            "geometry": rounded_geometry(cores[cell_id]["geometry"]),
        })

    generated_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    public_catalog = {
        "schema_version": 1,
        "generated_at": generated_at,
        "repository": REPOSITORY_URL,
        "grid_id": catalog.get("grid_id"),
        "cell_count": len(public_cells),
        "published_count": published_count,
        "bounds": union_bounds(core_bounds),
        "cells": public_cells,
    }
    public_cores = {"type": "FeatureCollection", "features": public_features}
    return public_catalog, public_cores


def copy_site(project_root: Path, repository: Path, public_catalog: dict, public_cores: dict) -> Path:
    source = project_root / "07_Scripts" / "interactive_map_src"
    required = (
        "index.html", "app.css", "app.js", "assets/TracciaBianca_LogoCirlce.png",
        "vendor/leaflet/leaflet.css", "vendor/leaflet/leaflet.js",
        "webmap/index.html", "webmap/app.css", "webmap/app.js", "webmap/config.js",
        "webmap/pmtiles-manifest.json",
        "webmap/dev-server.js", "webmap/vendor/maplibre-gl/maplibre-gl.js",
        "webmap/vendor/maplibre-gl/maplibre-gl.css", "webmap/vendor/pmtiles/pmtiles.js",
    )
    for relative in required:
        if not (source / relative).is_file():
            raise ValueError(f"Missing website source asset: {source / relative}")
    if not (repository / ".git").exists():
        raise ValueError(f"Not a Git checkout: {repository}")

    with tempfile.TemporaryDirectory(prefix="tracciabianca-map-") as temporary:
        staged = Path(temporary) / "docs"
        shutil.copytree(source, staged)
        data_dir = staged / "data"
        data_dir.mkdir()
        (data_dir / "atlas.json").write_text(
            json.dumps(public_catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (data_dir / "cores.geojson").write_text(
            json.dumps(public_cores, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        docs = repository / "docs"
        docs.mkdir(exist_ok=True)
        for name in GENERATED_FILES:
            destination = docs / name
            source_item = staged / name
            if name == "webmap" and destination.is_dir():
                # Local PMTiles can be hundreds of MB and are intentionally not
                # part of the generated site. Refresh the viewer while keeping
                # the developer's ignored tile drop directory intact.
                for child in destination.iterdir():
                    if child.name == "tiles":
                        continue
                    if child.is_dir():
                        shutil.rmtree(child)
                    else:
                        child.unlink()
                shutil.copytree(source_item, destination, dirs_exist_ok=True)
                continue
            if destination.is_dir():
                shutil.rmtree(destination)
            elif destination.exists():
                destination.unlink()
            if source_item.is_dir():
                shutil.copytree(source_item, destination)
            else:
                shutil.copy2(source_item, destination)
    return docs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True,
                        help="Local checkout of tel-la/TracciaBianca")
    parser.add_argument("--project-root", type=Path,
                        default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    project_root = args.project_root.expanduser().resolve()
    repository = args.repository.expanduser().resolve()
    public_catalog, public_cores = build_data(
        project_root, published_catalog_fallback(repository))
    docs = copy_site(project_root, repository, public_catalog, public_cores)
    print(json.dumps({
        "docs": str(docs),
        "cells": public_catalog["cell_count"],
        "published": public_catalog["published_count"],
        "generated_at": public_catalog["generated_at"],
    }, indent=2))


if __name__ == "__main__":
    main()
