# Incremental map releases

TracciaBianca publishes map coverage incrementally. A release contains only
map sheets added for the first time or map sheets with a new edition. Unchanged
MBTiles are not copied into every release.

The [interactive atlas](https://tel-la.github.io/TracciaBianca/) is the
cumulative index: each available cell links to its newest published asset,
regardless of which incremental release contains it.

## Versioning

- beta batches: v0.1.0-beta.1, v0.1.0-beta.2, ...;
- first stable batch: v0.1.0;
- new coverage: increment the minor version, for example v0.2.0;
- corrections or replacement editions only: increment the patch version, for
  example v0.2.1.

Every release title states what changed, for example “Offline Alpine Maps —
Beta 1”, “Coverage Update 0.2” or “Map Update 0.2.1”.

## Contents of a release

Every release contains:

- one or more uniquely named MBTiles assets;
- SHA256SUMS.txt covering every MBTiles asset in that release;
- release-manifest.json with map-sheet ID, area, edition, zoom range, byte
  count and SHA-256;
- release notes listing only the newly added or updated sheets.

Each MBTiles asset remains below GitHub's 2 GiB per-file limit. MBTiles are
stored only as Release assets and never committed to the repository.

## Publishing sequence

1. Validate the MBTiles and complete the required application, hosting and
   licensing checks.
2. Prepare release notes, checksums and the technical manifest.
3. Upload all assets to a **draft** release.
4. Check asset names, byte counts, notes and manifest.
5. Publish the release.
6. Verify the published assets and update the authoritative local catalogues.
7. Regenerate and commit docs/ so the interactive atlas points to the exact
   GitHub Release asset URLs.

A map sheet is shown as Available only after its release is public and the
remote asset has been verified. Local exports and draft assets remain
Validation pending.

## Integrity check

On macOS and Linux:

~~~sh
shasum -a 256 -c SHA256SUMS.txt
~~~

On Windows PowerShell, compare each manifest checksum with:

~~~powershell
Get-FileHash .\MAP_FILE.mbtiles -Algorithm SHA256
~~~

Older releases remain available for reproducibility. A published asset is
never silently replaced; a new edition receives a new filename and is
published in a new incremental release.
