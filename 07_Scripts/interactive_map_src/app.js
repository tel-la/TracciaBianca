(() => {
  "use strict";

  const app = document.getElementById("app");
  const loadingState = document.getElementById("loading-state");
  const errorState = document.getElementById("error-state");
  const summary = document.getElementById("atlas-summary");
  const panel = document.getElementById("details-panel");
  const closePanelButton = document.getElementById("close-panel");
  const downloadButton = document.getElementById("download-button");
  const elevationDownloadButton = document.getElementById("elevation-download-button");
  const unavailableMessage = document.getElementById("unavailable-message");
  const checksumBlock = document.getElementById("checksum-block");
  const copyChecksumButton = document.getElementById("copy-checksum");
  const copyFeedback = document.getElementById("copy-feedback");
  const placeSearch = document.getElementById("place-search");
  const placeSearchInput = document.getElementById("place-search-input");
  const searchMessage = document.getElementById("search-message");
  const searchResults = document.getElementById("search-results");
  const hillshadeToggle = document.getElementById("hillshade-toggle");
  const terrainStatus = document.getElementById("terrain-status");
  const NOMINATIM_URL = "https://nominatim.openstreetmap.org/search";
  const MAPTERHORN_TILEJSON = "https://tiles.mapterhorn.com/tilejson.json";

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

  function installSmoothWheelZoom(targetMap) {
    const container = targetMap.getContainer();
    const smoothingTime = 40;
    const wheelDeltaPerZoom = 40;
    let targetZoom = targetMap.getZoom();
    let anchorPoint = null;
    let anchorLatLng = null;
    let animationFrame = null;
    let previousFrameTime = null;
    let moving = false;

    function clampZoom(zoom) {
      return Math.max(targetMap.getMinZoom(), Math.min(targetMap.getMaxZoom(), zoom));
    }

    function moveAroundAnchor(zoom) {
      const halfSize = targetMap.getSize().divideBy(2);
      const centerPoint = targetMap.project(anchorLatLng, zoom)
        .subtract(anchorPoint.subtract(halfSize));
      let center = targetMap.unproject(centerPoint, zoom);
      if (targetMap.options.maxBounds) {
        center = targetMap._limitCenter(center, zoom, targetMap.options.maxBounds);
      }
      targetMap._move(center, zoom, { pinch: true, wheel: true, round: false });
    }

    function finishZoom() {
      moveAroundAnchor(targetZoom);
      animationFrame = null;
      previousFrameTime = null;
      if (moving) {
        moving = false;
        targetMap._moveEnd(true);
      }
    }

    function animateZoom(frameTime) {
      animationFrame = null;
      const currentZoom = targetMap.getZoom();
      const remaining = targetZoom - currentZoom;
      if (Math.abs(remaining) < 0.001) {
        finishZoom();
        return;
      }

      const elapsed = previousFrameTime === null
        ? 16
        : Math.min(32, frameTime - previousFrameTime);
      previousFrameTime = frameTime;
      const progress = 1 - Math.exp(-elapsed / smoothingTime);
      moveAroundAnchor(currentZoom + remaining * progress);
      animationFrame = window.requestAnimationFrame(animateZoom);
    }

    function onWheel(event) {
      const wheelDelta = L.DomEvent.getWheelDelta(event);
      if (!wheelDelta) return;
      L.DomEvent.stop(event);

      const currentZoom = targetMap.getZoom();
      const baseZoom = moving ? targetZoom : currentZoom;
      const requestedDelta = Math.max(-1.5, Math.min(1.5, wheelDelta / wheelDeltaPerZoom));
      const requestedZoom = clampZoom(baseZoom + requestedDelta);
      if (!moving && requestedZoom === currentZoom) return;

      anchorPoint = targetMap.mouseEventToContainerPoint(event);
      anchorLatLng = targetMap.containerPointToLatLng(anchorPoint);
      targetZoom = clampZoom(Math.max(currentZoom - 2, Math.min(currentZoom + 2, requestedZoom)));

      if (!moving) {
        targetMap._stop();
        targetMap._moveStart(true, false);
        moving = true;
      }
      if (animationFrame === null) {
        previousFrameTime = null;
        animationFrame = window.requestAnimationFrame(animateZoom);
      }
    }

    L.DomEvent.on(container, "wheel", onWheel);
  }

  const map = L.map("map", {
    zoomControl: true,
    attributionControl: true,
    keyboard: true,
    scrollWheelZoom: false,
    touchZoom: true,
    bounceAtZoomLimits: false,
    maxBoundsViscosity: 1,
    zoomSnap: 0,
    zoomDelta: 0.5,
  }).setView([46.25, 10.8], 7);

  installSmoothWheelZoom(map);

  map.attributionControl.setPosition("bottomright");
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    minZoom: 0,
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors',
  }).addTo(map);
  map.createPane("hillshadePane");
  map.getPane("hillshadePane").style.zIndex = "250";
  map.getPane("hillshadePane").style.pointerEvents = "none";

  let catalog;
  let atlasBounds;
  let selectedLayer = null;
  let selectedCell = null;
  let resizeTimer = null;
  let lastGeocoderRequest = 0;
  let hillshadeLayer = null;
  let hillshadeLayerPromise = null;
  let hillshadeEnabled = false;
  let hillshadeLoadCycle = { loaded: 0, failed: 0 };
  const geocoderCache = new Map();
  const cellsById = new Map();
  const layersById = new Map();
  const labels = [];
  const labelContext = document.createElement("canvas").getContext("2d");

  const statusLabels = {
    published: "Available",
    release_ready: "Planned",
    validation_pending: "Validation pending",
    prepared: "In preparation",
    blocked: "Temporarily unavailable",
    planned: "Planned",
  };

  function setTerrainStatus(message = "", isError = false) {
    terrainStatus.textContent = message;
    terrainStatus.hidden = !message;
    terrainStatus.classList.toggle("is-error", isError);
  }

  function setHillshadeBusy(busy) {
    hillshadeToggle.disabled = busy;
    hillshadeToggle.setAttribute("aria-busy", String(busy));
  }

  function updateHillshadeToggle() {
    hillshadeToggle.setAttribute("aria-pressed", String(hillshadeEnabled));
  }

  function terrainTileTemplates(tilejson) {
    if (!Array.isArray(tilejson.tiles) || !tilejson.tiles.length) {
      throw new Error("Mapterhorn TileJSON has no tile endpoints");
    }
    return tilejson.tiles.map((template) => new URL(template, MAPTERHORN_TILEJSON).href
      .replace(/%7B([a-z0-9_-]+)%7D/gi, "{$1}"));
  }

  function terrainTileUrl(template, coords, scheme) {
    const y = scheme === "tms" ? (2 ** coords.z) - coords.y - 1 : coords.y;
    return template.replace("{z}", coords.z).replace("{x}", coords.x).replace("{y}", y);
  }

  function renderHillshadeTile(tile, image, coords) {
    const sourceWidth = image.naturalWidth || image.width;
    const sourceHeight = image.naturalHeight || image.height;
    if (!sourceWidth || !sourceHeight) throw new Error("Empty Mapterhorn terrain tile");

    const sourceCanvas = document.createElement("canvas");
    sourceCanvas.width = sourceWidth;
    sourceCanvas.height = sourceHeight;
    const sourceContext = sourceCanvas.getContext("2d", { willReadFrequently: true });
    sourceContext.drawImage(image, 0, 0);
    const source = sourceContext.getImageData(0, 0, sourceWidth, sourceHeight).data;

    const outputSize = 256;
    tile.width = outputSize;
    tile.height = outputSize;
    const outputContext = tile.getContext("2d");
    const outputImage = outputContext.createImageData(outputSize, outputSize);
    const output = outputImage.data;
    const sampleStepX = Math.max(1, Math.round(sourceWidth / outputSize));
    const sampleStepY = Math.max(1, Math.round(sourceHeight / outputSize));
    const worldTiles = 2 ** coords.z;
    const tileCenterY = (coords.y + 0.5) / worldTiles;
    const latitude = Math.atan(Math.sinh(Math.PI * (1 - 2 * tileCenterY)));
    const metersPerSourcePixel = (2 * Math.PI * 6378137 * Math.cos(latitude))
      / (worldTiles * sourceWidth);
    const lightAzimuth = 315 * Math.PI / 180;
    const lightAltitude = 45 * Math.PI / 180;
    const lightHorizontal = Math.cos(lightAltitude);
    const lightEast = Math.sin(lightAzimuth) * lightHorizontal;
    const lightSouth = -Math.cos(lightAzimuth) * lightHorizontal;
    const lightUp = Math.sin(lightAltitude);
    const contrastBoost = 1.885;

    function elevationAt(x, y) {
      const index = (y * sourceWidth + x) * 4;
      if (source[index + 3] === 0) return null;
      return source[index] * 256 + source[index + 1] + source[index + 2] / 256 - 32768;
    }

    for (let y = 0; y < outputSize; y += 1) {
      const sourceY = Math.min(sourceHeight - 1, Math.floor((y + 0.5) * sourceHeight / outputSize));
      const northY = Math.max(0, sourceY - sampleStepY);
      const southY = Math.min(sourceHeight - 1, sourceY + sampleStepY);
      for (let x = 0; x < outputSize; x += 1) {
        const sourceX = Math.min(sourceWidth - 1, Math.floor((x + 0.5) * sourceWidth / outputSize));
        const westX = Math.max(0, sourceX - sampleStepX);
        const eastX = Math.min(sourceWidth - 1, sourceX + sampleStepX);
        const west = elevationAt(westX, sourceY);
        const east = elevationAt(eastX, sourceY);
        const north = elevationAt(sourceX, northY);
        const south = elevationAt(sourceX, southY);
        if (west === null || east === null || north === null || south === null) continue;

        const dzdx = (east - west) / ((eastX - westX) * metersPerSourcePixel);
        const dzdy = (south - north) / ((southY - northY) * metersPerSourcePixel);
        const normalLength = Math.sqrt(dzdx * dzdx + dzdy * dzdy + 1);
        const illumination = ((-dzdx * lightEast) + (-dzdy * lightSouth) + lightUp)
          / normalLength;
        const contrast = illumination - lightUp;
        const outputIndex = (y * outputSize + x) * 4;
        if (contrast < 0) {
          output[outputIndex] = 63;
          output[outputIndex + 1] = 57;
          output[outputIndex + 2] = 45;
          output[outputIndex + 3] = Math.min(255, Math.round(-contrast * 210 * contrastBoost));
        } else {
          output[outputIndex] = 255;
          output[outputIndex + 1] = 255;
          output[outputIndex + 2] = 255;
          output[outputIndex + 3] = Math.min(136, Math.round(contrast * 120 * contrastBoost));
        }
      }
    }
    outputContext.putImageData(outputImage, 0, 0);
  }

  function createHillshadeLayer(tilejson) {
    const templates = terrainTileTemplates(tilejson);
    const scheme = tilejson.scheme === "tms" ? "tms" : "xyz";
    const attribution = typeof tilejson.attribution === "string" && tilejson.attribution.trim()
      ? tilejson.attribution
      : '<a href="https://mapterhorn.com/attribution" target="_blank" rel="noopener">© Mapterhorn</a>';
    const options = {
      attribution,
      pane: "hillshadePane",
      tileSize: 256,
      opacity: 1,
      updateWhenZooming: false,
      keepBuffer: 1,
    };
    if (Number.isFinite(Number(tilejson.minzoom))) options.minNativeZoom = Number(tilejson.minzoom);
    if (Number.isFinite(Number(tilejson.maxzoom))) options.maxNativeZoom = Number(tilejson.maxzoom);
    if (Array.isArray(tilejson.bounds) && tilejson.bounds.length === 4) {
      options.bounds = L.latLngBounds(
        [Number(tilejson.bounds[1]), Number(tilejson.bounds[0])],
        [Number(tilejson.bounds[3]), Number(tilejson.bounds[2])],
      );
    }

    const HillshadeGrid = L.GridLayer.extend({
      createTile(coords, done) {
        const tile = document.createElement("canvas");
        const template = templates[Math.abs(coords.x + coords.y) % templates.length];
        const image = new Image();
        image.crossOrigin = "anonymous";
        image.decoding = "async";
        image.onload = () => {
          window.setTimeout(() => {
            try {
              renderHillshadeTile(tile, image, coords);
              done(null, tile);
            } catch (error) {
              done(error, tile);
            }
          }, 0);
        };
        image.onerror = () => done(new Error("Mapterhorn terrain tile failed to load"), tile);
        image.src = terrainTileUrl(template, coords, scheme);
        tile._hillshadeImage = image;
        return tile;
      },
    });
    return new HillshadeGrid(options);
  }

  function watchHillshadeAvailability(layer) {
    layer.on("loading", () => {
      hillshadeLoadCycle = { loaded: 0, failed: 0 };
    });
    layer.on("tileload", () => {
      hillshadeLoadCycle.loaded += 1;
    });
    layer.on("tileerror", () => {
      hillshadeLoadCycle.failed += 1;
    });
    layer.on("load", () => {
      if (!hillshadeEnabled || !hillshadeLoadCycle.failed) {
        if (hillshadeEnabled) setTerrainStatus();
        return;
      }
      if (hillshadeLoadCycle.loaded) {
        setTerrainStatus("Some terrain tiles are unavailable; OSM remains visible.", true);
        return;
      }
      map.removeLayer(layer);
      hillshadeEnabled = false;
      updateHillshadeToggle();
      setTerrainStatus("Mapterhorn is temporarily unavailable; OSM remains active.", true);
    });
  }

  async function ensureHillshadeLayer() {
    if (hillshadeLayer) return hillshadeLayer;
    if (hillshadeLayerPromise) return hillshadeLayerPromise;
    hillshadeLayerPromise = (async () => {
      setHillshadeBusy(true);
      setTerrainStatus("Loading Mapterhorn hillshade…");
      const response = await fetch(MAPTERHORN_TILEJSON, {
        cache: "force-cache",
        credentials: "omit",
      });
      if (!response.ok) throw new Error(`Mapterhorn TileJSON request failed (${response.status})`);
      const tilejson = await response.json();
      if (tilejson.encoding && tilejson.encoding !== "terrarium") {
        throw new Error(`Unsupported Mapterhorn encoding: ${tilejson.encoding}`);
      }
      hillshadeLayer = createHillshadeLayer(tilejson || {});
      watchHillshadeAvailability(hillshadeLayer);
      return hillshadeLayer;
    })().catch((error) => {
      console.warn(error);
      hillshadeLayerPromise = null;
      setTerrainStatus("Mapterhorn is temporarily unavailable; OSM remains active.", true);
      return null;
    }).finally(() => {
      setHillshadeBusy(false);
    });
    return hillshadeLayerPromise;
  }

  async function setHillshadeEnabled(enabled) {
    const next = Boolean(enabled);
    if (next) {
      const layer = await ensureHillshadeLayer();
      if (!layer) return false;
      hillshadeEnabled = true;
      updateHillshadeToggle();
      if (!map.hasLayer(layer)) layer.addTo(map);
      return true;
    }
    if (hillshadeLayer && map.hasLayer(hillshadeLayer)) map.removeLayer(hillshadeLayer);
    hillshadeEnabled = false;
    updateHillshadeToggle();
    setTerrainStatus();
    return true;
  }

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
    if (!normalized) return [];
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
    const layer = layersById.get(cell.id);
    if (!layer) return;
    clearSearchFeedback();
    selectCell(cell.id, layer, false);
    window.setTimeout(() => {
      const cellZoom = map.getBoundsZoom(layer.getBounds(), false, L.point(26, 26));
      const targetZoom = Math.max(map.getMinZoom(), Math.min(map.getMaxZoom(), cellZoom - 1));
      map.setView(layer.getCenter(), targetZoom, { animate: true });
    }, 250);
  }

  function cellForCoordinate(lat, lon) {
    const point = L.latLng(lat, lon);
    const match = catalog.cells.find((cell) => {
      const bounds = L.latLngBounds(cell.analysis_bounds);
      return bounds.contains(point);
    });
    return match || null;
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
      button.innerHTML = `<strong></strong><span></span>`;
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

  function wrappedLineCount(text, width) {
    if (!labelContext) return Infinity;
    labelContext.font = '10px Inter, ui-sans-serif, system-ui, sans-serif';
    let lines = 1;
    let current = "";
    for (const word of text.split(/\s+/)) {
      if (labelContext.measureText(word).width > width) return Infinity;
      const candidate = current ? `${current} ${word}` : word;
      if (labelContext.measureText(candidate).width <= width) {
        current = candidate;
      } else {
        lines += 1;
        current = word;
      }
    }
    return lines;
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

  function cellStyle(cell, isSelected = false) {
    if (isSelected) {
      return { color: "#f8fafc", weight: 5, opacity: 1, fillColor: "#2a82b3", fillOpacity: 0.48, bubblingMouseEvents: false };
    }
    if (cell.status === "published") {
      return { color: "#145b83", weight: 2, opacity: 0.96, fillColor: "#2a82b3", fillOpacity: 0.31, bubblingMouseEvents: false };
    }
    return { color: "#6d8ca1", weight: 1.7, opacity: 0.92, fillColor: "#c9e1f1", fillOpacity: 0.23, bubblingMouseEvents: false };
  }

  function createLabel(cell, featureLayer) {
    const bounds = featureLayer.getBounds();
    const label = document.createElement("div");
    label.className = "cell-label";

    const compact = document.createElement("span");
    compact.className = "compact";
    compact.textContent = compactId(cell.id);

    const detailed = document.createElement("span");
    detailed.className = "detailed";
    const identifier = document.createElement("strong");
    identifier.textContent = compactId(cell.id);
    const locality = document.createElement("span");
    locality.textContent = cell.locality;
    detailed.append(identifier, locality);
    label.append(compact, detailed);

    const marker = L.marker(bounds.getCenter(), {
      interactive: false,
      keyboard: false,
      icon: L.divIcon({
        className: "cell-label-wrapper",
        html: label,
        iconSize: [0, 0],
        iconAnchor: [0, 0],
      }),
    }).addTo(map);
    featureLayer.on("add", () => marker.setLatLng(featureLayer.getCenter()));
    labels.push({ marker, label, bounds, cell, identifier });
  }

  function updateLabels() {
    for (const item of labels) {
      const northWest = map.latLngToContainerPoint(item.bounds.getNorthWest());
      const southEast = map.latLngToContainerPoint(item.bounds.getSouthEast());
      const width = Math.abs(southEast.x - northWest.x);
      const height = Math.abs(southEast.y - northWest.y);
      const contentWidth = Math.max(8, Math.floor(width * 0.82));
      const contentHeight = Math.max(8, Math.floor(height * 0.88));
      const compactFont = Math.max(3, Math.min(9, width / 3.2, height / 3.3));
      item.label.style.setProperty("--label-width", `${contentWidth}px`);
      item.label.style.setProperty("--compact-font-size", `${compactFont.toFixed(2)}px`);
      if (labelContext) labelContext.font = '800 9px Inter, ui-sans-serif, system-ui, sans-serif';
      const idInlineFits = Boolean(labelContext) && labelContext.measureText(displayId(item.cell.id)).width + 2 <= contentWidth;
      const idStackedFits = Boolean(labelContext) && compactId(item.cell.id).split("\n")
        .every((line) => labelContext.measureText(line).width + 2 <= contentWidth);
      item.identifier.textContent = idInlineFits ? displayId(item.cell.id) : compactId(item.cell.id);
      const localityLines = wrappedLineCount(item.cell.locality, contentWidth);
      const idLines = idInlineFits ? 1 : 3;
      const detailedFits = idStackedFits && localityLines <= 3
        && idLines * 9 + 3 + localityLines * 11 <= contentHeight;
      item.label.classList.toggle("is-detailed", detailedFits);
    }
  }

  function setLayerAccessibility(layer, cell) {
    const element = layer.getElement();
    if (!element) return;
    element.classList.add("map-sheet");
    element.setAttribute("tabindex", "0");
    element.setAttribute("role", "button");
    element.setAttribute("aria-label", `${cell.id}, ${cell.locality}, ${statusLabels[cell.status] || "In preparation"}`);
    element.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        selectCell(cell.id, layer, true);
      }
    });
  }

  function packageFor(cell) {
    return Array.isArray(cell.packages) && cell.packages.length ? cell.packages[0] : null;
  }

  function showDetails(cell) {
    const pack = packageFor(cell);
    const elevation = cell.elevation_package || null;
    const downloadable = cell.status === "published" && pack && pack.download_url;
    const elevationDownloadable = cell.status === "published" && elevation && elevation.download_url;
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
      downloadButton.setAttribute("aria-label", `Download ${cell.id} MBTiles, ${formatBytes(pack.bytes)}; opens in a new tab`);
    } else {
      downloadButton.removeAttribute("href");
      downloadButton.removeAttribute("aria-label");
      unavailableMessage.textContent = "Download not available yet. This map sheet is still being prepared.";
    }
    elevationDownloadButton.hidden = !elevationDownloadable;
    if (elevationDownloadable) {
      elevationDownloadButton.href = elevation.download_url;
      elevationDownloadButton.firstChild.textContent = `Download elevation DEM · ${formatBytes(elevation.bytes)} `;
      elevationDownloadButton.setAttribute("aria-label", `Download ${cell.id} elevation DEM, ${formatBytes(elevation.bytes)}; opens in a new tab`);
    } else {
      elevationDownloadButton.removeAttribute("href");
      elevationDownloadButton.removeAttribute("aria-label");
    }
  }

  function selectCell(cellId, layer, moveFocus = false) {
    const cell = cellsById.get(cellId);
    if (!cell) return;
    if (selectedLayer && selectedCell) selectedLayer.setStyle(cellStyle(selectedCell));
    selectedCell = cell;
    selectedLayer = layer;
    selectedLayer.setStyle(cellStyle(cell, true));
    selectedLayer.bringToFront();
    showDetails(cell);
    app.classList.add("panel-open");
    panel.setAttribute("aria-hidden", "false");
    window.setTimeout(() => {
      const wasOverview = map.getZoom() <= map.getMinZoom() + 0.25;
      map.invalidateSize({ pan: false });
      recalculateMapLimits(wasOverview);
      updateLabels();
      if (moveFocus) closePanelButton.focus();
    }, 240);
  }

  function closeDetails(returnFocus = true) {
    if (!app.classList.contains("panel-open")) return;
    app.classList.remove("panel-open");
    panel.setAttribute("aria-hidden", "true");
    if (selectedLayer && selectedCell) selectedLayer.setStyle(cellStyle(selectedCell));
    const focusTarget = selectedLayer && selectedLayer.getElement();
    selectedLayer = null;
    selectedCell = null;
    window.setTimeout(() => {
      const wasOverview = map.getZoom() <= map.getMinZoom() + 0.25;
      map.invalidateSize({ pan: false });
      recalculateMapLimits(wasOverview);
      updateLabels();
      if (returnFocus && focusTarget) focusTarget.focus();
    }, 240);
  }

  function recalculateMapLimits(fitInitial) {
    if (!catalog || !atlasBounds || map.getSize().x < 1 || map.getSize().y < 1) return;
    map.setMinZoom(0);
    map.setMaxZoom(19);
    const minZoom = map.getBoundsZoom(atlasBounds, false, L.point(48, 48));
    const referenceZooms = catalog.cells.map((cell) =>
      map.getBoundsZoom(L.latLngBounds(cell.analysis_bounds), false, L.point(26, 26))
    );
    const maxZoom = Math.max(minZoom, Math.min(...referenceZooms));
    map.setMinZoom(minZoom);
    map.setMaxZoom(maxZoom);
    map.setMaxBounds(atlasBounds.pad(0.08));
    if (fitInitial) {
      map.fitBounds(atlasBounds, { padding: [24, 24], animate: false });
    } else {
      if (map.getZoom() < minZoom) map.setZoom(minZoom, { animate: false });
      if (map.getZoom() > maxZoom) map.setZoom(maxZoom, { animate: false });
      map.panInsideBounds(atlasBounds.pad(0.08), { animate: false });
    }
  }

  function installCellLayer(cores) {
    const layer = L.geoJSON(cores, {
      style: (feature) => cellStyle(cellsById.get(feature.properties.cell_id)),
      onEachFeature: (feature, featureLayer) => {
        const cell = cellsById.get(feature.properties.cell_id);
        if (!cell) throw new Error(`Unknown map sheet ${feature.properties.cell_id}`);
        layersById.set(cell.id, featureLayer);
        featureLayer.options.bubblingMouseEvents = false;
        const tooltip = document.createElement("span");
        tooltip.textContent = `${cell.id} · ${cell.locality}`;
        featureLayer.bindTooltip(tooltip, { sticky: true, direction: "top", opacity: 0.96 });
        featureLayer.on({
          add: () => setLayerAccessibility(featureLayer, cell),
          click: (event) => {
            L.DomEvent.stopPropagation(event.originalEvent);
            selectCell(cell.id, featureLayer, false);
          },
          mouseover: () => {
            if (featureLayer !== selectedLayer) featureLayer.setStyle({ weight: 3, fillOpacity: cell.status === "published" ? 0.41 : 0.31 });
          },
          mouseout: () => {
            if (featureLayer !== selectedLayer) featureLayer.setStyle(cellStyle(cell));
          },
        });
        createLabel(cell, featureLayer);
      },
    }).addTo(map);
    atlasBounds = layer.getBounds();
  }

  async function loadAtlas() {
    try {
      const [catalogResponse, coresResponse] = await Promise.all([
        fetch("./data/atlas.json", { cache: "no-cache" }),
        fetch("./data/cores.geojson", { cache: "no-cache" }),
      ]);
      if (!catalogResponse.ok || !coresResponse.ok) throw new Error("Atlas data request failed");
      catalog = await catalogResponse.json();
      const cores = await coresResponse.json();
      if (!Array.isArray(catalog.cells) || !catalog.cells.length || catalog.cells.length !== catalog.cell_count ||
          !Array.isArray(cores.features) || cores.features.length !== catalog.cell_count) {
        throw new Error("Unexpected atlas catalogue");
      }
      for (const cell of catalog.cells) cellsById.set(cell.id, cell);
      installCellLayer(cores);
      recalculateMapLimits(true);
      updateLabels();
      summary.textContent = `${catalog.cell_count} map sheets · ${catalog.published_count} available`;
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
  hillshadeToggle.addEventListener("click", () => {
    void setHillshadeEnabled(!hillshadeEnabled);
  });
  map.on("click", () => closeDetails(false));
  map.on("zoomend moveend", updateLabels);
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
      const wasOverview = Boolean(catalog) && map.getZoom() <= map.getMinZoom() + 0.25;
      map.invalidateSize({ pan: false });
      recalculateMapLimits(wasOverview);
      updateLabels();
    }, 120);
  });

  void setHillshadeEnabled(true);
  loadAtlas();
})();
