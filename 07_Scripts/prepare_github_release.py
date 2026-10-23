#!/usr/bin/env python3
"""Prepare and register incremental TracciaBianca GitHub Releases.

The script uses only the Python standard library.  It never uploads an asset:
``prepare`` produces release notes, checksums, a manifest and the exact GitHub
CLI commands; ``mark-published`` verifies an already published GitHub Release
before changing the authoritative per-cell catalogues.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shlex
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


REPOSITORY = "tel-la/TracciaBianca"
REPOSITORY_URL = f"https://github.com/{REPOSITORY}"
TAG_PATTERN = re.compile(r"^v\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")
CELL_PATTERN = re.compile(r"^ALP_E\d+_N\d+$")
MAX_ASSET_BYTES = 2 * 1024**3


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def save_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def catalog_path(root: Path, cell_id: str) -> Path:
    if not CELL_PATTERN.fullmatch(cell_id):
        raise ValueError(f"Invalid map-sheet ID: {cell_id}")
    return root / "##_aree" / cell_id / "output" / "mbtiles" / "catalogo_mbtiles.json"


def discover_cells(root: Path) -> list[str]:
    result = []
    for path in (root / "##_aree").glob("ALP_E*_N*/output/mbtiles/catalogo_mbtiles.json"):
        cell_id = path.parents[2].name
        if CELL_PATTERN.fullmatch(cell_id):
            result.append(cell_id)
    return sorted(result)


def selected_cells(root: Path, requested: list[str]) -> list[str]:
    cells = requested or discover_cells(root)
    if not cells:
        raise ValueError("No map-sheet catalogues found")
    if len(cells) != len(set(cells)):
        raise ValueError("Duplicate map-sheet IDs in command")
    return sorted(cells)


def inspect_cell(root: Path, cell_id: str, verify_hash: bool) -> dict:
    path = catalog_path(root, cell_id)
    catalog = load_json(path)
    failures = []
    if catalog.get("technical_validation") != "passed":
        failures.append("technical validation has not passed")
    edition = catalog.get("edition")
    if not isinstance(edition, str) or not re.fullmatch(r"\d{8}T\d{6}Z", edition):
        failures.append("edition is missing or malformed")
    packages = []
    raw_packages = catalog.get("packages")
    if not isinstance(raw_packages, list) or not raw_packages:
        failures.append("no MBTiles packages recorded")
        raw_packages = []
    should_hash = verify_hash and not failures
    for package in raw_packages:
        relative = package.get("file")
        expected_bytes = package.get("bytes")
        expected_sha = str(package.get("sha256") or "").lower()
        if not isinstance(relative, str) or Path(relative).name != relative.split("/")[-1]:
            failures.append("package path is malformed")
            continue
        file_path = path.parent / relative
        if not file_path.is_file():
            failures.append(f"missing package {relative}")
            continue
        actual_bytes = file_path.stat().st_size
        if not isinstance(expected_bytes, int) or expected_bytes != actual_bytes:
            failures.append(f"size mismatch for {file_path.name}")
        if actual_bytes >= MAX_ASSET_BYTES:
            failures.append(f"{file_path.name} reaches GitHub's 2 GiB per-asset limit")
        if not re.fullmatch(r"[0-9a-f]{64}", expected_sha):
            failures.append(f"invalid SHA-256 for {file_path.name}")
        elif should_hash and sha256_file(file_path) != expected_sha:
            failures.append(f"SHA-256 mismatch for {file_path.name}")
        packages.append({
            "name": file_path.name,
            "path": file_path,
            "bytes": actual_bytes,
            "sha256": expected_sha,
        })
    atlas = catalog.get("atlas") or {}
    return {
        "id": cell_id,
        "edition": edition,
        "display_name": str(atlas.get("display_name") or cell_id),
        "zoom": [
            (catalog.get("settings") or {}).get("minzoom"),
            (catalog.get("settings") or {}).get("maxzoom"),
        ],
        "catalog_path": path,
        "catalog": catalog,
        "packages": packages,
        "failures": failures,
    }


def human_bytes(value: int) -> str:
    return f"{value / 1_000_000:.1f} MB" if value < 1_000_000_000 else f"{value / 1_000_000_000:.2f} GB"


def audit_command(args: argparse.Namespace) -> None:
    records = [inspect_cell(args.root, cell, False) for cell in selected_cells(args.root, args.cells)]
    for record in records:
        state = "READY" if not record["failures"] else "BLOCKED"
        print(f"{record['id']}  {state}  {record['edition']}  {record['display_name']}")
        for failure in record["failures"]:
            print(f"  - {failure}")
    if any(record["failures"] for record in records):
        raise SystemExit(2)


def release_notes(tag: str, title: str, records: list[dict]) -> str:
    lines = [
        f"# {title}",
        "",
        f"This incremental release adds {len(records)} new or updated offline map sheet(s). ",
        "Unchanged MBTiles are not repeated: the interactive atlas always points to the newest published edition of each sheet.",
        "",
        "## Added in this release",
        "",
        "| Map sheet | Area | Edition | Zoom | Size |",
        "|---|---|---:|---:|---:|",
    ]
    for record in records:
        size = sum(package["bytes"] for package in record["packages"])
        lines.append(
            f"| `{record['id']}` | {record['display_name']} | `{record['edition']}` | "
            f"z{record['zoom'][0]}–{record['zoom'][1]} | {human_bytes(size)} |"
        )
    lines += [
        "",
        "## Download and integrity",
        "",
        "Download the MBTiles asset for the required map sheet and verify it against `SHA256SUMS.txt`. ",
        "`release-manifest.json` records the exact edition, byte count, checksum and source catalogue for every asset.",
        "",
        "## Map index",
        "",
        "Use the [interactive TracciaBianca atlas](https://tel-la.github.io/TracciaBianca/) to select a sheet. ",
        "Published cells link directly to the matching asset in this or an earlier incremental release.",
        "",
        f"Release tag: `{tag}`",
        "",
    ]
    return "\n".join(lines)


def prepare_command(args: argparse.Namespace) -> None:
    if not TAG_PATTERN.fullmatch(args.tag):
        raise ValueError("Release tag must look like v0.1.0-beta.1 or v1.0.0")
    records = [inspect_cell(args.root, cell, True) for cell in selected_cells(args.root, args.cells)]
    failures = [(record["id"], failure) for record in records for failure in record["failures"]]
    if failures:
        formatted = "\n".join(f"- {cell}: {failure}" for cell, failure in failures)
        raise ValueError("Release preparation blocked:\n" + formatted)
    names = [package["name"] for record in records for package in record["packages"]]
    if len(names) != len(set(names)):
        raise ValueError("Release assets must have unique filenames")
    output = args.output.expanduser().resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"Output directory is not empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    notes_path = output / "RELEASE_NOTES.md"
    checksums_path = output / "SHA256SUMS.txt"
    manifest_path = output / "release-manifest.json"
    notes_path.write_text(release_notes(args.tag, args.title, records), encoding="utf-8")
    checksum_lines = [
        f"{package['sha256']}  {package['name']}"
        for record in records for package in record["packages"]
    ]
    checksums_path.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "repository": REPOSITORY_URL,
        "release_tag": args.tag,
        "title": args.title,
        "prepared_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "incremental": True,
        "cells": [{
            "id": record["id"],
            "display_name": record["display_name"],
            "edition": record["edition"],
            "zoom": record["zoom"],
            "packages": [{key: package[key] for key in ("name", "bytes", "sha256")}
                         for package in record["packages"]],
        } for record in records],
    }
    save_json(manifest_path, manifest)
    assets = [package["path"] for record in records for package in record["packages"]]
    command = [
        "gh", "release", "create", args.tag,
        "--repo", REPOSITORY,
        "--target", "main",
        "--draft",
        "--prerelease",
        "--title", args.title,
        "--notes-file", str(notes_path),
        *map(str, assets), str(checksums_path), str(manifest_path),
    ]
    publish_command = ["gh", "release", "edit", args.tag, "--repo", REPOSITORY, "--draft=false"]
    print("Prepared release bundle:", output)
    print("\nCreate and inspect the draft:\n" + " ".join(map(shlex.quote, command)))
    print("\nPublish after checking the draft:\n" + " ".join(map(shlex.quote, publish_command)))


def github_release(tag: str) -> dict:
    encoded = urllib.parse.quote(tag, safe="")
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPOSITORY}/releases/tags/{encoded}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "TracciaBianca-release-tool"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise ValueError(f"GitHub Release {tag} could not be read: HTTP {exc.code}") from exc


def mark_published_command(args: argparse.Namespace) -> None:
    release = github_release(args.tag)
    if release.get("draft") or not release.get("published_at"):
        raise ValueError(f"Release {args.tag} is still a draft")
    remote_assets = {asset["name"]: asset for asset in release.get("assets", [])}
    records = [inspect_cell(args.root, cell, True) for cell in selected_cells(args.root, args.cells)]
    failures = [(record["id"], failure) for record in records for failure in record["failures"]]
    if failures:
        formatted = "\n".join(f"- {cell}: {failure}" for cell, failure in failures)
        raise ValueError("Publication registration blocked:\n" + formatted)
    for record in records:
        publication_assets = {}
        for package in record["packages"]:
            asset = remote_assets.get(package["name"])
            if not asset:
                raise ValueError(f"Release {args.tag} has no asset {package['name']}")
            if asset.get("size") != package["bytes"]:
                raise ValueError(f"Remote size mismatch for {package['name']}")
            publication_assets[package["name"]] = asset["browser_download_url"]
        catalog = record["catalog"]
        catalog["publication_status"] = "published"
        catalog["publication"] = {
            "release_tag": args.tag,
            "release_url": release["html_url"],
            "published_at": release["published_at"],
            "assets": publication_assets,
        }
        save_json(record["catalog_path"], catalog)
        print(f"Marked {record['id']} as published in {args.tag}")
    if args.repository:
        builder = args.root / "07_Scripts" / "build_interactive_map.py"
        subprocess.run([sys.executable, str(builder), "--repository", str(args.repository)], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    subparsers = parser.add_subparsers(dest="command", required=True)
    audit = subparsers.add_parser("audit", help="List release blockers for current map sheets")
    audit.add_argument("cells", nargs="*")
    prepare = subparsers.add_parser("prepare", help="Prepare a validated incremental release bundle")
    prepare.add_argument("--tag", required=True)
    prepare.add_argument("--title", required=True)
    prepare.add_argument("--output", type=Path, required=True)
    prepare.add_argument("cells", nargs="*")
    published = subparsers.add_parser("mark-published", help="Verify a live release and update catalogues")
    published.add_argument("--tag", required=True)
    published.add_argument("--repository", type=Path,
                           help="Also rebuild docs/ in this tel-la/TracciaBianca checkout")
    published.add_argument("cells", nargs="+")
    args = parser.parse_args()
    args.root = args.root.expanduser().resolve()
    try:
        if args.command == "audit":
            audit_command(args)
        elif args.command == "prepare":
            prepare_command(args)
        else:
            mark_published_command(args)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")


if __name__ == "__main__":
    main()
