#!/usr/bin/env python3
"""Build the PMTiles manifest from an ``rclone lsjson`` bucket listing.

The bucket is authoritative: objects added to R2 appear in the manifest and
objects removed from R2 disappear from it.  When multiple versioned objects
exist for one cell, the newest timestamp in the filename wins.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from collections import defaultdict
from pathlib import Path


PMTILES_NAME = re.compile(
    r"^(?P<cell>(?:ALP|APP)_E\d+_N\d+)_.*_"
    r"(?P<edition>\d{8}T\d{6}Z)_\d+_z"
    r"(?P<minzoom>\d+)-(?P<maxzoom>\d+)\.pmtiles$"
)


def load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"File non trovato: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON non valido in {path}: {exc}") from exc


def atlas_cell_ids(path: Path) -> set[str]:
    data = load_json(path)
    if not isinstance(data, dict) or not isinstance(data.get("cells"), list):
        raise ValueError(f"Catalogo atlante non valido: {path}")
    return {
        str(cell.get("id"))
        for cell in data["cells"]
        if isinstance(cell, dict) and cell.get("id")
    }


def current_sheets(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    data = load_json(path)
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError(f"Manifest non valido: {path}")
    sheets = data.get("sheets")
    if not isinstance(sheets, dict):
        raise ValueError(f"Manifest senza oggetto 'sheets': {path}")
    return sheets


def build_sheets(objects: object, valid_cells: set[str]) -> tuple[dict, list[str]]:
    if not isinstance(objects, list):
        raise ValueError("L'output di 'rclone lsjson' non e' una lista JSON")

    candidates: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for item in objects:
        if not isinstance(item, dict):
            raise ValueError("Voce non valida nell'elenco R2")
        object_path = item.get("Path")
        size = item.get("Size")
        if not isinstance(object_path, str) or Path(object_path).name != object_path:
            raise ValueError(f"PMTiles R2 non collocato alla radice: {object_path!r}")
        match = PMTILES_NAME.fullmatch(object_path)
        if not match:
            raise ValueError(f"Nome PMTiles R2 non conforme: {object_path}")
        if not isinstance(size, int) or size <= 0:
            raise ValueError(f"Dimensione R2 non valida per {object_path}: {size!r}")

        cell = match.group("cell")
        if cell not in valid_cells:
            raise ValueError(f"Cella {cell} assente dal catalogo dell'atlante")
        minzoom = int(match.group("minzoom"))
        maxzoom = int(match.group("maxzoom"))
        if minzoom > maxzoom:
            raise ValueError(f"Intervallo zoom non valido per {object_path}")

        candidates[cell].append((match.group("edition"), {
            "file": object_path,
            "bytes": size,
            "minzoom": minzoom,
            "maxzoom": maxzoom,
        }))

    sheets: dict[str, dict] = {}
    ignored: list[str] = []
    for cell, versions in sorted(candidates.items()):
        versions.sort(key=lambda value: (value[0], value[1]["file"]))
        sheets[cell] = versions[-1][1]
        ignored.extend(entry["file"] for _, entry in versions[:-1])
    return sheets, ignored


def write_atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.",
        delete=False,
    ) as stream:
        stream.write(payload)
        temporary = Path(stream.name)
    temporary.replace(path)


def print_changes(before: dict, after: dict) -> None:
    before_ids = set(before)
    after_ids = set(after)
    added = sorted(after_ids - before_ids)
    removed = sorted(before_ids - after_ids)
    updated = sorted(
        cell for cell in before_ids & after_ids if before[cell] != after[cell]
    )
    print(f"Manifest sincronizzato: {len(after)} celle")
    if added:
        print("  aggiunte:  " + ", ".join(added))
    if removed:
        print("  rimosse:   " + ", ".join(removed))
    if updated:
        print("  aggiornate: " + ", ".join(updated))
    if not (added or removed or updated):
        print("  nessuna variazione")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sincronizza il manifest PMTiles con gli oggetti presenti su R2."
    )
    parser.add_argument("--atlas", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--public-manifest", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        objects = json.load(sys.stdin)
        before = current_sheets(args.source_manifest)
        sheets, ignored = build_sheets(objects, atlas_cell_ids(args.atlas))
        manifest = {"schema_version": 1, "sheets": sheets}
        write_atomic(args.source_manifest, manifest)
        write_atomic(args.public_manifest, manifest)
        print_changes(before, sheets)
        for name in ignored:
            print(f"  edizione R2 precedente ignorata: {name}", file=sys.stderr)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Errore: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
