#!/usr/bin/env python3
"""Safely publish new or updated TracciaBianca map sheets.

The command updates the existing GitHub Release in place, verifies every
remote asset, rebuilds the public atlas, commits the generated public files
and optionally pushes ``main``.  It is deliberately conservative: existing
MBTiles are never overwritten and every remote mutation has a confirmation
unless ``--yes`` is supplied.

Example::

    python3 07_Scripts/publish_maps.py --dry-run ALP_E134_N083
    python3 07_Scripts/publish_maps.py ALP_E134_N083 ALP_E135_N083
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.parse
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo


DEFAULT_REPOSITORY = "tel-la/TracciaBianca"
DEFAULT_TAG = "v0.1.0-beta.1"
DEFAULT_TITLE = "Offline Alpine Maps — Beta 1"
DEFAULT_BRANCH = "main"
TIMEZONE = ZoneInfo("Europe/Rome")
PUBLIC_SITE = "https://tel-la.github.io/TracciaBianca/"
PUBLIC_ATLAS = PUBLIC_SITE + "data/atlas.json"
ALLOWED_PUBLIC_CHANGES = {
    "06_documentazione/PUBBLICAZIONE_RELEASES_GITHUB.md",
    "docs/data/atlas.json",
    "docs/data/cores.geojson",
}


class PublishError(RuntimeError):
    """A safe, user-facing publication failure."""


def command_text(command: list[str]) -> str:
    return shlex.join(map(str, command))


def capture(command: list[str], cwd: Path) -> str:
    print(f"+ {command_text(command)}")
    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise PublishError(f"Command failed ({result.returncode}): {command_text(command)}\n{detail}")
    return result.stdout


def execute(command: list[str], cwd: Path) -> None:
    print(f"+ {command_text(command)}")
    result = subprocess.run(command, cwd=cwd)
    if result.returncode:
        raise PublishError(f"Command failed ({result.returncode}): {command_text(command)}")


def require_program(name: str) -> None:
    if not shutil.which(name):
        raise PublishError(f"Required program not found: {name}")


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PublishError(f"Missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PublishError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PublishError(f"Expected a JSON object in {path}")
    return value


def save_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_release_helper(root: Path):
    path = root / "07_Scripts" / "prepare_github_release.py"
    spec = importlib.util.spec_from_file_location("tracciabianca_release_helper", path)
    if not spec or not spec.loader:
        raise PublishError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def github_release(root: Path, repository: str, tag: str) -> dict:
    encoded = urllib.parse.quote(tag, safe="")
    output = capture(["gh", "api", f"repos/{repository}/releases/tags/{encoded}"], root)
    try:
        value = json.loads(output)
    except json.JSONDecodeError as exc:
        raise PublishError(f"GitHub returned invalid Release JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise PublishError("GitHub returned an unexpected Release response")
    return value


def remote_assets(release: dict) -> dict[str, dict]:
    assets = release.get("assets")
    if not isinstance(assets, list):
        raise PublishError("The GitHub Release has no valid asset list")
    result: dict[str, dict] = {}
    for asset in assets:
        name = asset.get("name") if isinstance(asset, dict) else None
        if not isinstance(name, str) or not name:
            raise PublishError("The GitHub Release contains an unnamed asset")
        if name in result:
            raise PublishError(f"Duplicate remote asset name: {name}")
        result[name] = asset
    return result


def verify_asset(asset: dict, package: dict, require_digest: bool = True) -> None:
    name = package["name"]
    if asset.get("state") != "uploaded":
        raise PublishError(f"Remote asset is not fully uploaded: {name}")
    if asset.get("size") != package["bytes"]:
        raise PublishError(
            f"Remote size mismatch for {name}: {asset.get('size')} != {package['bytes']}"
        )
    expected_digest = "sha256:" + package["sha256"]
    remote_digest = asset.get("digest")
    if require_digest and remote_digest != expected_digest:
        raise PublishError(
            f"Remote SHA-256 mismatch for {name}: {remote_digest!r} != {expected_digest!r}"
        )
    if remote_digest not in (None, expected_digest):
        raise PublishError(f"Remote SHA-256 mismatch for {name}")


def record_cell(record: dict) -> dict:
    return {
        "id": record["id"],
        "display_name": record["display_name"],
        "edition": record["edition"],
        "zoom": record["zoom"],
        "packages": [
            {key: package[key] for key in ("name", "bytes", "sha256")}
            for package in record["packages"]
        ],
    }


def comparable_cell(cell: dict) -> dict:
    return {
        "id": cell.get("id"),
        "display_name": cell.get("display_name"),
        "edition": cell.get("edition"),
        "zoom": cell.get("zoom"),
        "packages": [
            {key: package.get(key) for key in ("name", "bytes", "sha256")}
            for package in cell.get("packages", [])
        ],
    }


def human_bytes(value: int) -> str:
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.1f} {unit}" if unit != "B" else f"{int(amount)} B"
        amount /= 1024
    raise AssertionError("unreachable")


def markdown(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def release_notes(
    tag: str,
    title: str,
    cells: list[dict],
    changed_ids: set[str],
    old_ids: set[str],
    superseded: list[str],
) -> str:
    now = dt.datetime.now(TIMEZONE)
    lines = [
        f"# {title}",
        "",
        f"> **Updated {now.strftime('%-d %B %Y')}.** This beta release was refreshed in place "
        f"and now contains {len(cells)} map sheets.",
        "",
        "## Current contents",
        "",
        f"This release contains {len(cells)} offline map sheets. Existing unchanged MBTiles were "
        "retained without being re-uploaded.",
        "",
        "| Map sheet | Area | Edition | Zoom | Size | Status |",
        "|---|---|---:|---:|---:|---|",
    ]
    for cell in cells:
        size = sum(package["bytes"] for package in cell["packages"])
        if cell["id"] in changed_ids:
            status = "Updated in latest publication" if cell["id"] in old_ids else "Added in latest publication"
        else:
            status = "Available"
        lines.append(
            f"| `{cell['id']}` | {markdown(cell['display_name'])} | `{cell['edition']}` | "
            f"z{cell['zoom'][0]}–{cell['zoom'][1]} | {human_bytes(size)} | {status} |"
        )
    lines += ["", "## Latest publication", ""]
    for cell in cells:
        if cell["id"] not in changed_ids:
            continue
        action = "Updated" if cell["id"] in old_ids else "Added"
        lines.append(f"- {action}: `{cell['id']}` — {cell['display_name']} (`{cell['edition']}`).")
    if superseded:
        lines += ["", "Superseded assets removed after verification:", ""]
        lines += [f"- `{name}`" for name in sorted(superseded)]
    lines += [
        "",
        "## Download and integrity",
        "",
        "Download the required MBTiles asset and verify it against `SHA256SUMS.txt`. "
        "`release-manifest.json` records the current edition, byte count and SHA-256 checksum "
        "for every map asset in this release.",
        "",
        "## Map index",
        "",
        f"Use the [interactive TracciaBianca atlas]({PUBLIC_SITE}) to select a sheet and download "
        "its current edition.",
        "",
        f"Release tag: `{tag}`",
        "",
    ]
    return "\n".join(lines)


def italian_date(value: dt.datetime) -> str:
    months = (
        "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
        "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre",
    )
    return f"{value.day} {months[value.month - 1]} {value.year}"


def update_public_document(
    path: Path,
    tag: str,
    total: int,
    added: list[str],
    updated: list[str],
) -> None:
    text = path.read_text(encoding="utf-8")
    heading = "## Stato attuale"
    start = text.find(heading)
    if start < 0:
        raise PublishError(f"Missing '{heading}' section in {path}")
    next_heading = text.find("\n## ", start + len(heading))
    end = len(text) if next_heading < 0 else next_heading + 1
    sentences = [
        f"La Release `{tag}` è stata aggiornata in-place il "
        f"{italian_date(dt.datetime.now(TIMEZONE))} e contiene {total} celle pubblicate.",
    ]
    if added:
        sentences.append("Nell'ultimo aggiornamento sono state aggiunte " +
                         ", ".join(f"`{cell}`" for cell in added) + ".")
    if updated:
        sentences.append("Sono state aggiornate " +
                         ", ".join(f"`{cell}`" for cell in updated) + ".")
    sentences.append(
        "Gli MBTiles invariati sono stati conservati senza ricaricarli. Manifest, checksum, "
        "note e mappa interattiva sono stati aggiornati e verificati."
    )
    replacement = heading + "\n\n" + "\n".join(sentences) + "\n"
    path.write_text(text[:start] + replacement + text[end:], encoding="utf-8")


def confirm(message: str, assume_yes: bool) -> None:
    if assume_yes:
        print(f"AUTO-CONFIRMED: {message}")
        return
    answer = input(f"{message} [y/N] ").strip().lower()
    if answer not in {"y", "yes", "s", "si", "sì"}:
        raise PublishError("Operation cancelled by user")


def git_paths(root: Path) -> set[str]:
    output = capture(["git", "status", "--porcelain", "--untracked-files=all"], root)
    paths: set[str] = set()
    for line in output.splitlines():
        if not line:
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.add(path)
    return paths


def verify_git_preflight(
    root: Path,
    repository: str,
    branch: str,
    require_clean: bool = True,
) -> None:
    top = Path(capture(["git", "rev-parse", "--show-toplevel"], root).strip()).resolve()
    if top != root:
        raise PublishError(f"Run from repository {root}; Git root is {top}")
    current_branch = capture(["git", "branch", "--show-current"], root).strip()
    if current_branch != branch:
        raise PublishError(f"Expected branch {branch!r}, found {current_branch!r}")
    dirty = git_paths(root)
    if dirty and require_clean:
        raise PublishError("Working tree is not clean:\n- " + "\n- ".join(sorted(dirty)))
    if dirty:
        print("DRY RUN warning: working tree is not clean:\n- " + "\n- ".join(sorted(dirty)))
    remote_url = capture(["git", "remote", "get-url", "origin"], root).strip()
    if repository not in remote_url and repository.replace("/", ":") not in remote_url:
        raise PublishError(f"origin does not point to {repository}: {remote_url}")
    local_head = capture(["git", "rev-parse", "HEAD"], root).strip()
    remote_line = capture(["git", "ls-remote", "origin", f"refs/heads/{branch}"], root).strip()
    remote_head = remote_line.split()[0] if remote_line else ""
    if not remote_head:
        raise PublishError(f"Remote branch origin/{branch} was not found")
    if local_head != remote_head:
        raise PublishError(
            f"Local HEAD and origin/{branch} differ:\nlocal  {local_head}\nremote {remote_head}"
        )


def validate_release(release: dict, tag: str) -> None:
    if release.get("tag_name") != tag:
        raise PublishError(f"Unexpected Release tag: {release.get('tag_name')!r}")
    if release.get("draft") or not release.get("published_at"):
        raise PublishError(f"Release {tag} is not public")
    if release.get("immutable"):
        raise PublishError(f"Release {tag} is immutable")


def verify_manifest_assets(manifest: dict, assets: dict[str, dict]) -> None:
    cells = manifest.get("cells")
    if not isinstance(cells, list):
        raise PublishError("Current release-manifest.json has no valid cells list")
    for cell in cells:
        for package in cell.get("packages", []):
            name = package.get("name")
            asset = assets.get(name)
            if not asset:
                raise PublishError(f"Manifest references missing remote asset: {name}")
            verify_asset(asset, package)


def verify_public_atlas(
    root: Path,
    manifest: dict,
    changed_cells: list[dict],
    assets: dict[str, dict],
) -> None:
    atlas = load_json(root / "docs" / "data" / "atlas.json")
    public_cells = {cell["id"]: cell for cell in atlas.get("cells", [])}
    expected_count = len(manifest["cells"])
    if atlas.get("published_count") != expected_count:
        raise PublishError(
            f"docs published_count is {atlas.get('published_count')}, expected {expected_count}"
        )
    for expected in changed_cells:
        cell = public_cells.get(expected["id"])
        if not cell or cell.get("status") != "published":
            raise PublishError(f"Public atlas did not mark {expected['id']} as published")
        if cell.get("edition") != expected["edition"]:
            raise PublishError(f"Public atlas edition mismatch for {expected['id']}")
        for package in cell.get("packages", []):
            asset = assets.get(package["file"])
            if not asset:
                raise PublishError(f"Public atlas references missing asset {package['file']}")
            if package.get("download_url") != asset.get("browser_download_url"):
                raise PublishError(f"Public atlas URL mismatch for {package['file']}")


def run_interactive_map_tests(root: Path) -> None:
    """Run stable map tests while the publisher verifies the live count itself.

    The local test module contains one intentionally fixed publication-count
    snapshot.  A publication necessarily changes that count, so this command
    excludes only that snapshot and runs every structural/URL/site-copy test.
    """
    path = root / "07_Scripts" / "tests" / "test_interactive_map.py"
    spec = importlib.util.spec_from_file_location("tracciabianca_interactive_tests", path)
    if not spec or not spec.loader:
        raise PublishError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    loaded = unittest.defaultTestLoader.loadTestsFromTestCase(module.InteractiveMapTests)
    suite = unittest.TestSuite(
        test for test in loaded
        if not test._testMethodName.startswith("test_current_release_contains_")
    )
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful():
        raise PublishError("Interactive map tests failed")


def verify_live_atlas(manifest: dict, changed_cells: list[dict]) -> None:
    url = PUBLIC_ATLAS + "?v=" + str(int(time.time()))
    request = urllib.request.Request(url, headers={"User-Agent": "TracciaBianca-publisher"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            atlas = json.load(response)
    except (OSError, json.JSONDecodeError) as exc:
        raise PublishError(f"Unable to verify live GitHub Pages atlas: {exc}") from exc
    if atlas.get("published_count") != len(manifest["cells"]):
        raise PublishError("Live GitHub Pages published_count is not current")
    cells = {cell.get("id"): cell for cell in atlas.get("cells", [])}
    for expected in changed_cells:
        cell = cells.get(expected["id"])
        if not cell or cell.get("status") != "published" or cell.get("edition") != expected["edition"]:
            raise PublishError(f"Live GitHub Pages is not current for {expected['id']}")


def wait_for_pages(root: Path, repository: str, commit: str, timeout: int) -> None:
    deadline = time.monotonic() + timeout
    last_state = None
    while time.monotonic() < deadline:
        output = capture(["gh", "api", f"repos/{repository}/pages/builds/latest"], root)
        try:
            build = json.loads(output)
        except json.JSONDecodeError as exc:
            raise PublishError(f"Invalid GitHub Pages build response: {exc}") from exc
        state = (build.get("commit"), build.get("status"), (build.get("error") or {}).get("message"))
        if state != last_state:
            print(f"GitHub Pages: commit={state[0]} status={state[1]} error={state[2]}")
            last_state = state
        if state[0] == commit and state[1] == "built" and not state[2]:
            return
        if state[0] == commit and state[1] == "errored":
            raise PublishError(f"GitHub Pages build failed: {state[2]}")
        time.sleep(10)
    raise PublishError(f"Timed out after {timeout}s waiting for GitHub Pages")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cells", nargs="+", help="Map-sheet IDs such as ALP_E134_N083")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--tag", default=DEFAULT_TAG)
    parser.add_argument("--repository", default=DEFAULT_REPOSITORY)
    parser.add_argument("--title", default=DEFAULT_TITLE)
    parser.add_argument("--branch", default=DEFAULT_BRANCH)
    parser.add_argument("--dry-run", action="store_true", help="Validate and prepare without mutations")
    parser.add_argument("--yes", action="store_true", help="Accept all confirmation prompts")
    parser.add_argument("--no-push", action="store_true", help="Create the commit but do not push it")
    parser.add_argument("--keep-staging", action="store_true", help="Preserve temporary release files")
    parser.add_argument("--pages-timeout", type=int, default=300, metavar="SECONDS")
    return parser.parse_args()


def publish(args: argparse.Namespace) -> None:
    root = args.root.expanduser().resolve()
    staging = Path(tempfile.mkdtemp(prefix="tracciabianca-publish-"))
    success = False
    print(f"Staging directory: {staging}")
    try:
        for program in ("git", "gh", "node"):
            require_program(program)
        helper = load_release_helper(root)
        cells = helper.selected_cells(root, args.cells)
        if cells != sorted(set(args.cells)):
            raise PublishError("Cell IDs must be unique and correctly formatted")

        print("\n== Preflight ==")
        capture(["gh", "auth", "status"], root)
        verify_git_preflight(
            root,
            args.repository,
            args.branch,
            require_clean=not args.dry_run,
        )
        release = github_release(root, args.repository, args.tag)
        validate_release(release, args.tag)
        assets = remote_assets(release)

        print("\n== Local package validation and SHA-256 ==")
        records = [helper.inspect_cell(root, cell, True) for cell in cells]
        failures = [(record["id"], item) for record in records for item in record["failures"]]
        if failures:
            details = "\n".join(f"- {cell}: {failure}" for cell, failure in failures)
            raise PublishError("Local validation failed:\n" + details)
        for record in records:
            status = record["catalog"].get("publication_status")
            if status not in {"release_ready", "published"}:
                raise PublishError(f"{record['id']} has unsupported publication_status: {status!r}")
            print(f"READY {record['id']} {record['edition']} {record['display_name']}")

        current_dir = staging / "current"
        final_dir = staging / "final"
        upload_dir = staging / "upload"
        current_dir.mkdir()
        final_dir.mkdir()
        upload_dir.mkdir()
        execute([
            "gh", "release", "download", args.tag,
            "--repo", args.repository,
            "--pattern", "release-manifest.json",
            "--pattern", "SHA256SUMS.txt",
            "--dir", str(current_dir),
        ], root)
        old_manifest = load_json(current_dir / "release-manifest.json")
        verify_manifest_assets(old_manifest, assets)
        old_cells = {cell["id"]: cell for cell in old_manifest["cells"]}
        proposed_cells = {record["id"]: record_cell(record) for record in records}
        effective_ids = {
            cell_id for cell_id, cell in proposed_cells.items()
            if cell_id not in old_cells or comparable_cell(old_cells[cell_id]) != comparable_cell(cell)
        }
        if not effective_ids:
            print("All selected cells already match the cumulative manifest and remote assets. Nothing to do.")
            success = True
            return
        effective_records = [record for record in records if record["id"] in effective_ids]
        effective_cells = [proposed_cells[record["id"]] for record in effective_records]

        superseded: list[str] = []
        for cell in effective_cells:
            previous = old_cells.get(cell["id"])
            if not previous:
                continue
            current_names = {package["name"] for package in cell["packages"]}
            superseded += [
                package["name"] for package in previous.get("packages", [])
                if package["name"] not in current_names
            ]

        combined = dict(old_cells)
        combined.update({cell["id"]: cell for cell in effective_cells})
        final_cells = [combined[cell_id] for cell_id in sorted(combined)]
        final_manifest = dict(old_manifest)
        final_manifest.update({
            "repository": f"https://github.com/{args.repository}",
            "release_tag": args.tag,
            "title": args.title,
            "prepared_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
            "incremental": True,
            "cells": final_cells,
        })
        manifest_path = final_dir / "release-manifest.json"
        checksums_path = final_dir / "SHA256SUMS.txt"
        notes_path = final_dir / "RELEASE_NOTES.md"
        save_json(manifest_path, final_manifest)
        checksum_lines = [
            f"{package['sha256']}  {package['name']}"
            for cell in final_cells for package in cell["packages"]
        ]
        checksums_path.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
        notes_path.write_text(
            release_notes(
                args.tag, args.title, final_cells, effective_ids, set(old_cells), superseded
            ),
            encoding="utf-8",
        )

        to_upload: list[dict] = []
        already_uploaded: list[dict] = []
        for record in effective_records:
            for package in record["packages"]:
                remote = assets.get(package["name"])
                if remote:
                    verify_asset(remote, package)
                    already_uploaded.append(package)
                else:
                    to_upload.append(package)
        total_upload = sum(package["bytes"] for package in to_upload)
        added = sorted(effective_ids - set(old_cells))
        updated = sorted(effective_ids & set(old_cells))

        print("\n== Publication plan ==")
        print(f"Release: {args.repository} {args.tag}")
        print(f"Added cells: {', '.join(added) or 'none'}")
        print(f"Updated cells: {', '.join(updated) or 'none'}")
        print(f"New uploads: {len(to_upload)} ({human_bytes(total_upload)})")
        print(f"Already uploaded and reusable: {len(already_uploaded)}")
        print(f"Superseded assets to remove at the end: {len(superseded)}")
        print(f"Final cumulative maps: {len(final_cells)}")

        if args.dry_run:
            print("\nDRY RUN complete: no Release, catalogue, docs or Git changes were made.")
            print(f"Prepared files remain in {staging}")
            success = True
            return

        confirm(
            f"Upload {len(to_upload)} MBTiles ({human_bytes(total_upload)}) to {args.tag}?",
            args.yes,
        )
        for package in to_upload:
            link = upload_dir / package["name"]
            link.symlink_to(package["path"].resolve())
        if to_upload:
            execute([
                "gh", "release", "upload", args.tag,
                *[str(upload_dir / package["name"]) for package in to_upload],
                "--repo", args.repository,
            ], root)

        release = github_release(root, args.repository, args.tag)
        assets = remote_assets(release)
        for record in effective_records:
            for package in record["packages"]:
                asset = assets.get(package["name"])
                if not asset:
                    raise PublishError(f"Uploaded asset is missing: {package['name']}")
                verify_asset(asset, package)
        print("All selected remote MBTiles match local byte counts and SHA-256 digests.")

        confirm(
            "Replace cumulative manifest/checksums, update Release notes and remove superseded assets?",
            args.yes,
        )
        execute([
            "gh", "release", "upload", args.tag,
            str(manifest_path), str(checksums_path),
            "--repo", args.repository, "--clobber",
        ], root)
        execute([
            "gh", "release", "edit", args.tag,
            "--repo", args.repository,
            "--title", args.title,
            "--notes-file", str(notes_path),
        ], root)

        release = github_release(root, args.repository, args.tag)
        assets = remote_assets(release)
        for path in (manifest_path, checksums_path):
            expected = {
                "name": path.name,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            asset = assets.get(path.name)
            if not asset:
                raise PublishError(f"Updated metadata asset is missing: {path.name}")
            verify_asset(asset, expected)
        if str(len(final_cells)) not in str(release.get("body", "")):
            raise PublishError("Release notes do not contain the final map count")

        for name in superseded:
            if name not in assets:
                continue
            execute([
                "gh", "release", "delete-asset", args.tag, name,
                "--repo", args.repository, "--yes",
            ], root)

        print("\n== Local catalogues and GitHub Pages data ==")
        execute([
            sys.executable,
            str(root / "07_Scripts" / "prepare_github_release.py"),
            "mark-published",
            "--tag", args.tag,
            "--repository", str(root),
            *sorted(effective_ids),
        ], root)
        update_public_document(
            root / "06_documentazione" / "PUBBLICAZIONE_RELEASES_GITHUB.md",
            args.tag,
            len(final_cells),
            added,
            updated,
        )

        release = github_release(root, args.repository, args.tag)
        assets = remote_assets(release)
        verify_manifest_assets(final_manifest, assets)
        verify_public_atlas(root, final_manifest, effective_cells, assets)

        print("\n== Tests ==")
        run_interactive_map_tests(root)
        execute(["node", "--check", "docs/app.js"], root)
        execute(["git", "diff", "--check"], root)

        changed_paths = git_paths(root)
        unexpected = changed_paths - ALLOWED_PUBLIC_CHANGES
        if unexpected:
            raise PublishError(
                "Unexpected files changed; refusing to commit:\n- " + "\n- ".join(sorted(unexpected))
            )
        if not changed_paths:
            raise PublishError("Release was updated, but no public repository files changed")

        confirm(
            f"Commit {len(changed_paths)} public files" +
            (" without pushing?" if args.no_push else " and push to origin/main?"),
            args.yes,
        )
        execute(["git", "add", *sorted(changed_paths)], root)
        execute(["git", "diff", "--cached", "--check"], root)
        message = f"Publish {len(effective_ids)} additional Beta 1 sheet"
        if len(effective_ids) != 1:
            message += "s"
        execute(["git", "commit", "-m", message], root)
        commit = capture(["git", "rev-parse", "HEAD"], root).strip()
        if args.no_push:
            print(f"Commit created but not pushed: {commit}")
            success = True
            return

        execute(["git", "push", "origin", args.branch], root)
        wait_for_pages(root, args.repository, commit, args.pages_timeout)
        verify_live_atlas(final_manifest, effective_cells)
        remote_head = capture(
            ["git", "ls-remote", "origin", f"refs/heads/{args.branch}"], root
        ).split()[0]
        if remote_head != commit:
            raise PublishError(f"origin/{args.branch} does not point to {commit}")
        if git_paths(root):
            raise PublishError("Working tree is not clean after publication")

        print("\nPublication completed successfully.")
        print(f"Release: https://github.com/{args.repository}/releases/tag/{args.tag}")
        print(f"Atlas: {PUBLIC_SITE}")
        print(f"Commit: https://github.com/{args.repository}/commit/{commit}")
        success = True
    finally:
        if success and not args.keep_staging and not args.dry_run:
            shutil.rmtree(staging, ignore_errors=True)
        else:
            print(f"Staging preserved at: {staging}")


def main() -> int:
    args = parse_arguments()
    try:
        publish(args)
    except (PublishError, ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
