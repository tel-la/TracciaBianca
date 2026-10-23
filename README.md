<div align="center">
 
<img width="280" height="280" alt="TracciaBianca_ Avventura Alpina Offline" src="https://github.com/user-attachments/assets/72693f2d-37bd-48da-a9e5-2e44835e20c7" />

</div>

<div align="center">

[![Support my work!](https://img.shields.io/badge/Support%20my%20work%21-87CEFA?style=flat)](https://ko-fi.com/andretella)

</div>


# TracciaBianca

TracciaBianca is a collection of offline raster maps for ski touring in the Italian Alps. Each map is distributed as an individual MBTiles file for compatible mobile and desktop viewers, including QGIS.

> [!CAUTION]
> These maps are planning and orientation aids only. They do not replace official avalanche bulletins, weather forecasts, local restrictions, professional guidance, current observations, suitable equipment, training or personal risk assessment. Mountain conditions can change rapidly, and every field decision remains the user's responsibility.

## Available areas

Use the **[interactive map-sheet index](https://tel-la.github.io/TracciaBianca/)** to identify a map by locality, inspect its status and download a published MBTiles release.

<p align="center">
  <a href="https://tel-la.github.io/TracciaBianca/">
    <img
      src="https://github.com/user-attachments/assets/1fdf3755-7207-4af2-8e2f-3e5c4e9b63e0"
      alt="Explore the interactive TracciaBianca map-sheet index"
      width="100%"
    />
  </a>
</p>

<p align="center">
  <a href="https://tel-la.github.io/TracciaBianca/">
    <strong>Explore the interactive map →</strong>
  </a>
</p>

## Project status

TracciaBianca is a continuous WIP public distribution.

The project is built upon a solid foundation of publicly available online geospatial data and a robust analysis and processing workflow that has been tested across multiple geographic areas. Nevertheless, TracciaBianca remains an exploratory project, and the resulting maps may contain errors, inaccuracies, inconsistencies or other limitations, particularly in certain regions. All maps and information are provided **"as is"**, without any warranty or guarantee of completeness, accuracy, reliability, truthfulness or currency. Users should therefore consider the maps as experimental resources, acknowledge their potential limitations and independently verify any information relevant to their intended use.

### Current release status

The raster MBTiles export workflow, incremental Release conventions and
interactive map-sheet index are operational. Every export that passes the
automatic technical validation is immediately marked **Ready for release**.
There are no repeated per-sheet application, hosting or licensing checks.

The license for TracciaBianca rendered map content is declared once in this
README as CC BY-NC-SA 4.0. Source metadata below is maintained as provenance
documentation and does not block an otherwise technically valid Release.

## What this project provides

TracciaBianca divides its coverage of the Italian Alps into predefined map sheets. GitHub Releases add new or updated map sheets incrementally, and each map is distributed as an offline raster `.mbtiles` file.

The intended workflow consists of:

1. identification of the required area on the map-sheet index;
2. selection of the corresponding map-sheet ID;
3. selection of the newest matching GitHub release;
4. download and optional checksum verification of the MBTiles asset;
5. import into a compatible mobile or desktop offline map viewer, such as Maps Viewer;
6. optional use in QGIS 3.x for desktop inspection and GIS workflows;
7. verification of offline availability before field use.

## Map-sheet selection

The [interactive map-sheet index](https://tel-la.github.io/TracciaBianca/) shows all atlas cores and their current publication status. Select a cell to inspect its identifier, locality, edition, download size and checksum. The download button is enabled only for published releases.

Each map-sheet boundary contains a stable ID, such as `ALP_E143_N084`. The same ID appears in the release description, manifest and asset filename. The interactive atlas resolves that ID to its newest published asset, even when different sheets were added in different incremental releases.

## Requirements

- **Compatible software:** any mobile or desktop application capable of importing and displaying raster MBTiles.
- **QGIS:** a supported QGIS 3.x version for desktop inspection and GIS workflows. QGIS is recommended but not mandatory.
- **Disk space:** sufficient free storage for the selected map and any application-generated cache.
- **PDF reader:** required only for the full-resolution map-sheet index.
- **QGIS plugins:** no plugin is required for the standard raster MBTiles workflow.

User-facing runtime requirements are recorded in this README. Dependencies associated only with future maintenance or build scripts are represented by the standard dependency file for the relevant language, such as `requirements.txt` for Python tooling.

### Compatible viewers

Sorbetto's compatibility notes report successful MBTiles use with the following applications. Compatibility can vary between application and operating-system versions, and reliable field use depends on prior testing with the selected device.

- [Maps Viewer for Android](https://play.google.com/store/apps/details?id=com.ravenfeld.maps) and Maps Viewer for iOS;
- [OruxMaps](https://www.oruxmaps.com/) on Android and iOS;
- [Locus Map](https://www.locusmap.app/);
- [AlpineQuest](https://www.alpinequest.net/);
- [Cartograph](https://www.cartograph.eu/);
- [EasyTrails GPS](https://www.easytrailsgps.com/);
- [GPXSee](https://www.gpxsee.org/) as a cross-platform desktop viewer.

Other software is also compatible when it explicitly supports raster `.mbtiles` files. The listed applications are independent products, and their inclusion does not imply affiliation or endorsement.

## Map downloads

After public distribution begins, maps appear on the GitHub **Releases** page. The map-sheet ID connects the interactive index, release manifest and downloadable asset.

The authoritative filename is generated by the atlas exporter and follows this structure:

```text
<ID>_<area-slug>_<EDITION>_<part>_z<min>-<max>.mbtiles
```

Example:

```text
ALP_E143_N084_brixen-bressanone-alto-adige-dolomiti-occidentali_20261022T180730Z_01_z12-16.mbtiles
```

Every incremental release also includes `SHA256SUMS.txt` and `release-manifest.json`. The release description records the covered areas, editions, file sizes and changes. See [Incremental map releases](RELEASES.md).

## Compatible-viewer workflow

A typical mobile or desktop viewing session consists of transferring the downloaded `.mbtiles` file to the target device, selecting the application's offline-map import function and opening the file. The displayed coverage corresponds to the map-sheet ID in the filename and release description.

Applications use different menu names and storage locations. Their own documentation defines the exact import procedure. Offline testing before departure confirms that the file, map coverage and required zoom levels remain available without a network connection.

Maps Viewer is one compatible option. OruxMaps, Locus Map, AlpineQuest, Cartograph, EasyTrails GPS and GPXSee are additional options reported in Sorbetto's compatibility guidance.

## Checksum verification

Checksum verification provides an integrity check for large downloads. `SHA256SUMS.txt` contains the expected SHA-256 value for every MBTiles asset in that incremental release.

On macOS and Linux, download `SHA256SUMS.txt` from the same release and run:

```sh
shasum -a 256 -c SHA256SUMS.txt
```

On Windows PowerShell, checksum calculation is available through:

```powershell
Get-FileHash .\ALP_E143_N084_brixen-bressanone-alto-adige-dolomiti-occidentali_20261022T180730Z_01_z12-16.mbtiles -Algorithm SHA256
```

A matching value confirms that the downloaded file corresponds to the published checksum. A different value identifies an incomplete, corrupted or otherwise non-matching download.

## QGIS workflow

QGIS 3.x loads raster MBTiles through **Layer > Add Layer > Add Raster Layer**. The downloaded `.mbtiles` file acts as the raster source. After loading, the layer appears in the **Layers** panel and its displayed coverage corresponds to the selected map sheet.

Menu wording can vary slightly between QGIS versions and operating systems. A saved local QGIS project preserves the layer setup for later use.

## Release conventions

Releases are incremental coverage updates. Each one contains only map sheets added for the first time or map sheets with a new edition; unchanged MBTiles are not duplicated. The interactive atlas provides the cumulative view and always points each available cell to its newest asset.

### Release tag

Beta batches use `v0.1.0-beta.1`, `v0.1.0-beta.2` and so on. Stable additions increment the minor version; replacement-only updates increment the patch version.

### Release assets

Each release contains the new or updated MBTiles, `SHA256SUMS.txt` and `release-manifest.json`.

### Release information

Every release description contains:

- the map-sheet ID;
- a human-readable coverage area;
- the publication or update date;
- the MBTiles filename and file size;
- the data sources and source dates;
- the required attribution;
- the applicable data and project licenses;
- relevant coordinate-reference and technical details;
- a summary of changes from the previous release of the same map sheet;
- known limitations.

Updates use a new incremental release and a new edition filename. Older assets remain identifiable and are not silently replaced. The complete policy is documented in [RELEASES.md](RELEASES.md).

## Map-sheet index specification

The planned map-sheet index has two publication formats: a PNG preview for GitHub and a full-resolution PDF for viewing or printing.

The PDF publication specification comprises:

- A3 landscape page orientation;
- clearly differentiated map-sheet boundaries;
- a unique and prominent ID inside every map sheet;
- labels without collisions or overlaps;
- type sizes that remain legible at the intended print scale;
- a concise legend;
- a scale bar and north arrow;
- an update or publication date;
- sufficient visual contrast for screen viewing and printing;
- the repository or Releases page address;
- attribution required by the underlying data sources.

Publication quality requires readable text at 100% PDF zoom and in an A3 print preview. The PNG provides rapid area identification on GitHub, while the PDF provides the detailed reference. Every label, map-sheet ID and boundary remains unambiguous in both outputs.

## Data sources and attribution

This inventory reflects the current TracciaBianca source registry and the source reports generated for the map sheets present in the active atlas. It is independent from Sorbetto's source inventory.

The current exported map sheets use HR-DTM-5m as their continuous elevation base, with available local coverage from Alto Adige, Veneto and Austria layered above it. OpenStreetMap supplies the current topographic and thematic features. The swisstopo and ARSO elevation services are registered for map sheets that extend into Switzerland and Slovenia.

Each published release has its own source manifest because the exact elevation-source combination changes with geographic coverage.

### Elevation models

| Source | Project status | Resolution used by the workflow | License and attribution status |
| --- | --- | --- | --- |
| [HR-DTM-5m national DTM, version 1.2](https://doi.org/10.5281/zenodo.18921767), by Mario Panza, Marina Muto, Mauro Rossi, Massimiliano Alvioli, Giulio Iovine and Ivan Marchesini | Used as the continuous elevation base in every current map sheet | 5 m project grid; the source combines higher-resolution LiDAR DTMs with TINITALY 1.1 at 10 m | `[PENDING: the Zenodo record currently exposes no license value; redistribution and citation terms require confirmation]` |
| [Autonomous Province of Bolzano/Bozen 2.5 m DTM](https://nature-territory.province.bz.it/it/modelli-digitali-di-elevazione) | A local 2.5 m subset is used in current Alto Adige coverage | Approximately 2.5 m | `[PENDING: dataset-level license and vertical datum confirmation]`; provisional source statement: `Autonomous Province of Bolzano/Bozen — Digital Terrain Model` |
| Regione del Veneto DTM files `12_2K_0137.asc`, `12_2K_0165.asc` and `029050.txt` from the [regional geoportal](https://idt2.regione.veneto.it/) | Used where their footprints intersect the current Veneto map sheets | 5 m | `[PENDING: confirmation from each dataset metadata record]`; the portal applies [IODL 2.0](https://www.dati.gov.it/content/italian-open-data-license-v20) to Territorial Planning Directorate data and specifies the attribution `Regione del Veneto – L.R. n. 28/76 – Formazione della Carta Tecnica Regionale` for that category |
| [Austria ALS-DGM elevation grid](https://www.bev.gv.at/Services/Produkte/Digitales-Gelaendehoehenmodell/ALS-Hoehenraster.html) | Used in current map sheets that intersect Austria | 1 m native data, normalized to the project grid | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); attribution: `© Bundesamt für Eich- und Vermessungswesen (BEV)` |
| [swissALTI3D](https://www.swisstopo.admin.ch/en/height-model-swissalti3d), Federal Office of Topography swisstopo | Registered for Swiss coverage; no current atlas sheet relies on it | 2 m COG tiles, normalized to the project grid | [Terms of use for free geodata and geoservices](https://www.swisstopo.admin.ch/en/terms-of-use-free-geodata-and-geoservices); attribution: `© swisstopo` |
| [Slovenia DMR D96/TM ImageServer](https://gis.arso.gov.si/arcgis/rest/services/Slovenija_DMR_D96TM/ImageServer), Slovenian Environment Agency | Registered for Slovenian coverage; no current atlas sheet relies on it | 1 m native service, normalized to the project grid | CC BY 4.0 according to the project's current source registry; attribution: `Slovenian Environment Agency (ARSO)`; `[PENDING: service-specific attribution and vertical datum confirmation]` |

Slope, hillshade and contour layers are generated by TracciaBianca from the elevation-source mosaic used by each map sheet. Their provenance and redistribution conditions follow the contributing elevation datasets.

### Topographic and thematic data

| Source or generated content | Project use | License and attribution status |
| --- | --- | --- |
| [OpenStreetMap](https://www.openstreetmap.org/copyright) local PBF extract | Source for paths, roads, water bodies, waterways, vegetation, settlements, ski infrastructure, points of interest, buildings, huts, minor structures and place names | [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/); visible attribution: `© OpenStreetMap contributors`; `[PENDING: original extract provider and acquisition date confirmation — the current filename indicates 2026-09-12]` |
| TracciaBianca map-sheet grid | Project-generated 60-sheet atlas grid in ETRS89-extended / LAEA Europe (EPSG:3035) | Original project content released under CC BY-NC-SA 4.0 |
| TracciaBianca map-sheet labels and locality index | Project-generated index derived from the atlas grid and OpenStreetMap locality data | Project content released under CC BY-NC-SA 4.0; ODbL attribution remains applicable to OSM-derived data |
| TracciaBianca raster rendering | Combined visual output containing terrain derivatives, OpenStreetMap features and project styling | The release manifest carries the obligations of every contributing dataset; adapted Sorbetto material, where present, remains under CC BY-NC-SA 4.0 |

### Source metadata notes

- Exact HR-DTM-5m v1.2 citation details can be expanded when available.
- Alto Adige, Veneto and ARSO source records can be enriched with dataset-level metadata and vertical-datum details.
- The original provider and acquisition date of the current OpenStreetMap PBF extract can be recorded more precisely.
- Per-release source editions and geographic coverage may be added to the machine-readable manifest.

These metadata items improve provenance documentation but are not per-sheet
publication gates. Released map content uses the license declared below.

## License

The map-generation software is licensed under the GNU General Public License v3.0 or later (GPL-3.0-or-later).
The original cartographic design and rendered map content distributed in the TracciaBianca MBTiles releases are licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0), except for third-party data and materials, which remain subject to their respective licenses and attribution requirements.

Sorbetto is licensed under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). Sorbetto material incorporated into or adapted for TracciaBianca remains attributed, non-commercial and share-alike under that license, with its modifications identified.

Software, documentation, generated maps, adapted Sorbetto material and third-party geographic data can be governed by different licenses. The license applicable to each category is stated separately. A software or documentation license does not grant redistribution rights for source data, rendered tiles or derivative databases.

## Source code and usage guide

The repository also contains the QGIS workflow used to prepare and export the
maps. Installation requirements, local-data setup and the safe working process
are documented in [`HOWTO.md`](HOWTO.md).

## Citation

If you reuse the software or original TracciaBianca material, cite the project
using [`CITATION.cff`](CITATION.cff). A compact BibTeX entry is provided here for
convenience:

```bibtex
@software{tellatin_tracciabianca,
  author = {Tellatin, Andrea},
  title  = {TracciaBianca},
  year   = {2026},
  url    = {https://github.com/tel-la/TracciaBianca}
}
```

## Issue reports

The repository's **Issues** page is the designated public support channel after repository publication. A reproducible issue report contains:

- the map-sheet ID;
- the release tag;
- the exact downloaded filename;
- the viewer or QGIS version and operating system;
- the checksum result;
- a concise description of the problem;
- the reproduction sequence;
- a screenshot when it clarifies the problem.

Public issue reports exclude private routes, personal information, access credentials, private filesystem paths and other sensitive information.

## Contributions

External contributions are accepted after publication of the repository's contribution process. An eligible map contribution has verified redistribution rights, complete attribution, an established map-sheet ID, documented source dates and processing steps, successful testing in compatible software, a verified checksum and a readable index-map update where applicable.

 ## Acknowledgements

TracciaBianca was strongly inspired by [Sorbetto, the ski-touring map for Piedmont and the Aosta Valley](https://tartamillo.wordpress.com/sorbetto/), created by Maki. Sorbetto demonstrated a practical way to combine terrain, slope and topographic information in offline maps for winter mountain use.

Sorbetto is distributed under the [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International license](https://creativecommons.org/licenses/by-nc-sa/4.0/). Sorbetto material incorporated into or adapted for TracciaBianca retains attribution to Maki and Sorbetto, remains non-commercial, carries an indication of the changes and is distributed under the same license.

The attribution associated with adapted Sorbetto material is:

> Based on or adapted from [Sorbetto](https://tartamillo.wordpress.com/sorbetto/) by Maki, licensed under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). Changes were made for TracciaBianca.

Conceptual inspiration alone does not place independently created TracciaBianca content under the Sorbetto license. TracciaBianca is an independent project and does not imply endorsement by Maki.


