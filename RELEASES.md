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
- release notes listing the newly added or updated sheets; an explicitly
  documented in-place beta refresh lists the complete current contents.

Each MBTiles asset remains below GitHub's 2 GiB per-file limit. MBTiles are
stored only as Release assets and never committed to the repository.

## Publishing sequence

1. Complete the automatic MBTiles technical validation.
2. Prepare release notes, checksums and the technical manifest.
3. Upload all assets to a **draft** release.
4. Check asset names, byte counts, notes and manifest.
5. Publish the release.
6. Verify the published assets and update the authoritative local catalogues.
7. Regenerate and commit docs/ so the interactive atlas points to the exact
   GitHub Release asset URLs.

A technically valid local export is shown as Ready for release. It becomes
Available only after its release is public and the remote asset has been
verified.

No per-sheet application, hosting or licensing checklist is required. Released
map content uses the CC BY-NC-SA 4.0 license declared in the repository README.

## Integrity check

On macOS and Linux:

~~~sh
shasum -a 256 -c SHA256SUMS.txt
~~~

On Windows PowerShell, compare each manifest checksum with:

~~~powershell
Get-FileHash .\MAP_FILE.mbtiles -Algorithm SHA256
~~~

As a rule, older releases remain available for reproducibility and a new
edition receives a new filename in a new incremental release. Beta 1 was
exceptionally refreshed in place on 23 October 2026: the release notes identify
the replaced Cortina edition, the manifest and checksum list were regenerated,
and the old asset was removed only after the new asset had been uploaded and
verified. Published assets must never be replaced silently.
