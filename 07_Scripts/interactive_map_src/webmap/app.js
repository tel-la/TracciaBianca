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
  const measureToggle = document.getElementById("measure-toggle");
  const measureReadout = document.getElementById("measure-readout");
  const measureText = document.getElementById("measure-text");
  const measureClear = document.getElementById("measure-clear");
  const routeToggle = document.getElementById("route-toggle");
  const routeReadout = document.getElementById("route-readout");
  const routeText = document.getElementById("route-text");
  const routeUndo = document.getElementById("route-undo");
  const routeClear = document.getElementById("route-clear");
  const routeDownload = document.getElementById("route-download");
  const routeProfile = document.getElementById("route-profile");
  const routeElevationStatus = document.getElementById("route-elevation-status");
  const routeProfileChart = document.getElementById("route-profile-chart");
  const routeProfileExpand = document.getElementById("route-profile-expand");
  const routeProfileDialog = document.getElementById("route-profile-dialog");
  const routeProfileClose = document.getElementById("route-profile-close");
  const routeElevationStatusExpanded = document.getElementById("route-elevation-status-expanded");
  const routeProfileChartExpanded = document.getElementById("route-profile-chart-expanded");
  const routeProfileCharts = [routeProfileChart, routeProfileChartExpanded];
  const routeStatValues = document.querySelectorAll("[data-route-stat]");
  const measurementLabel = document.getElementById("measurement-label");
  const coordinateMenu = document.getElementById("coordinate-menu");
  const coordinateValues = document.getElementById("coordinate-values");
  const coordinateLink = document.getElementById("coordinate-link");
  const pmtilesVisibilityToggle = document.getElementById("pmtiles-visibility-toggle");
  const NOMINATIM_URL = "https://nominatim.openstreetmap.org/search";
  const SEARCH_BOUNDS_BUFFER_KM = 20;
  const MAPLIBRE_CANONICAL_TILE_SIZE = 512;
  const DESKTOP_RASTER_ZOOM_SHIFT = 2.5;
  const MOBILE_CELL_SPAN_THRESHOLD = 0.6;
  const MOBILE_MEDIA_QUERY = "(max-width: 720px)";
  const CELL_LABEL_HIDE_ARCHIVE_ZOOM = 14;
  const MEASUREMENT_SOURCE = "distance-measurement";
  const MEASUREMENT_LINE_LAYER = "distance-measurement-line";
  const MEASUREMENT_POINT_LAYER = "distance-measurement-points";
  const ROUTE_SOURCE = "planned-route";
  const ROUTE_LINE_LAYER = "planned-route-line";
  const ROUTE_POINT_LAYER = "planned-route-points";
  const ROUTE_HOVER_HALO_LAYER = "planned-route-profile-position-halo";
  const ROUTE_HOVER_LAYER = "planned-route-profile-position";
  const ELEVATION_API = "https://api.open-meteo.com/v1/elevation";
  const PROFILE_PLOTS = {
    compact: { left: 38, right: 310, top: 8, bottom: 72, axisY: 86 },
    expanded: { left: 38, right: 310, top: 8, bottom: 130, axisY: 145 },
  };
  const PMTILES_HOLD_DELAY_MS = 1200;
  const PMTILES_HOLD_MOVE_TOLERANCE = 10;

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
  map.addControl(new maplibregl.ScaleControl({ maxWidth: 140, unit: "metric" }), "bottom-left");

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
  let measurementActive = false;
  let measurementPoints = [];
  let measurementPreviewPoint = null;
  let routeActive = false;
  let routePoints = [];
  let routeProfilePoints = [];
  let routeHoverPoint = null;
  let routeElevationRequestId = 0;
  let pmtilesEnabled = true;
  let pmtilesPeekHidden = false;
  let pmtilesHoldTimer = null;
  let pmtilesHoldPointerId = null;
  let pmtilesHoldStart = null;
  let suppressNextMapClick = false;
  let suppressNextMapClickTimer = null;
  let routeProfileResizeRaf = 0;

  const routeProfileResizeObserver = new ResizeObserver(() => {
    if (!routeProfileDialog.open || routeProfilePoints.length < 2) return;
    window.cancelAnimationFrame(routeProfileResizeRaf);
    routeProfileResizeRaf = window.requestAnimationFrame(() => drawElevationProfile(routeProfilePoints));
  });
  routeProfileResizeObserver.observe(routeProfileChartExpanded);

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

  function pmtilesLayersAreVisible() {
    return pmtilesEnabled && !pmtilesPeekHidden;
  }

  function applyPmtilesVisibility() {
    const visibility = pmtilesLayersAreVisible() ? "visible" : "none";
    for (const cellId of activeRasters.keys()) {
      const layerId = rasterIdsFor(cellId).layer;
      if (map.getLayer(layerId)) map.setLayoutProperty(layerId, "visibility", visibility);
    }
  }

  function updatePmtilesVisibilityToggle() {
    pmtilesVisibilityToggle.textContent = pmtilesEnabled ? "Hide PMTiles" : "Show PMTiles";
    pmtilesVisibilityToggle.setAttribute("aria-pressed", String(pmtilesEnabled));
  }

  function setPmtilesEnabled(enabled) {
    pmtilesEnabled = Boolean(enabled);
    pmtilesPeekHidden = false;
    cancelPmtilesHold();
    updatePmtilesVisibilityToggle();
    applyPmtilesVisibility();
    if (pmtilesEnabled) syncRasterToMap();
  }

  function rasterArchiveMinZoomFor(cell) {
    const entry = availablePmtiles.get(cell.id);
    const manifestMinZoom = Number(entry && entry.minzoom);
    if (Number.isFinite(manifestMinZoom)) return manifestMinZoom;
    if (Array.isArray(cell.zoom) && Number.isFinite(cell.zoom[0])) return cell.zoom[0];
    return 12;
  }

  function isMobileViewport() {
    return window.matchMedia(MOBILE_MEDIA_QUERY).matches;
  }

  function mobileCellSpanRatio(cell) {
    const bbox = analysisBBox(cell);
    const container = map.getContainer();
    if (!bbox || !container.clientWidth || !container.clientHeight) return 0;
    const southWest = map.project(bbox[0]);
    const northEast = map.project(bbox[1]);
    const widthRatio = Math.abs(northEast.x - southWest.x) / container.clientWidth;
    const heightRatio = Math.abs(southWest.y - northEast.y) / container.clientHeight;
    return Math.max(widthRatio, heightRatio);
  }

  function rasterDisplayProfileFor(cell) {
    const archiveMinZoom = rasterArchiveMinZoomFor(cell);
    let activationZoom = archiveMinZoom - DESKTOP_RASTER_ZOOM_SHIFT;
    if (isMobileViewport()) {
      const spanRatio = mobileCellSpanRatio(cell);
      if (spanRatio > 0) {
        activationZoom = map.getZoom()
          + Math.log2(MOBILE_CELL_SPAN_THRESHOLD / spanRatio);
      }
    }
    activationZoom = Math.max(0, Math.round(activationZoom * 1000) / 1000);
    const earlyZoomShift = archiveMinZoom - activationZoom;
    const regularZoomShift = archiveMinZoom - (activationZoom + 0.5);
    const earlyTileSize = Math.round(
      (MAPLIBRE_CANONICAL_TILE_SIZE / Math.pow(2, earlyZoomShift)) * 1000) / 1000;
    const regularTileSize = Math.round(
      (MAPLIBRE_CANONICAL_TILE_SIZE / Math.pow(2, regularZoomShift)) * 1000) / 1000;
    const tileSize = map.getZoom() + 1e-6 < activationZoom + 0.5
      ? earlyTileSize : regularTileSize;
    return { activationZoom, tileSize };
  }

  function displayedPmtilesZoomFor(cell) {
    const profile = rasterDisplayProfileFor(cell);
    const zoomShift = Math.log2(MAPLIBRE_CANONICAL_TILE_SIZE / profile.tileSize);
    return map.getZoom() + zoomShift;
  }

  function bboxIntersectsViewport(bbox, bounds) {
    return bbox[0][0] <= bounds.getEast() && bbox[1][0] >= bounds.getWest()
      && bbox[0][1] <= bounds.getNorth() && bbox[1][1] >= bounds.getSouth();
  }

  function rasterCellsForViewport() {
    if (!catalog || !mapLoaded) return [];
    const bounds = map.getBounds();
    const matches = [];
    for (const cell of catalog.cells) {
      const bbox = analysisBBox(cell);
      if (!bbox || !bboxIntersectsViewport(bbox, bounds)) continue;
      const profile = rasterDisplayProfileFor(cell);
      if (map.getZoom() + 1e-6 >= profile.activationZoom) {
        matches.push({ cell, ...profile });
      }
    }
    return matches;
  }

  function syncRasterToMap() {
    const nextDesired = new Map(rasterCellsForViewport().map((entry) =>
      [entry.cell.id, entry]));

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
    if (!pmtilesEnabled) return;

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
        layout: { visibility: pmtilesLayersAreVisible() ? "visible" : "none" },
      }, before);
      activeRasters.set(cell.id, { url: absUrl, tileSize });
      rasterFailures.delete(cell.id);
      const zoomShift = Math.log2(MAPLIBRE_CANONICAL_TILE_SIZE / tileSize);
      const displayMinZoom = minzoom - zoomShift;
      const displayMaxZoom = maxzoom - zoomShift;
      console.info(
        `PMTiles ready for ${cell.id}: archive z${minzoom}–${maxzoom} `
        + `displayed at map z${displayMinZoom.toFixed(2)}–${displayMaxZoom.toFixed(2)}.`);
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
    raiseMeasurementLayers();
  }

  /* ---- DOM labels (mirrors the Leaflet visual language, offline-safe) ----- */

  function createLabels() {
    if (labelsCreated || !catalog) return;
    labelsCreated = true;
    for (const cell of catalog.cells) {
      const bbox = analysisBBox(cell);
      if (!bbox) continue;
      const el = document.createElement("button");
      el.type = "button";
      el.className = "cell-label";
      el.setAttribute("aria-label", `Open details for ${cell.id}, ${cell.locality}`);
      el.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        selectCell(cell.id, true);
      });
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
    for (const { el, cell, bbox } of labelEls.values()) {
      const show = displayedPmtilesZoomFor(cell) + 1e-6 < CELL_LABEL_HIDE_ARCHIVE_ZOOM;
      if (!show) {
        if (document.activeElement === el) map.getCanvas().focus();
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

  /* ---- Scale, straight-line measurement and coordinate menu ------------- */

  function measurementEndpoints() {
    if (measurementPoints.length === 2) return measurementPoints;
    if (measurementPoints.length === 1 && measurementPreviewPoint) {
      return [measurementPoints[0], measurementPreviewPoint];
    }
    return null;
  }

  function measurementData() {
    const displayedPoints = [...measurementPoints];
    if (measurementPoints.length === 1 && measurementPreviewPoint) {
      displayedPoints.push(measurementPreviewPoint);
    }
    const coordinates = displayedPoints.map((point) => [point.lng, point.lat]);
    const features = coordinates.map((coordinate, index) => ({
      type: "Feature",
      properties: { index, preview: index >= measurementPoints.length },
      geometry: { type: "Point", coordinates: coordinate },
    }));
    if (coordinates.length === 2) {
      features.unshift({
        type: "Feature",
        properties: {},
        geometry: { type: "LineString", coordinates },
      });
    }
    return { type: "FeatureCollection", features };
  }

  function raiseMeasurementLayers() {
    if (map.getLayer(MEASUREMENT_LINE_LAYER)) map.moveLayer(MEASUREMENT_LINE_LAYER);
    if (map.getLayer(MEASUREMENT_POINT_LAYER)) map.moveLayer(MEASUREMENT_POINT_LAYER);
    if (map.getLayer(ROUTE_LINE_LAYER)) map.moveLayer(ROUTE_LINE_LAYER);
    if (map.getLayer(ROUTE_POINT_LAYER)) map.moveLayer(ROUTE_POINT_LAYER);
    if (map.getLayer(ROUTE_HOVER_HALO_LAYER)) map.moveLayer(ROUTE_HOVER_HALO_LAYER);
    if (map.getLayer(ROUTE_HOVER_LAYER)) map.moveLayer(ROUTE_HOVER_LAYER);
  }

  function installMeasurementLayers() {
    if (!mapLoaded || map.getSource(MEASUREMENT_SOURCE)) return;
    map.addSource(MEASUREMENT_SOURCE, { type: "geojson", data: measurementData() });
    map.addLayer({
      id: MEASUREMENT_LINE_LAYER,
      type: "line",
      source: MEASUREMENT_SOURCE,
      filter: ["==", ["geometry-type"], "LineString"],
      layout: { "line-cap": "round", "line-join": "round" },
      paint: {
        "line-color": "#d14f2a",
        "line-width": 3,
        "line-opacity": 0.95,
      },
    });
    map.addLayer({
      id: MEASUREMENT_POINT_LAYER,
      type: "circle",
      source: MEASUREMENT_SOURCE,
      filter: ["==", ["geometry-type"], "Point"],
      paint: {
        "circle-radius": 6,
        "circle-color": "#f8fafc",
        "circle-stroke-color": "#d14f2a",
        "circle-stroke-width": 3,
      },
    });
  }

  function updateMeasurementData() {
    installMeasurementLayers();
    const source = map.getSource(MEASUREMENT_SOURCE);
    if (source) source.setData(measurementData());
    updateMeasurementLabel();
  }

  function haversineDistanceMeters(start, end) {
    const toRadians = (degrees) => degrees * Math.PI / 180;
    const earthRadiusMeters = 6371008.8;
    const latitudeDelta = toRadians(end.lat - start.lat);
    const longitudeDelta = toRadians(end.lng - start.lng);
    const startLatitude = toRadians(start.lat);
    const endLatitude = toRadians(end.lat);
    const a = Math.sin(latitudeDelta / 2) ** 2
      + Math.cos(startLatitude) * Math.cos(endLatitude)
      * Math.sin(longitudeDelta / 2) ** 2;
    return earthRadiusMeters * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }

  function routeData() {
    const coordinates = routePoints.map((point) => [point.lng, point.lat]);
    const features = coordinates.map((coordinate) => ({ type: "Feature", properties: { role: "waypoint" }, geometry: { type: "Point", coordinates: coordinate } }));
    if (coordinates.length > 1) features.unshift({ type: "Feature", properties: { role: "route" }, geometry: { type: "LineString", coordinates } });
    if (routeHoverPoint) features.push({
      type: "Feature",
      properties: { role: "profile-position" },
      geometry: { type: "Point", coordinates: [routeHoverPoint.lng, routeHoverPoint.lat] },
    });
    return { type: "FeatureCollection", features };
  }

  function installRouteLayers() {
    if (!mapLoaded || map.getSource(ROUTE_SOURCE)) return;
    map.addSource(ROUTE_SOURCE, { type: "geojson", data: routeData() });
    map.addLayer({ id: ROUTE_LINE_LAYER, type: "line", source: ROUTE_SOURCE, filter: ["==", ["geometry-type"], "LineString"], layout: { "line-cap": "round", "line-join": "round" }, paint: { "line-color": "#d14f2a", "line-width": 4 } });
    map.addLayer({ id: ROUTE_POINT_LAYER, type: "circle", source: ROUTE_SOURCE, filter: ["==", ["get", "role"], "waypoint"], paint: { "circle-radius": 6, "circle-color": "#fff", "circle-stroke-color": "#d14f2a", "circle-stroke-width": 3 } });
    map.addLayer({ id: ROUTE_HOVER_HALO_LAYER, type: "circle", source: ROUTE_SOURCE, filter: ["==", ["get", "role"], "profile-position"], paint: { "circle-radius": 14, "circle-color": "#d14f2a", "circle-opacity": 0.3, "circle-blur": 0.25 } });
    map.addLayer({ id: ROUTE_HOVER_LAYER, type: "circle", source: ROUTE_SOURCE, filter: ["==", ["get", "role"], "profile-position"], paint: { "circle-radius": 8, "circle-color": "#d14f2a", "circle-stroke-color": "#fff", "circle-stroke-width": 3 } });
  }

  function updateRouteSource() {
    installRouteLayers();
    const source = map.getSource(ROUTE_SOURCE);
    if (source) source.setData(routeData());
  }

  function routeDistance(points = routePoints) {
    return points.slice(1).reduce((total, point, index) => total + haversineDistanceMeters(points[index], point), 0);
  }

  function sampleRoute(points, maximum = 100) {
    if (points.length < 2) return points.map((point) => ({ ...point }));
    const lengths = points.slice(1).map((point, index) => haversineDistanceMeters(points[index], point));
    const total = lengths.reduce((sum, value) => sum + value, 0);
    const count = Math.min(maximum, Math.max(points.length, Math.ceil(total / 250) + 1));
    const samples = [];
    for (let index = 0; index < count; index += 1) {
      const target = total * index / (count - 1);
      let travelled = 0;
      let segment = 0;
      while (segment < lengths.length - 1 && travelled + lengths[segment] < target) travelled += lengths[segment++];
      const ratio = lengths[segment] ? (target - travelled) / lengths[segment] : 0;
      samples.push({ lng: points[segment].lng + (points[segment + 1].lng - points[segment].lng) * ratio, lat: points[segment].lat + (points[segment + 1].lat - points[segment].lat) * ratio });
    }
    return samples;
  }

  function setRouteElevationStatus(message) {
    routeElevationStatus.textContent = message;
    routeElevationStatusExpanded.textContent = message;
  }

  function routeElevationStats(points) {
    if (!points.some((point) => Number.isFinite(point.ele))) {
      return { start: "—", finish: "—", gain: "—", loss: "—" };
    }
    let gain = 0;
    let loss = 0;
    for (let index = 1; index < points.length; index += 1) {
      if (!Number.isFinite(points[index - 1].ele) || !Number.isFinite(points[index].ele)) continue;
      const change = points[index].ele - points[index - 1].ele;
      if (change > 0) gain += change;
      else loss -= change;
    }
    return {
      start: Number.isFinite(points[0]?.ele) ? `${Math.round(points[0].ele)} m` : "—",
      finish: Number.isFinite(points.at(-1)?.ele) ? `${Math.round(points.at(-1).ele)} m` : "—",
      gain: `${Math.round(gain)} m`,
      loss: `${Math.round(loss)} m`,
    };
  }

  function renderRouteStats(points) {
    const stats = routeElevationStats(points);
    for (const value of routeStatValues) value.textContent = stats[value.dataset.routeStat];
  }

  function cumulativeGainAt(points, lowerIndex, segmentRatio) {
    let gain = 0;
    for (let index = 1; index <= lowerIndex; index += 1) {
      const change = points[index].ele - points[index - 1].ele;
      if (Number.isFinite(change) && change > 0) gain += change;
    }
    if (lowerIndex < points.length - 1 && segmentRatio > 0) {
      const partialChange = points[lowerIndex + 1].ele - points[lowerIndex].ele;
      if (Number.isFinite(partialChange) && partialChange > 0) gain += partialChange * segmentRatio;
    }
    return gain;
  }

  function niceProfileStep(value) {
    const magnitude = 10 ** Math.floor(Math.log10(Math.max(1, value)));
    const normalized = value / magnitude;
    const factor = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10;
    return factor * magnitude;
  }

  function profilePlotFor(chart) {
    if (chart !== routeProfileChartExpanded || !chart.clientWidth || !chart.clientHeight) {
      return chart === routeProfileChartExpanded ? PROFILE_PLOTS.expanded : PROFILE_PLOTS.compact;
    }
    const viewHeight = Math.max(115, Math.min(240, 320 * chart.clientHeight / chart.clientWidth));
    chart.setAttribute("viewBox", `0 0 320 ${viewHeight}`);
    return { left: 38, right: 310, top: 8, bottom: viewHeight - 20, axisY: viewHeight - 5 };
  }

  function profileScale(points, plot) {
    const elevations = points.map((point) => point.ele).filter(Number.isFinite);
    if (elevations.length < 2) return null;
    const rawMin = Math.min(...elevations);
    const rawMax = Math.max(...elevations);
    const step = niceProfileStep((rawMax - rawMin) / 4);
    const min = Math.floor(rawMin / step) * step;
    const max = Math.max(min + step, Math.ceil(rawMax / step) * step);
    return {
      min,
      max,
      step,
      x: (fraction) => plot.left + fraction * (plot.right - plot.left),
      y: (elevation) => plot.bottom - (elevation - min) * (plot.bottom - plot.top) / (max - min),
    };
  }

  function formatProfileDistance(distance, total) {
    if (total < 1000) return `${Math.round(distance)} m`;
    if (distance === 0) return "0";
    const decimals = total < 10000 ? 1 : 0;
    return `${(distance / 1000).toFixed(decimals)} km`;
  }

  function drawElevationProfile(points) {
    if (!profileScale(points, PROFILE_PLOTS.compact)) {
      for (const chart of routeProfileCharts) chart.replaceChildren();
      return;
    }
    const totalDistance = routeDistance();
    for (const chart of routeProfileCharts) {
      const plot = profilePlotFor(chart);
      const scale = profileScale(points, plot);
      const coordinates = points.map((point, index) => `${scale.x(index / (points.length - 1))},${scale.y(point.ele)}`).join(" ");
      const horizontalGrid = [];
      for (let elevation = scale.min; elevation <= scale.max + scale.step / 2; elevation += scale.step) {
        const y = scale.y(elevation);
        horizontalGrid.push(`<line x1="${plot.left}" x2="${plot.right}" y1="${y}" y2="${y}"/><text class="profile-axis-label" x="34" y="${y + 2.5}" text-anchor="end">${Math.round(elevation)} m</text>`);
      }
      const verticalGrid = [];
      for (let index = 0; index <= 4; index += 1) {
        const fraction = index / 4;
        const x = scale.x(fraction);
        const anchor = index === 0 ? "start" : index === 4 ? "end" : "middle";
        verticalGrid.push(`<line x1="${x}" x2="${x}" y1="${plot.top}" y2="${plot.bottom}"/><text class="profile-axis-label" x="${x}" y="${plot.axisY}" text-anchor="${anchor}">${formatProfileDistance(totalDistance * fraction, totalDistance)}</text>`);
      }
      chart.innerHTML = `<g class="profile-grid">${horizontalGrid.join("")}${verticalGrid.join("")}</g><polyline points="${plot.left},${plot.bottom} ${coordinates} ${plot.right},${plot.bottom}"/><g class="profile-inspector" hidden><line class="profile-inspector-horizontal" x1="${plot.left}" x2="${plot.right}"/><line class="profile-inspector-vertical" y1="${plot.top}" y2="${plot.bottom}"/><circle r="4"/><text class="profile-inspector-summary"></text><text class="profile-inspector-altitude" x="34" text-anchor="end"></text></g>`;
    }
    renderRouteStats(points);
  }

  function inspectRouteProfile(chart, event) {
    if (routeProfilePoints.length < 2) return;
    const plot = profilePlotFor(chart);
    const bounds = chart.getBoundingClientRect();
    const chartX = (event.clientX - bounds.left) * 320 / bounds.width;
    const fraction = Math.max(0, Math.min(1, (chartX - plot.left) / (plot.right - plot.left)));
    const scaledIndex = fraction * (routeProfilePoints.length - 1);
    const lowerIndex = Math.floor(scaledIndex);
    const upperIndex = Math.min(routeProfilePoints.length - 1, lowerIndex + 1);
    const ratio = scaledIndex - lowerIndex;
    const lower = routeProfilePoints[lowerIndex];
    const upper = routeProfilePoints[upperIndex];
    const cumulativeGain = cumulativeGainAt(routeProfilePoints, lowerIndex, ratio);
    routeHoverPoint = {
      lng: lower.lng + (upper.lng - lower.lng) * ratio,
      lat: lower.lat + (upper.lat - lower.lat) * ratio,
      ele: lower.ele + (upper.ele - lower.ele) * ratio,
    };
    if (!profileScale(routeProfilePoints, plot)) return;
    for (const profileChart of routeProfileCharts) {
      const profilePlot = profilePlotFor(profileChart);
      const profileChartScale = profileScale(routeProfilePoints, profilePlot);
      const inspector = profileChart.querySelector(".profile-inspector");
      if (!inspector || !profileChartScale) continue;
      inspector.removeAttribute("hidden");
      const verticalLine = inspector.querySelector(".profile-inspector-vertical");
      const horizontalLine = inspector.querySelector(".profile-inspector-horizontal");
      const circle = inspector.querySelector("circle");
      const label = inspector.querySelector(".profile-inspector-summary");
      const altitudeLabel = inspector.querySelector(".profile-inspector-altitude");
      const profileX = profileChartScale.x(fraction);
      const profileY = profileChartScale.y(routeHoverPoint.ele);
      verticalLine.setAttribute("x1", profileX); verticalLine.setAttribute("x2", profileX);
      horizontalLine.setAttribute("y1", profileY); horizontalLine.setAttribute("y2", profileY);
      circle.setAttribute("cx", profileX); circle.setAttribute("cy", profileY);
      label.setAttribute("x", profileX + (fraction > 0.68 ? -5 : 5));
      label.setAttribute("y", profileY < 20 ? profileY + 12 : profileY - 5);
      label.setAttribute("text-anchor", fraction > 0.68 ? "end" : "start");
      label.textContent = `${formatDistance(routeDistance() * fraction)} · D+ ${Math.round(cumulativeGain)} m`;
      altitudeLabel.setAttribute("y", profileY + 2.5);
      altitudeLabel.textContent = `${Math.round(routeHoverPoint.ele)} m`;
    }
    updateRouteSource();
  }

  function clearRouteProfileInspection() {
    routeHoverPoint = null;
    for (const chart of routeProfileCharts) {
      const inspector = chart.querySelector(".profile-inspector");
      if (inspector) inspector.setAttribute("hidden", "");
    }
    updateRouteSource();
  }

  async function updateRouteElevation() {
    const requestId = ++routeElevationRequestId;
    if (routePoints.length < 2) return;
    routeProfile.hidden = false;
    setRouteElevationStatus("Loading elevation…");
    const samples = sampleRoute(routePoints);
    const url = new URL(ELEVATION_API);
    url.searchParams.set("latitude", samples.map((point) => point.lat.toFixed(6)).join(","));
    url.searchParams.set("longitude", samples.map((point) => point.lng.toFixed(6)).join(","));
    try {
      const response = await fetch(url, { credentials: "omit" });
      if (!response.ok) throw new Error(`Elevation request failed (${response.status})`);
      const data = await response.json();
      if (requestId !== routeElevationRequestId || !Array.isArray(data.elevation)) return;
      routeProfilePoints = samples.map((point, index) => {
        const rawElevation = data.elevation[index];
        const elevation = rawElevation === null || rawElevation === undefined ? NaN : Number(rawElevation);
        return { ...point, ele: Number.isFinite(elevation) ? elevation : NaN };
      });
      const validElevations = routeProfilePoints.map((point) => point.ele).filter(Number.isFinite);
      if (validElevations.length < 2) throw new Error("Elevation response did not contain enough values");
      drawElevationProfile(routeProfilePoints);
      setRouteElevationStatus(`${formatDistance(routeDistance())} · ${Math.round(Math.min(...validElevations))}–${Math.round(Math.max(...validElevations))} m`);
      routeDownload.disabled = false;
    } catch (error) {
      console.warn(error);
      routeProfilePoints = samples;
      drawElevationProfile(routeProfilePoints);
      setRouteElevationStatus("Elevation temporarily unavailable; GPX remains downloadable.");
      routeDownload.disabled = false;
    }
  }

  function updateRoute() {
    routeHoverPoint = null;
    updateRouteSource();
    routeText.textContent = routePoints.length ? `${routePoints.length} points · ${formatDistance(routeDistance())}` : "Click to add points.";
    routeUndo.disabled = !routePoints.length; routeDownload.disabled = routePoints.length < 2;
    routeProfilePoints = [];
    drawElevationProfile(routeProfilePoints);
    renderRouteStats(routeProfilePoints);
    if (routePoints.length < 2) {
      routeProfile.hidden = true;
      routeElevationRequestId += 1;
      if (routeProfileDialog.open) routeProfileDialog.close();
    }
    else void updateRouteElevation();
  }

  function setRouteMode(active) {
    routeActive = active; routeToggle.setAttribute("aria-pressed", String(active));
    routeReadout.hidden = !active && !routePoints.length;
    map.getCanvas().classList.toggle("is-routing", active);
    if (active) { setMeasurementMode(false); closeCoordinateMenu(); closeDetails(false); }
  }

  function downloadRouteGpx() {
    const points = routeProfilePoints.length ? routeProfilePoints : routePoints;
    if (points.length < 2) return;
    const trackPoints = points.map((point) => `      <trkpt lat="${point.lat.toFixed(7)}" lon="${point.lng.toFixed(7)}">${Number.isFinite(point.ele) ? `<ele>${Math.round(point.ele)}</ele>` : ""}</trkpt>`).join("\n");
    const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1" creator="TracciaBianca Map inspector" xmlns="http://www.topografix.com/GPX/1/1"><metadata><name>TracciaBianca planned route</name></metadata><trk><name>Planned route</name><trkseg>\n${trackPoints}\n</trkseg></trk></gpx>`;
    const link = document.createElement("a"); link.href = URL.createObjectURL(new Blob([xml], { type: "application/gpx+xml" })); link.download = "tracciabianca-route.gpx"; link.click(); URL.revokeObjectURL(link.href);
  }

  function formatDistance(meters) {
    if (meters < 1000) return `${Math.round(meters)} m`;
    const kilometres = meters / 1000;
    return `${kilometres.toLocaleString("en", {
      minimumFractionDigits: kilometres < 10 ? 2 : 1,
      maximumFractionDigits: kilometres < 10 ? 2 : 1,
    })} km`;
  }

  function updateMeasurementLabel() {
    const endpoints = measurementEndpoints();
    if (!endpoints || !mapLoaded) {
      measurementLabel.hidden = true;
      return;
    }
    const distanceText = formatDistance(haversineDistanceMeters(endpoints[0], endpoints[1]));
    const midpoint = {
      lng: (endpoints[0].lng + endpoints[1].lng) / 2,
      lat: (endpoints[0].lat + endpoints[1].lat) / 2,
    };
    const point = map.project(midpoint);
    const container = map.getContainer();
    const visible = point.x >= 0 && point.x <= container.clientWidth
      && point.y >= 0 && point.y <= container.clientHeight;
    measurementLabel.hidden = !visible;
    if (!visible) return;
    measurementLabel.textContent = distanceText;
    measurementLabel.style.left = `${point.x}px`;
    measurementLabel.style.top = `${point.y}px`;
  }

  function setMeasurementMode(active) {
    measurementActive = active;
    measureToggle.setAttribute("aria-pressed", String(active));
    map.getCanvas().classList.toggle("is-measuring", active);
  }

  function clearMeasurement() {
    measurementPoints = [];
    measurementPreviewPoint = null;
    setMeasurementMode(false);
    updateMeasurementData();
    measureReadout.hidden = true;
    measureText.textContent = "";
  }

  function startMeasurement() {
    setRouteMode(false);
    closeDetails(false);
    closeCoordinateMenu();
    measurementPoints = [];
    measurementPreviewPoint = null;
    updateMeasurementData();
    setMeasurementMode(true);
    measureText.textContent = "Click the starting point.";
    measureReadout.hidden = false;
  }

  function addMeasurementPoint(lngLat) {
    measurementPoints.push({ lng: lngLat.lng, lat: lngLat.lat });
    measurementPreviewPoint = null;
    updateMeasurementData();
    if (measurementPoints.length === 1) {
      measureText.textContent = "Move the pointer, then click the end point.";
      return;
    }
    const distance = haversineDistanceMeters(measurementPoints[0], measurementPoints[1]);
    measureText.textContent = `${formatDistance(distance)} straight line`;
    setMeasurementMode(false);
  }

  function updateMeasurementPreview(event) {
    if (!measurementActive || measurementPoints.length !== 1) return;
    measurementPreviewPoint = { lng: event.lngLat.lng, lat: event.lngLat.lat };
    const distance = haversineDistanceMeters(measurementPoints[0], measurementPreviewPoint);
    measureText.textContent = `${formatDistance(distance)} straight line`;
    updateMeasurementData();
  }

  function cancelPmtilesHold() {
    if (pmtilesHoldTimer !== null) {
      window.clearTimeout(pmtilesHoldTimer);
      pmtilesHoldTimer = null;
    }
    pmtilesHoldPointerId = null;
    pmtilesHoldStart = null;
    if (pmtilesPeekHidden) {
      pmtilesPeekHidden = false;
      applyPmtilesVisibility();
    }
  }

  function suppressMapClickBriefly() {
    suppressNextMapClick = true;
    if (suppressNextMapClickTimer !== null) {
      window.clearTimeout(suppressNextMapClickTimer);
    }
    suppressNextMapClickTimer = window.setTimeout(() => {
      suppressNextMapClick = false;
      suppressNextMapClickTimer = null;
    }, 800);
  }

  function startPmtilesHold(event) {
    if (event.button !== 0 || measurementActive || routeActive) return;
    if (!pmtilesEnabled || !activeRasters.size) return;
    cancelPmtilesHold();
    pmtilesHoldPointerId = event.pointerId;
    const canvasRect = map.getCanvas().getBoundingClientRect();
    const point = {
      x: event.clientX - canvasRect.left,
      y: event.clientY - canvasRect.top,
    };
    pmtilesHoldStart = {
      x: event.clientX,
      y: event.clientY,
      point,
      lngLat: map.unproject([point.x, point.y]),
    };
    pmtilesHoldTimer = window.setTimeout(() => {
      pmtilesHoldTimer = null;
      if (pmtilesHoldPointerId === null) return;
      if (!pmtilesEnabled) return;
      pmtilesPeekHidden = true;
      closeCoordinateMenu();
      applyPmtilesVisibility();
    }, PMTILES_HOLD_DELAY_MS);
  }

  function movePmtilesHold(event) {
    if (event.pointerId !== pmtilesHoldPointerId || pmtilesHoldTimer === null || !pmtilesHoldStart) return;
    const distance = Math.hypot(
      event.clientX - pmtilesHoldStart.x,
      event.clientY - pmtilesHoldStart.y);
    if (distance > PMTILES_HOLD_MOVE_TOLERANCE) cancelPmtilesHold();
  }

  function endPmtilesHold(event) {
    if (event.pointerId === pmtilesHoldPointerId) cancelPmtilesHold();
  }

  function closeCoordinateMenu() {
    coordinateMenu.hidden = true;
  }

  function openCoordinateMenuAt(point, lngLat) {
    updatePmtilesVisibilityToggle();
    const latitude = lngLat.lat;
    const longitude = lngLat.lng;
    const coordinateText = `${latitude.toFixed(5)}, ${longitude.toFixed(5)}`;
    coordinateValues.textContent = coordinateText;
    coordinateLink.href = `https://www.google.com/maps?q=${latitude.toFixed(6)},${longitude.toFixed(6)}`;
    coordinateLink.setAttribute("aria-label", `Open ${coordinateText} in Google Maps`);
    coordinateMenu.hidden = false;
    coordinateMenu.style.left = `${point.x + 8}px`;
    coordinateMenu.style.top = `${point.y + 8}px`;
    window.requestAnimationFrame(() => {
      const maxLeft = Math.max(8, mapShell.clientWidth - coordinateMenu.offsetWidth - 8);
      const maxTop = Math.max(8, mapShell.clientHeight - coordinateMenu.offsetHeight - 8);
      coordinateMenu.style.left = `${Math.max(8, Math.min(point.x + 8, maxLeft))}px`;
      coordinateMenu.style.top = `${Math.max(8, Math.min(point.y + 8, maxTop))}px`;
      coordinateLink.focus({ preventScroll: true });
    });
  }

  function openCoordinateMenu(event) {
    event.originalEvent.preventDefault();
    if (isMobileViewport()) suppressMapClickBriefly();
    openCoordinateMenuAt(event.point, event.lngLat);
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
      updateMeasurementLabel();
    });
  }

  function closePanel() {
    app.classList.remove("panel-open");
    panel.setAttribute("aria-hidden", "true");
    window.requestAnimationFrame(() => map.resize());
    window.setTimeout(() => {
      map.resize();
      updateLabels();
      updateMeasurementLabel();
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
    measureToggle.disabled = false;
    routeToggle.disabled = false;
    if (catalog) installCellLayer();
    createLabels();
    updateLabels();
    syncRasterToMap();
  });

  map.on("click", (event) => {
    if (suppressNextMapClick) {
      suppressNextMapClick = false;
      if (suppressNextMapClickTimer !== null) {
        window.clearTimeout(suppressNextMapClickTimer);
        suppressNextMapClickTimer = null;
      }
      return;
    }
    if (routeActive) {
      if (!event.originalEvent || event.originalEvent.detail < 2) {
        routePoints.push({ lng: event.lngLat.lng, lat: event.lngLat.lat });
        updateRoute();
      }
      return;
    }
    if (isMobileViewport()) {
      openCoordinateMenuAt(event.point, event.lngLat);
      return;
    }
    closeCoordinateMenu();
    if (measurementActive) addMeasurementPoint(event.lngLat);
    else closeDetails(false);
  });
  map.on("contextmenu", openCoordinateMenu);
  map.on("movestart", closeCoordinateMenu);
  map.on("mousemove", updateMeasurementPreview);
  map.on("move", () => {
    scheduleLabels();
    updateMeasurementLabel();
  });
  map.on("moveend", syncRasterToMap);
  map.on("zoom", () => {
    scheduleLabels();
    updateMeasurementLabel();
  });
  const mapCanvas = map.getCanvas();
  mapCanvas.addEventListener("pointerdown", startPmtilesHold);
  mapCanvas.addEventListener("pointermove", movePmtilesHold);
  mapCanvas.addEventListener("pointerleave", () => {
    if (pmtilesHoldTimer !== null) cancelPmtilesHold();
  });
  window.addEventListener("pointerup", endPmtilesHold, true);
  window.addEventListener("pointercancel", endPmtilesHold, true);
  window.addEventListener("blur", cancelPmtilesHold);

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
  measureToggle.addEventListener("click", () => {
    if (measurementActive) clearMeasurement();
    else startMeasurement();
  });
  measureClear.addEventListener("click", clearMeasurement);
  routeToggle.addEventListener("click", () => setRouteMode(!routeActive));
  routeUndo.addEventListener("click", () => { routePoints.pop(); updateRoute(); });
  routeClear.addEventListener("click", () => { routePoints = []; routeProfilePoints = []; updateRoute(); setRouteMode(false); });
  routeDownload.addEventListener("click", downloadRouteGpx);
  routeProfileExpand.addEventListener("click", () => {
    routeProfileDialog.show();
    routeProfile.classList.add("is-expanded");
    drawElevationProfile(routeProfilePoints);
  });
  routeProfileClose.addEventListener("click", () => routeProfileDialog.close());
  routeProfileDialog.addEventListener("close", () => {
    routeProfile.classList.remove("is-expanded");
    clearRouteProfileInspection();
  });
  for (const chart of routeProfileCharts) {
    chart.addEventListener("pointermove", (event) => inspectRouteProfile(chart, event));
    chart.addEventListener("pointerdown", (event) => inspectRouteProfile(chart, event));
    chart.addEventListener("click", (event) => inspectRouteProfile(chart, event));
    chart.addEventListener("pointerleave", clearRouteProfileInspection);
  }
  pmtilesVisibilityToggle.addEventListener("click", () => {
    setPmtilesEnabled(!pmtilesEnabled);
    closeCoordinateMenu();
  });
  document.addEventListener("pointerdown", (event) => {
    if (!coordinateMenu.hidden && !coordinateMenu.contains(event.target)) closeCoordinateMenu();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    cancelPmtilesHold();
    closeCoordinateMenu();
    if (routeProfileDialog.open) routeProfileDialog.close();
    if (measurementActive) clearMeasurement();
    closeDetails(true);
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
      updateMeasurementLabel();
      if (routeProfileDialog.open && routeProfilePoints.length > 1) drawElevationProfile(routeProfilePoints);
      syncRasterToMap();
    }, 120);
  });

  loadAtlas();
})();
