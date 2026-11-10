(() => {
  "use strict";

  /* -------------------------------------------------------------------------
   * TracciaBianca webmap — MapLibre GL JS + PMTiles viewer shell
   *
   * Mirrors the Leaflet docs/app.js visual language and UX (search, details
   * panel, checksum / download, status labels) but renders cell polygons as a
   * MapLibre GeoJSON overlay and, on demand, the published sheet's converted
   * PMTiles as a raster source via the pmtiles `Protocol` API.
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
  const pmtilesManifestUrl = typeof config.pmtilesManifest === "string"
    ? config.pmtilesManifest : "./pmtiles-manifest.json";

  function resolveEnvironment() {
    if (config.env === "dev" || config.env === "publish") return config.env;
    const localHosts = new Set(["localhost", "127.0.0.1", "::1", "[::1]"]);
    return localHosts.has(window.location.hostname) ? "dev" : "publish";
  }

  const environment = resolveEnvironment();
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
  const geocoderCache = new Map();
  const cellsById = new Map();
  const availablePmtiles = new Map();
  const labelEls = new Map();
  let protocolRegistered = false;
  let pmtilesProtocol = null;
  let rasterRequestId = 0;
  let activeRaster = null;

  const ACTIVE_RASTER_SOURCE = "active-pmtiles";
  const ACTIVE_RASTER_LAYER = "active-pmtiles-layer";

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

  function focusSearchResult(cell) {
    clearSearchFeedback();
    selectCell(cell.id, false);
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
    if (!normalized) return [];
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
      if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
      const cell = cellForCoordinate(lat, lon);
      if (cell) matches.push({ cell, label: place.display_name || query.trim() });
    }
    const unique = [...new Map(matches.map((match) => [match.cell.id, match])).values()];
    geocoderCache.set(normalized, unique);
    return unique;
  }

  function renderSearchResults(results, query) {
    clearSearchFeedback();
    if (!results.length) {
      searchMessage.textContent = "Not available in this atlas.";
      searchMessage.hidden = false;
      return;
    }
    if (results.length === 1) {
      focusSearchResult(results[0].cell);
      return;
    }
    for (const { cell, label } of results.slice(0, 5)) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "search-result";
      button.setAttribute("role", "option");
      button.innerHTML = "<strong></strong><span></span>";
      button.querySelector("strong").textContent = label;
      button.querySelector("span").textContent = `${cell.id} · ${cell.locality}`;
      button.addEventListener("click", () => focusSearchResult(cell));
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
      renderSearchResults(local.map((r) => ({ cell: r.cell, label: r.cell.display_name })), query);
      return;
    }
    // Fall back to Nominatim (needs network).
    searchMessage.textContent = "Searching OpenStreetMap…";
    searchMessage.hidden = false;
    try {
      const results = await geocodePlace(query);
      renderSearchResults(results, query);
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

  function removeActiveRaster() {
    if (map.getLayer(ACTIVE_RASTER_LAYER)) map.removeLayer(ACTIVE_RASTER_LAYER);
    if (map.getSource(ACTIVE_RASTER_SOURCE)) map.removeSource(ACTIVE_RASTER_SOURCE);
    activeRaster = null;
  }

  function cancelRasterLoad({ remove = false } = {}) {
    rasterRequestId += 1;
    if (remove && mapLoaded) removeActiveRaster();
  }

  async function loadCellRaster(cell) {
    const requestId = ++rasterRequestId;
    if (!cell || cell.status !== "published") {
      if (mapLoaded) removeActiveRaster();
      setTilesNote("hidden");
      return;
    }
    const hasEngine = typeof window.pmtiles !== "undefined" && window.pmtiles.PMTiles;
    const resource = availablePmtiles.get(cell.id);
    const absUrl = pmtilesUrlFor(cell);
    if (!resource || !absUrl || !hasEngine || !ensureProtocol()) {
      if (mapLoaded) removeActiveRaster();
      setTilesNote("unavailable",
        environment === "publish" && !pmtilesBase
          ? `PMTiles publishing is not configured yet for ${cell.id}. The base map and details remain available.`
          : `PMTiles not available yet for ${cell.id}. Add the converted archive to the configured tile directory; the base map and details remain available.`);
      return;
    }
    try {
      if (activeRaster && activeRaster.url === absUrl) {
        setTilesNote("ready", `PMTiles loaded for ${cell.id}.`);
        return;
      }

      if (mapLoaded) removeActiveRaster();
      setTilesNote("loading", `Loading PMTiles for ${cell.id}…`);
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
      if (requestId !== rasterRequestId || !selectedCell || selectedCell.id !== cell.id) return;

      const catalogZoom = Array.isArray(cell.zoom) && cell.zoom.every(Number.isFinite)
        ? cell.zoom : [12, 16];
      const minzoom = Number.isFinite(header.minZoom) ? header.minZoom : catalogZoom[0];
      const maxzoom = Number.isFinite(header.maxZoom) ? header.maxZoom : catalogZoom[1];
      removeActiveRaster();
      map.addSource(ACTIVE_RASTER_SOURCE, {
        type: "raster",
        tiles: [`pmtiles://${absUrl}/{z}/{x}/{y}`],
        tileSize: 256,
        minzoom,
        maxzoom,
      });
      const before = map.getLayer("cells-line") ? "cells-line" : undefined;
      map.addLayer({
        id: ACTIVE_RASTER_LAYER,
        type: "raster",
        source: ACTIVE_RASTER_SOURCE,
      }, before);
      activeRaster = { cellId: cell.id, url: absUrl };
      console.info(`PMTiles ready for ${cell.id} (z${minzoom}–${maxzoom}).`);
      setTilesNote("ready", `PMTiles loaded for ${cell.id}.`);
    } catch (error) {
      if (requestId !== rasterRequestId || !selectedCell || selectedCell.id !== cell.id) return;
      if (mapLoaded) removeActiveRaster();
      console.info(`PMTiles unavailable for ${cell.id}:`, error);
      setTilesNote("error",
        `PMTiles not available yet for ${cell.id}. The base map and details still work; ` +
        `add or verify the converted archive and select the cell again to retry.`);
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
    window.requestAnimationFrame(() => map.resize());
  }

  function closePanel() {
    app.classList.remove("panel-open");
    panel.setAttribute("aria-hidden", "true");
    window.requestAnimationFrame(() => map.resize());
    window.setTimeout(() => {
      map.resize();
      updateLabels();
    }, 240);
  }

  function selectCell(cellId, moveFocus = false) {
    const cell = cellsById.get(cellId);
    if (!cell) return;
    if (selectedCell && selectedCell.id !== cell.id) setFeatureSelected(selectedCell.id, false);
    selectedCell = cell;
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
    void loadCellRaster(cell);
    if (moveFocus) window.setTimeout(() => closePanelButton.focus(), 60);
  }

  function closeDetails(returnFocus = true) {
    if (!app.classList.contains("panel-open")) return;
    if (selectedCell) setFeatureSelected(selectedCell.id, false);
    cancelRasterLoad({ remove: true });
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
    }, 120);
  });

  loadAtlas();
})();
