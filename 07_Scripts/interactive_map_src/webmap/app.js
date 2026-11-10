(() => {
  "use strict";

  /* -------------------------------------------------------------------------
   * TracciaBianca webmap — MapLibre GL JS + PMTiles viewer shell
   *
   * Mirrors the Leaflet docs/app.js visual language and UX (search, details
   * panel, checksum / download, status labels) but renders cell polygons as a
   * MapLibre GeoJSON overlay and, when the viewport enters a published sheet
   * at its minimum zoom, the converted PMTiles as a raster source via the
   * pmtiles `Protocol` API.
   *
   * Tile source is config-driven (window.TB_CONFIG) and degrades gracefully:
   * when no .pmtiles exists yet (the current 0-byte placeholder phase) the OSM
   * base, the cell overlay, search and the details panel all keep working, and
   * the details panel shows a "tiles not available yet" note instead of tiles.
   * ---------------------------------------------------------------------- */

  const app = document.getElementById("app");
  const mapShell = document.querySelector(".map-shell");
  const loadingState = document.getElementById("loading-state");
  const errorState = document.getElementById("error-state");
  const summary = document.getElementById("atlas-summary");
  const panel = document.getElementById("details-panel");
  const closePanelButton = document.getElementById("close-panel");
  const downloadButton = document.getElementById("download-button");
  const unavailableMessage = document.getElementById("unavailable-message");
  const tilesNote = document.getElementById("tiles-note");
  const checksumBlock = document.getElementById("checksum-block");
  const copyChecksumButton = document.getElementById("copy-checksum");
  const copyFeedback = document.getElementById("copy-feedback");
  const placeSearch = document.getElementById("place-search");
  const placeSearchInput = document.getElementById("place-search-input");
  const searchMessage = document.getElementById("search-message");
  const searchResults = document.getElementById("search-results");
  const NOMINATIM_URL = "https://nominatim.openstreetmap.org/search";
  const SEARCH_BOUNDS_BUFFER_KM = 20;
  const RASTER_TILE_SIZE = 256;
  const RASTER_PREVIEW_TILE_SIZE = 128;
  const MAPLIBRE_CANONICAL_TILE_SIZE = 512;
  const RASTER_STANDARD_ZOOM_OFFSET = Math.log2(
    MAPLIBRE_CANONICAL_TILE_SIZE / RASTER_TILE_SIZE);
  const RASTER_PREVIEW_ZOOM_OFFSET = 1.8;

  const fields = {
    title: document.getElementById("details-title"),
    locality: document.getElementById("details-locality"),
    status: document.getElementById("details-status"),
    edition: document.getElementById("details-edition"),
    zoom: document.getElementById("details-zoom"),
    file: document.getElementById("details-file"),
    size: document.getElementById("details-size"),
    checksum: document.getElementById("details-checksum"),
  };

  const config = window.TB_CONFIG || {};

  function resolveEnvironment() {
    if (config.env === "dev" || config.env === "publish") return config.env;
    const localHosts = new Set(["localhost", "127.0.0.1", "::1", "[::1]"]);
    return localHosts.has(window.location.hostname) ? "dev" : "publish";
  }

  const environment = resolveEnvironment();
  const pmtilesManifests = config.pmtilesManifests || {};
  const pmtilesManifestUrl = typeof pmtilesManifests[environment] === "string"
    ? pmtilesManifests[environment].trim()
    : (typeof config.pmtilesManifest === "string"
      ? config.pmtilesManifest : "./pmtiles-manifest.json");
  const pmtilesBases = config.pmtilesBases || {};
  const pmtilesBase = typeof pmtilesBases[environment] === "string"
    ? pmtilesBases[environment].trim() : "";

  // MapLibre centre is [lng, lat]; the Leaflet app used [lat, lng] = [46.25, 10.8].
  const map = new maplibregl.Map({
    container: "map",
    center: [10.8, 46.25],
    zoom: 7,
    minZoom: 0,
    maxZoom: 19,
    attributionControl: { compact: true },
    style: {
      version: 8,
      sources: {
        osm: {
          type: "raster",
          tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
          tileSize: 256,
          attribution:
            '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors',
        },
      },
      layers: [{ id: "osm-base", type: "raster", source: "osm" }],
    },
  });

  let catalog;
  let coresData;
  let mapLoaded = false;
  let installedCells = false;
  let labelsCreated = false;
  let selectedCell = null;
  let resizeTimer = null;
  let labelRaf = 0;
  let lastGeocoderRequest = 0;
  let searchBounds = null;
  const geocoderCache = new Map();
  const cellsById = new Map();
  const availablePmtiles = new Map();
  const labelEls = new Map();
  let protocolRegistered = false;
  let pmtilesProtocol = null;
  let rasterRequestId = 0;
  let desiredRasters = new Map();
  const activeRasters = new Map();
  const rasterLoads = new Map();
  const rasterFailures = new Set();

  const statusLabels = {
    published: "Available",
    release_ready: "Planned",
    validation_pending: "Validation pending",
    prepared: "In preparation",
    blocked: "Temporarily unavailable",
    planned: "Planned",
  };

  function compactId(cellId) {
    const match = /^([A-Z]{3})_(E\d+)_(N\d+)$/.exec(cellId);
    return match ? `${match[1]}\n${match[2]}\n${match[3]}` : cellId;
  }

  function displayId(cellId) {
    return cellId.replaceAll("_", " ");
  }

  function normalizeSearch(value) {
    return String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "")
      .toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
  }

  function matchingCells(query) {
    const normalized = normalizeSearch(query);
    if (!normalized || !catalog) return [];
    const words = normalized.split(" ");
    return catalog.cells.map((cell) => {
      const terms = (cell.search_terms || [cell.id, cell.locality, cell.display_name])
        .map(normalizeSearch);
      const score = Math.max(...terms.map((term) => {
        if (term === normalized) return 100;
        if (term.startsWith(normalized)) return 80;
        if (term.includes(normalized)) return 60;
        return words.every((word) => term.includes(word)) ? 40 : 0;
      }));
      return { cell, score };
    }).filter((result) => result.score > 0)
      .sort((a, b) => b.score - a.score || a.cell.locality.localeCompare(b.cell.locality));
  }

  function clearSearchFeedback() {
    searchMessage.hidden = true;
    searchMessage.textContent = "";
    searchResults.replaceChildren();
    searchResults.hidden = true;
  }

  function focusCellSearchResult(cell) {
    clearSearchFeedback();
    selectCell(cell.id, false);
  }

  function focusPlaceSearchResult(result) {
    clearSearchFeedback();
    closeDetails(false);
    map.flyTo({ center: [result.lon, result.lat], zoom: 13, duration: 700 });
  }

  // analysis_bounds is [[south, west], [north, east]] in [lat, lon].
  function analysisBBox(cell) {
    const b = cell.analysis_bounds;
    if (!Array.isArray(b) || b.length < 2) return null;
    const [south, west] = b[0];
    const [north, east] = b[1];
    if (![south, west, north, east].every(Number.isFinite)) return null;
    return [[west, south], [east, north]]; // MapLibre [[west,south],[east,north]]
  }

  function centerOf(bbox) {
    const [[west, south], [east, north]] = bbox;
    return [(west + east) / 2, (south + north) / 2]; // [lng, lat]
  }

  function bufferedBoundsForCells(cells, bufferKm = SEARCH_BOUNDS_BUFFER_KM) {
    let west = Infinity;
    let south = Infinity;
    let east = -Infinity;
    let north = -Infinity;
    for (const cell of cells) {
      const bbox = analysisBBox(cell);
      if (!bbox) continue;
      west = Math.min(west, bbox[0][0]);
      south = Math.min(south, bbox[0][1]);
      east = Math.max(east, bbox[1][0]);
      north = Math.max(north, bbox[1][1]);
    }
    if (![west, south, east, north].every(Number.isFinite)) return null;

    const earthRadiusKm = 6371.0088;
    const latitudePadding = (bufferKm / earthRadiusKm) * (180 / Math.PI);
    const outerLatitude = Math.min(89, Math.max(Math.abs(south), Math.abs(north)) + latitudePadding);
    const longitudePadding = latitudePadding / Math.max(Math.cos(outerLatitude * Math.PI / 180), 0.01);
    return {
      west: Math.max(-180, west - longitudePadding),
      south: Math.max(-90, south - latitudePadding),
      east: Math.min(180, east + longitudePadding),
      north: Math.min(90, north + latitudePadding),
    };
  }

  function coordinateInSearchBounds(lat, lon) {
    return Boolean(searchBounds && lat >= searchBounds.south && lat <= searchBounds.north
      && lon >= searchBounds.west && lon <= searchBounds.east);
  }

  function cellForCoordinate(lat, lon) {
    if (!catalog) return null;
    return catalog.cells.find((cell) => {
      const b = cell.analysis_bounds;
      if (!Array.isArray(b) || b.length < 2) return false;
      const [south, west] = b[0];
      const [north, east] = b[1];
      return lat >= south && lat <= north && lon >= west && lon <= east;
    }) || null;
  }

  async function geocodePlace(query) {
    const normalized = normalizeSearch(query);
    if (!normalized || !searchBounds) return [];
    if (geocoderCache.has(normalized)) return geocoderCache.get(normalized);
    const now = Date.now();
    const wait = Math.max(0, 1000 - (now - lastGeocoderRequest));
    if (wait) await new Promise((resolve) => window.setTimeout(resolve, wait));
    lastGeocoderRequest = Date.now();
    const url = new URL(NOMINATIM_URL);
    url.searchParams.set("q", query.trim());
    url.searchParams.set("format", "jsonv2");
    url.searchParams.set("limit", "5");
    url.searchParams.set("addressdetails", "0");
    url.searchParams.set("viewbox",
      `${searchBounds.west},${searchBounds.north},${searchBounds.east},${searchBounds.south}`);
    url.searchParams.set("bounded", "1");
    const response = await fetch(url, {
      headers: { Accept: "application/json" },
      credentials: "omit",
    });
    if (!response.ok) throw new Error(`Geocoder request failed (${response.status})`);
    const places = await response.json();
    const matches = [];
    for (const place of Array.isArray(places) ? places : []) {
      const lat = Number(place.lat);
      const lon = Number(place.lon);
      if (!Number.isFinite(lat) || !Number.isFinite(lon) || !coordinateInSearchBounds(lat, lon)) continue;
      matches.push({
        kind: "place",
        lat,
        lon,
        label: place.display_name || query.trim(),
      });
    }
    const unique = [...new Map(matches.map((match) =>
      [`${match.lat.toFixed(5)},${match.lon.toFixed(5)}`, match])).values()];
    geocoderCache.set(normalized, unique);
    return unique;
  }

  function activateSearchResult(result) {
    if (result.kind === "cell") focusCellSearchResult(result.cell);
    else focusPlaceSearchResult(result);
  }

  function renderSearchResults(results) {
    clearSearchFeedback();
    if (!results.length) {
      searchMessage.textContent = "No places found within the map area.";
      searchMessage.hidden = false;
      return;
    }
    if (results.length === 1) {
      activateSearchResult(results[0]);
      return;
    }
    for (const result of results.slice(0, 5)) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "search-result";
      button.setAttribute("role", "option");
      button.innerHTML = "<strong></strong><span></span>";
      button.querySelector("strong").textContent = result.label;
      button.querySelector("span").textContent = result.kind === "cell"
        ? `${result.cell.id} · ${result.cell.locality}`
        : "OpenStreetMap · within the map area";
      button.addEventListener("click", () => activateSearchResult(result));
      searchResults.append(button);
    }
    searchResults.hidden = false;
  }

  async function showSearchResults(query) {
    clearSearchFeedback();
    if (!normalizeSearch(query)) return;
    // Local, offline-capable catalog match first.
    const local = matchingCells(query);
    if (local.length) {
      renderSearchResults(local.map((r) => ({
        kind: "cell",
        cell: r.cell,
        label: r.cell.display_name,
      })));
      return;
    }
    // Fall back to Nominatim (needs network).
    searchMessage.textContent = "Searching OpenStreetMap…";
    searchMessage.hidden = false;
    try {
      const results = await geocodePlace(query);
      renderSearchResults(results);
    } catch (error) {
      console.error(error);
      searchMessage.textContent = "Search is temporarily unavailable. Try again later.";
      searchMessage.hidden = false;
    }
  }

  function formatBytes(bytes) {
    if (!Number.isFinite(bytes) || bytes <= 0) return "—";
    const units = ["B", "KB", "MB", "GB"];
    const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1000)), units.length - 1);
    const value = bytes / Math.pow(1000, index);
    return `${value.toLocaleString("en", { maximumFractionDigits: index >= 2 ? 1 : 0 })} ${units[index]}`;
  }

  function formatEdition(edition) {
    if (!edition || !/^\d{8}T\d{6}Z$/.test(edition)) return edition || "—";
    const year = edition.slice(0, 4);
    const month = edition.slice(4, 6);
    const day = edition.slice(6, 8);
    return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeZone: "UTC" })
      .format(new Date(`${year}-${month}-${day}T00:00:00Z`));
  }

  function packageFor(cell) {
    return Array.isArray(cell.packages) && cell.packages.length ? cell.packages[0] : null;
  }

  /* ---- PMTiles raster (on demand, graceful) ------------------------------- */

  function setTilesNote(state, text) {
    tilesNote.classList.remove("is-loading", "is-ready", "is-error");
    if (state === "hidden") {
      tilesNote.hidden = true;
      tilesNote.textContent = "";
      return;
    }
    tilesNote.textContent = text;
    if (state === "loading") tilesNote.classList.add("is-loading");
    if (state === "ready") tilesNote.classList.add("is-ready");
    if (state === "error") tilesNote.classList.add("is-error");
    tilesNote.hidden = false;
  }

  function setTilesNoteForCell(cell, state, text) {
    if (selectedCell && selectedCell.id === cell.id) setTilesNote(state, text);
  }

  function derivedPmtilesFileFor(cell) {
    const packages = Array.isArray(cell.packages) ? cell.packages : [];
    const pack = packages.find((item) => item && /\.mbtiles$/i.test(item.file || ""));
    if (pack) return pack.file.replace(/\.mbtiles$/i, ".pmtiles");
    return null;
  }

  // The manifest is the lightweight availability index. An explicit runtime
  // override still wins, followed by the manifest filename and the normal
  // MBTiles → PMTiles derivation.
  function pmtilesFileFor(cell) {
    if (config.sheetFiles && config.sheetFiles[cell.id]) return config.sheetFiles[cell.id];
    const entry = availablePmtiles.get(cell.id);
    if (entry && entry.file) return entry.file;
    return derivedPmtilesFileFor(cell);
  }

  function pmtilesUrlFor(cell) {
    const file = pmtilesFileFor(cell);
    if (!pmtilesBase || !file) return null;
    const baseAbs = new URL(pmtilesBase, document.baseURI).href;
    return new URL(file, baseAbs).href;
  }

  function isRasterHeader(header) {
    const mvtType = window.pmtiles.TileType && window.pmtiles.TileType.Mvt;
    return mvtType === undefined || header.tileType !== mvtType;
  }

  function ensureProtocol() {
    if (protocolRegistered) return true;
    if (typeof window.pmtiles === "undefined" || !window.pmtiles.Protocol) return false;
    try {
      // pmtiles v4 UMD build exposes a Protocol whose `.tile` is a MapLibre
      // protocol handler (the "v3compat" shim adapts the promise handler to
      // MapLibre's callback convention).
      pmtilesProtocol = new window.pmtiles.Protocol();
      maplibregl.addProtocol("pmtiles", pmtilesProtocol.tile);
      protocolRegistered = true;
      return true;
    } catch (error) {
      console.warn("Failed to register pmtiles protocol:", error);
      return false;
    }
  }

  function rasterIdsFor(cellId) {
    return {
      source: `pmtiles-source-${cellId}`,
      layer: `pmtiles-layer-${cellId}`,
    };
  }

  function removeCellRaster(cellId) {
    if (!mapLoaded) return;
    const ids = rasterIdsFor(cellId);
    if (map.getLayer(ids.layer)) map.removeLayer(ids.layer);
    if (map.getSource(ids.source)) map.removeSource(ids.source);
    activeRasters.delete(cellId);
  }

  function rasterArchiveMinZoomFor(cell) {
    const entry = availablePmtiles.get(cell.id);
    const manifestMinZoom = Number(entry && entry.minzoom);
    if (Number.isFinite(manifestMinZoom)) return manifestMinZoom;
    if (Array.isArray(cell.zoom) && Number.isFinite(cell.zoom[0])) return cell.zoom[0];
    return 12;
  }

  // A short 128 px preview displays archive z12 at about map zoom 10.2. At
  // zoom 11 the source returns to its normal 256 px scale.
  function rasterActivationZoomFor(cell) {
    return Math.max(0, rasterArchiveMinZoomFor(cell) - RASTER_PREVIEW_ZOOM_OFFSET);
  }

  function rasterTileSizeForViewport(cell) {
    const standardZoom = rasterArchiveMinZoomFor(cell) - RASTER_STANDARD_ZOOM_OFFSET;
    return map.getZoom() + 1e-6 < standardZoom
      ? RASTER_PREVIEW_TILE_SIZE : RASTER_TILE_SIZE;
  }

  function bboxIntersectsViewport(bbox, bounds) {
    return bbox[0][0] <= bounds.getEast() && bbox[1][0] >= bounds.getWest()
      && bbox[0][1] <= bounds.getNorth() && bbox[1][1] >= bounds.getSouth();
  }

  function rasterCellsForViewport() {
    if (!catalog || !mapLoaded) return [];
    const bounds = map.getBounds();
    return catalog.cells.filter((cell) => {
      const bbox = analysisBBox(cell);
      return bbox && map.getZoom() + 1e-6 >= rasterActivationZoomFor(cell)
        && bboxIntersectsViewport(bbox, bounds);
    });
  }

  function syncRasterToMap() {
    const nextDesired = new Map(rasterCellsForViewport().map((cell) => [cell.id, {
      cell,
      tileSize: rasterTileSizeForViewport(cell),
    }]));

    for (const cellId of rasterLoads.keys()) {
      const next = nextDesired.get(cellId);
      const loading = rasterLoads.get(cellId);
      if (!next || !loading || next.tileSize !== loading.tileSize) rasterLoads.delete(cellId);
    }
    for (const cellId of activeRasters.keys()) {
      if (!nextDesired.has(cellId)) removeCellRaster(cellId);
    }
    for (const cellId of rasterFailures) {
      if (!nextDesired.has(cellId)) rasterFailures.delete(cellId);
    }

    desiredRasters = nextDesired;
    if (selectedCell && !desiredRasters.has(selectedCell.id)) setTilesNote("hidden");

    for (const { cell, tileSize } of desiredRasters.values()) {
      const active = activeRasters.get(cell.id);
      const loading = rasterLoads.get(cell.id);
      if (active && active.tileSize === tileSize) {
        setTilesNoteForCell(cell, "ready", `PMTiles loaded for ${cell.id}.`);
        continue;
      }
      if ((loading && loading.tileSize === tileSize) || rasterFailures.has(cell.id)) continue;
      void loadCellRaster(cell, tileSize);
    }
  }

  async function loadCellRaster(cell, tileSize) {
    const requestId = ++rasterRequestId;
    const loadState = { requestId, tileSize };
    rasterLoads.set(cell.id, loadState);
    const isCurrent = () => {
      const loading = rasterLoads.get(cell.id);
      const desired = desiredRasters.get(cell.id);
      return loading && loading.requestId === requestId
        && desired && desired.tileSize === tileSize;
    };
    if (!cell || cell.status !== "published") {
      removeCellRaster(cell.id);
      if (cell) setTilesNoteForCell(cell, "hidden");
      rasterLoads.delete(cell.id);
      return;
    }
    const hasEngine = typeof window.pmtiles !== "undefined" && window.pmtiles.PMTiles;
    const resource = availablePmtiles.get(cell.id);
    const absUrl = pmtilesUrlFor(cell);
    if (!resource || !absUrl || !hasEngine || !ensureProtocol()) {
      removeCellRaster(cell.id);
      rasterFailures.add(cell.id);
      setTilesNoteForCell(cell, "unavailable",
        environment === "publish" && !pmtilesBase
          ? `PMTiles publishing is not configured yet for ${cell.id}. The base map and details remain available.`
          : `PMTiles not available yet for ${cell.id}. Add the converted archive to the configured tile directory; the base map and details remain available.`);
      if (rasterLoads.get(cell.id) === loadState) rasterLoads.delete(cell.id);
      return;
    }
    try {
      const active = activeRasters.get(cell.id);
      if (active && active.url === absUrl && active.tileSize === tileSize) {
        setTilesNoteForCell(cell, "ready", `PMTiles loaded for ${cell.id}.`);
        return;
      }

      setTilesNoteForCell(cell, "loading", `Loading PMTiles for ${cell.id}…`);
      let header = resource.header;
      if (!header || resource.url !== absUrl) {
        const archive = new window.pmtiles.PMTiles(absUrl);
        header = await archive.getHeader();
        if (!isRasterHeader(header)) {
          throw new Error("This viewer expects raster PMTiles, but the archive contains vector tiles.");
        }
        pmtilesProtocol.add(archive);
        resource.header = header;
        resource.url = absUrl;
      }
      if (!isCurrent()) return;

      const catalogZoom = Array.isArray(cell.zoom) && cell.zoom.every(Number.isFinite)
        ? cell.zoom : [12, 16];
      const minzoom = Number.isFinite(header.minZoom) ? header.minZoom : catalogZoom[0];
      const maxzoom = Number.isFinite(header.maxZoom) ? header.maxZoom : catalogZoom[1];
      removeCellRaster(cell.id);
      const ids = rasterIdsFor(cell.id);
      map.addSource(ids.source, {
        type: "raster",
        tiles: [`pmtiles://${absUrl}/{z}/{x}/{y}`],
        tileSize,
        minzoom,
        maxzoom,
      });
      const before = map.getLayer("cells-line") ? "cells-line" : undefined;
      map.addLayer({
        id: ids.layer,
        type: "raster",
        source: ids.source,
      }, before);
      activeRasters.set(cell.id, { url: absUrl, tileSize });
      rasterFailures.delete(cell.id);
      const preview = tileSize === RASTER_PREVIEW_TILE_SIZE ? " preview" : "";
      console.info(`PMTiles${preview} ready for ${cell.id} (z${minzoom}–${maxzoom}).`);
      setTilesNoteForCell(cell, "ready", `PMTiles loaded for ${cell.id}.`);
    } catch (error) {
      if (!isCurrent()) return;
      removeCellRaster(cell.id);
      rasterFailures.add(cell.id);
      console.info(`PMTiles unavailable for ${cell.id}:`, error);
      setTilesNoteForCell(cell, "error",
        `PMTiles not available yet for ${cell.id}. The base map and details still work; ` +
        `add or verify the converted archive, then move away and back or select the cell to retry.`);
    } finally {
      if (rasterLoads.get(cell.id) === loadState) rasterLoads.delete(cell.id);
    }
  }

  /* ---- Overlay (cell polygons) ------------------------------------------- */

  function setFeatureSelected(id, selected) {
    if (!id || !installedCells) return;
    try {
      map.setFeatureState({ source: "cores", id }, { selected: Boolean(selected) });
    } catch (_error) { /* source may still be settling */ }
  }

  function installCellLayer() {
    if (installedCells || !coresData) return;
    const fc = coresData;
    for (const feature of fc.features) {
      feature.id = feature.properties.cell_id;
      feature.properties._label = displayId(feature.properties.cell_id);
    }
    map.addSource("cores", { type: "geojson", data: fc });

    map.addLayer({
      id: "cells-line",
      type: "line",
      source: "cores",
      layout: { "line-join": "round", "line-cap": "round" },
      paint: {
        "line-color": [
          "case",
          ["boolean", ["feature-state", "selected"], false],
          "#f8fafc",
          "#145b83",
        ],
        "line-width": [
          "case",
          ["boolean", ["feature-state", "selected"], false],
          3.75,
          1.5,
        ],
        "line-opacity": [
          "case",
          ["boolean", ["feature-state", "selected"], false],
          1,
          0.95,
        ],
      },
    });
    installedCells = true;
  }

  /* ---- DOM labels (mirrors the Leaflet visual language, offline-safe) ----- */

  function createLabels() {
    if (labelsCreated || !catalog) return;
    labelsCreated = true;
    for (const cell of catalog.cells) {
      const bbox = analysisBBox(cell);
      if (!bbox) continue;
      const el = document.createElement("div");
      el.className = "cell-label";
      el.setAttribute("aria-hidden", "true");
      const compact = document.createElement("span");
      compact.className = "compact";
      compact.textContent = compactId(cell.id);
      el.append(compact);
      mapShell.append(el);
      labelEls.set(cell.id, { el, cell, bbox });
    }
  }

  function updateLabels() {
    if (!labelEls.size || !mapLoaded) return;
    const container = map.getContainer();
    const size = { x: container.clientWidth, y: container.clientHeight };
    const show = map.getZoom() <= 12;
    for (const { el, bbox } of labelEls.values()) {
      if (!show) {
        el.style.display = "none";
        continue;
      }
      const point = map.project(centerOf(bbox));
      const inView = point.x >= -24 && point.x <= size.x + 24
        && point.y >= -24 && point.y <= size.y + 24;
      if (inView) {
        el.style.display = "block";
        el.style.left = `${point.x}px`;
        el.style.top = `${point.y}px`;
      } else {
        el.style.display = "none";
      }
    }
  }

  function scheduleLabels() {
    if (labelRaf) return;
    labelRaf = window.requestAnimationFrame(() => {
      labelRaf = 0;
      updateLabels();
    });
  }

  /* ---- Selection / panel -------------------------------------------------- */

  function showDetails(cell) {
    const pack = packageFor(cell);
    const downloadable = cell.status === "published" && pack && pack.download_url;
    fields.title.textContent = cell.id;
    fields.locality.textContent = cell.locality;
    fields.status.textContent = statusLabels[cell.status] || "In preparation";
    fields.status.classList.toggle("is-published", cell.status === "published");
    fields.edition.textContent = formatEdition(cell.edition);
    fields.zoom.textContent = Array.isArray(cell.zoom) && cell.zoom.every(Number.isFinite)
      ? `z${cell.zoom[0]}–${cell.zoom[1]}` : "—";
    fields.file.textContent = pack ? pack.file : "—";
    fields.size.textContent = pack ? formatBytes(pack.bytes) : "—";
    fields.checksum.textContent = pack ? pack.sha256 : "";
    checksumBlock.hidden = !pack;
    copyFeedback.textContent = "";

    downloadButton.hidden = !downloadable;
    unavailableMessage.hidden = Boolean(downloadable);
    if (downloadable) {
      downloadButton.href = pack.download_url;
      downloadButton.firstChild.textContent = `Download MBTiles · ${formatBytes(pack.bytes)} `;
      downloadButton.setAttribute("aria-label",
        `Download ${cell.id} MBTiles, ${formatBytes(pack.bytes)}; opens in a new tab`);
    } else {
      downloadButton.removeAttribute("href");
      downloadButton.removeAttribute("aria-label");
      unavailableMessage.textContent = "Download not available yet. This map sheet is still being prepared.";
    }
  }

  function openPanel() {
    app.classList.add("panel-open");
    panel.setAttribute("aria-hidden", "false");
    window.requestAnimationFrame(() => {
      map.resize();
      syncRasterToMap();
    });
  }

  function closePanel() {
    app.classList.remove("panel-open");
    panel.setAttribute("aria-hidden", "true");
    window.requestAnimationFrame(() => map.resize());
    window.setTimeout(() => {
      map.resize();
      updateLabels();
      syncRasterToMap();
    }, 240);
  }

  function selectCell(cellId, moveFocus = false) {
    const cell = cellsById.get(cellId);
    if (!cell) return;
    if (selectedCell && selectedCell.id !== cell.id) setFeatureSelected(selectedCell.id, false);
    selectedCell = cell;
    rasterFailures.delete(cell.id);
    setFeatureSelected(cell.id, true);
    showDetails(cell);
    setTilesNote("hidden");
    openPanel();

    const bbox = analysisBBox(cell);
    if (bbox) {
      window.setTimeout(() => {
        if (!selectedCell || selectedCell.id !== cell.id) return;
        map.resize();
        map.fitBounds(bbox, { padding: 40, maxZoom: 13, duration: 700 });
      }, 240);
    }
    syncRasterToMap();
    if (moveFocus) window.setTimeout(() => closePanelButton.focus(), 60);
  }

  function closeDetails(returnFocus = true) {
    if (!app.classList.contains("panel-open")) return;
    if (selectedCell) setFeatureSelected(selectedCell.id, false);
    closePanel();
    setTilesNote("hidden");
    const focusTarget = selectedCell;
    selectedCell = null;
    window.setTimeout(() => {
      if (returnFocus && focusTarget) {
        const bbox = analysisBBox(focusTarget);
        if (bbox) {
          // Best-effort focus back onto the map.
          document.getElementById("map").focus({ preventScroll: true });
        }
      }
    }, 40);
  }

  /* ---- Boot --------------------------------------------------------------- */

  map.on("load", () => {
    mapLoaded = true;
    if (catalog) installCellLayer();
    createLabels();
    updateLabels();
    syncRasterToMap();
  });

  map.on("mousemove", (event) => {
    map.getCanvas().style.cursor = cellForCoordinate(event.lngLat.lat, event.lngLat.lng)
      ? "pointer" : "";
  });
  map.on("mouseout", () => { map.getCanvas().style.cursor = ""; });
  map.on("click", (event) => {
    if (!installedCells) return;
    const cell = cellForCoordinate(event.lngLat.lat, event.lngLat.lng);
    if (cell) selectCell(cell.id, false);
    else closeDetails(false);
  });
  map.on("move", scheduleLabels);
  map.on("moveend", syncRasterToMap);
  map.on("zoom", scheduleLabels);

  async function loadAtlas() {
    try {
      const [catalogResponse, coresResponse, manifestResponse] = await Promise.all([
        fetch("../data/atlas.json", { cache: "no-cache" }),
        fetch("../data/cores.geojson", { cache: "no-cache" }),
        fetch(pmtilesManifestUrl, { cache: "no-cache" }),
      ]);
      if (!catalogResponse.ok || !coresResponse.ok || !manifestResponse.ok) {
        throw new Error("Atlas data request failed");
      }
      const fullCatalog = await catalogResponse.json();
      const fullCoresData = await coresResponse.json();
      const manifest = await manifestResponse.json();
      if (!Array.isArray(fullCatalog.cells) || !fullCatalog.cells.length ||
          !Array.isArray(fullCoresData.features) || fullCoresData.features.length !== fullCatalog.cell_count) {
        throw new Error("Unexpected atlas catalogue");
      }
      if (manifest.schema_version !== 1 || !manifest.sheets ||
          typeof manifest.sheets !== "object" || Array.isArray(manifest.sheets)) {
        throw new Error("Unexpected PMTiles manifest");
      }

      const validIds = new Set();
      for (const cell of fullCatalog.cells) {
        if (cell.status !== "published" || !(cell.id in manifest.sheets)) continue;
        const rawEntry = manifest.sheets[cell.id];
        let entry;
        if (typeof rawEntry === "string") entry = { file: rawEntry };
        else if (rawEntry && typeof rawEntry === "object" && !Array.isArray(rawEntry)) {
          entry = { ...rawEntry };
        } else continue;
        entry.file = entry.file || derivedPmtilesFileFor(cell);
        if (!entry.file || !/\.pmtiles$/i.test(entry.file)) continue;
        availablePmtiles.set(cell.id, entry);
        validIds.add(cell.id);
      }
      const validCells = fullCatalog.cells.filter((cell) => validIds.has(cell.id));
      searchBounds = bufferedBoundsForCells(validCells);

      catalog = {
        ...fullCatalog,
        cells: validCells,
        cell_count: validCells.length,
        published_count: validCells.length,
      };
      coresData = {
        ...fullCoresData,
        features: fullCoresData.features.filter((feature) =>
          validIds.has(feature.properties && feature.properties.cell_id)),
      };
      for (const cell of validCells) cellsById.set(cell.id, cell);
      if (mapLoaded) installCellLayer();
      createLabels();
      syncRasterToMap();
      summary.textContent = validCells.length === 1
        ? "1 PMTiles map sheet available"
        : `${validCells.length} PMTiles map sheets available`;
      loadingState.hidden = true;
    } catch (error) {
      console.error(error);
      loadingState.hidden = true;
      errorState.hidden = false;
      summary.textContent = "Atlas unavailable";
    }
  }

  closePanelButton.addEventListener("click", () => closeDetails(true));
  placeSearch.addEventListener("submit", (event) => {
    event.preventDefault();
    void showSearchResults(placeSearchInput.value);
  });
  placeSearchInput.addEventListener("input", clearSearchFeedback);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeDetails(true);
  });

  copyChecksumButton.addEventListener("click", async () => {
    if (!fields.checksum.textContent) return;
    try {
      await navigator.clipboard.writeText(fields.checksum.textContent);
      copyFeedback.textContent = "Checksum copied.";
    } catch (_error) {
      copyFeedback.textContent = "Select the checksum and copy it manually.";
    }
  });

  window.addEventListener("resize", () => {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(() => {
      map.resize();
      updateLabels();
      syncRasterToMap();
    }, 120);
  });

  loadAtlas();
})();
