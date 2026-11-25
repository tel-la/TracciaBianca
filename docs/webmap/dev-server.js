#!/usr/bin/env node
"use strict";

/*
 * TracciaBianca webmap — dev-time static server
 * ---------------------------------------------------------------------------
 * Zero-dependency Node server (built-ins only: http, fs, path, url). It serves
 * the parent `docs/` directory as the web root so that BOTH the viewer
 * (http://localhost:PORT/webmap/) and the shared catalog it fetches
 * (http://localhost:PORT/data/atlas.json, /data/cores.geojson) resolve.
 *
 * It implements HTTP Range requests, which PMTiles needs for its sparse /
 * partial reads (a full .pmtiles can be hundreds of MB).
 *
 * Usage:
 *   node docs/webmap/dev-server.js
 *   node docs/webmap/dev-server.js --pmtiles=r2
 *   node docs/webmap/dev-server.js --pmtiles=local
 *   PORT=9000 node docs/webmap/dev-server.js
 *
 * Then open http://localhost:8080/webmap/  (drop converted .pmtiles into
 * docs/webmap/tiles/ for the dev tile source).
 */

const http = require("http");
const fs = require("fs");
const path = require("path");
const { Readable } = require("stream");
const vm = require("vm");

// Root = the docs/ directory (the parent of this webmap/ folder) so that
// /webmap/ and /data/ are both reachable.
const ROOT = path.resolve(__dirname, "..");
const HOST = process.env.HOST || "127.0.0.1";

function parseServerArgs(args, envPort = process.env.PORT) {
  let pmtiles = "local";
  let port = envPort ? Number(envPort) : 8080;
  for (const arg of args) {
    if (arg === "--pmtiles=r2" || arg === "--pmtiles=local") {
      pmtiles = arg.slice("--pmtiles=".length);
    } else if (/^\d+$/.test(arg) && !envPort) {
      port = Number(arg);
    } else {
      throw new Error(`Unknown server option: ${arg}. Use --pmtiles=local or --pmtiles=r2.`);
    }
  }
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error(`Invalid port: ${envPort || port}`);
  }
  return { port, pmtiles };
}

function r2Config(root) {
  const sandbox = { window: {} };
  vm.runInNewContext(fs.readFileSync(path.join(root, "webmap", "config.js"), "utf8"), sandbox);
  const config = sandbox.window.TB_CONFIG;
  const base = new URL(config.pmtilesBases.publish);
  const manifest = new URL(config.pmtilesManifests.publish);
  if (base.protocol !== "https:" || manifest.protocol !== "https:") {
    throw new Error("R2 URLs in webmap/config.js must use HTTPS");
  }
  return { base, manifest };
}

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".geojson": "application/geo+json; charset=utf-8",
  ".pmtiles": "application/octet-stream",
  ".mbtiles": "application/octet-stream",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".svg": "image/svg+xml",
  ".gif": "image/gif",
  ".ico": "image/x-icon",
  ".mp4": "video/mp4",
  ".webm": "video/webm",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".ttf": "font/ttf",
  ".txt": "text/plain; charset=utf-8",
  ".map": "application/json; charset=utf-8",
};

function send(req, res, code, body, headers = {}) {
  res.writeHead(code, headers);
  res.end(req.method === "HEAD" ? undefined : body);
}

function notFound(req, res) {
  send(req, res, 404, "Not found", { "content-type": "text/plain; charset=utf-8" });
}

// Resolve a request path to a safe file inside ROOT (block traversal).
function safePath(requestPath, root = ROOT) {
  // Strip query / hash, decode, and normalize. Reject anything that escapes ROOT.
  let pathname;
  try {
    pathname = decodeURIComponent(requestPath.split("?")[0].split("#")[0]);
  } catch (_e) {
    return null;
  }
  if (pathname.startsWith("/") === false) pathname = `/${pathname}`;
  const resolved = path.normalize(path.join(root, pathname)).replace(/\\/g, "/");
  if (resolved !== root && !resolved.startsWith(root + path.sep)) return null;
  return resolved;
}

function mimeFor(filePath) {
  return MIME[path.extname(filePath).toLowerCase()] || "application/octet-stream";
}

function parseRange(value, total) {
  if (!value || !Number.isSafeInteger(total) || total <= 0) return null;
  const match = /^bytes=(\d*)-(\d*)$/.exec(value.trim());
  if (!match || (!match[1] && !match[2])) return null;

  let start;
  let end;
  if (!match[1]) {
    const suffixLength = Number(match[2]);
    if (!Number.isSafeInteger(suffixLength) || suffixLength <= 0) return null;
    start = Math.max(0, total - suffixLength);
    end = total - 1;
  } else {
    start = Number(match[1]);
    end = match[2] ? Number(match[2]) : total - 1;
    if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end)) return null;
    if (start >= total || start > end) return null;
    end = Math.min(end, total - 1);
  }
  return { start, end };
}

// Handle a single file, honouring an optional Range header (PMTiles partial reads).
function serveFile(filePath, req, res) {
  fs.stat(filePath, (err, stat) => {
    if (err || !stat.isFile()) return notFound(req, res);
    const total = stat.size;
    const headers = {
      "content-type": mimeFor(filePath),
      "accept-ranges": "bytes",
      "cache-control": "no-cache",
    };

    const rangeHeader = req.headers.range;
    if (rangeHeader) {
      const range = parseRange(rangeHeader, total);
      if (!range) {
        return send(req, res, 416, "", {
          ...headers,
          "content-range": `bytes */${total}`,
          "content-length": "0",
        });
      }
      const { start, end } = range;

      const chunk = end - start + 1;
      res.writeHead(206, {
        ...headers,
        "content-range": `bytes ${start}-${end}/${total}`,
        "content-length": String(chunk),
      });
      if (req.method === "HEAD") return res.end();
      if (res.destroyed) return;
      fs.createReadStream(filePath, { start, end }).pipe(res);
      return;
    }

    headers["content-length"] = String(total);
    res.writeHead(200, headers);
    if (req.method === "HEAD") return res.end();
    if (res.destroyed) return;
    fs.createReadStream(filePath).pipe(res);
  });
}

function createServer(root = ROOT, options = {}) {
  const pmtiles = options.pmtiles || "local";
  if (pmtiles !== "local" && pmtiles !== "r2") throw new Error(`Invalid PMTiles source: ${pmtiles}`);
  const upstream = pmtiles === "r2" ? r2Config(root) : null;
  const fetchUpstream = options.fetchUpstream || fetch;
  return http.createServer((req, res) => {
    if (req.method !== "GET" && req.method !== "HEAD") {
      return send(req, res, 405, "Method not allowed", {
        allow: "GET, HEAD",
        "content-type": "text/plain; charset=utf-8",
      });
    }

    let requestPath;
    try {
      requestPath = req.url.split("?")[0].split("#")[0];
    } catch (_e) {
      requestPath = "/";
    }
    if (requestPath.endsWith("/")) requestPath += "index.html";

    if (upstream && requestPath === "/webmap/config.js") {
      fs.readFile(path.join(root, "webmap", "config.js"), "utf8", (error, configJs) => {
        if (error) return notFound(req, res);
        const script = configJs + "\nwindow.TB_CONFIG.pmtilesBases.dev = './r2/';"
          + "\nwindow.TB_CONFIG.pmtilesManifests.dev = './r2/pmtiles-manifest.json';\n";
        return send(req, res, 200, script, {
          "content-type": MIME[".js"],
          "content-length": String(Buffer.byteLength(script)),
          "cache-control": "no-store",
        });
      });
      return;
    }

    if (upstream && requestPath.startsWith("/webmap/r2/")) {
      const filename = requestPath.slice("/webmap/r2/".length);
      if (!/^[A-Za-z0-9][A-Za-z0-9_.-]*$/.test(filename)) return notFound(req, res);
      const url = filename === "pmtiles-manifest.json"
        ? upstream.manifest : new URL(filename, upstream.base);
      const headers = {};
      if (req.headers.range) headers.Range = req.headers.range;
      if (req.headers["if-range"]) headers["If-Range"] = req.headers["if-range"];
      const controller = new AbortController();
      res.on("close", () => { if (!res.writableEnded) controller.abort(); });
      void fetchUpstream(url, { method: req.method, headers, signal: controller.signal })
        .then((response) => {
          const forwarded = {};
          for (const name of ["content-type", "content-length", "content-range",
            "accept-ranges", "cache-control", "etag", "expires", "last-modified",
            "cf-cache-status", "age"]) {
            const value = response.headers.get(name);
            if (value !== null) forwarded[name] = value;
          }
          res.writeHead(response.status, forwarded);
          if (req.method === "HEAD" || !response.body) return res.end();
          Readable.fromWeb(response.body).on("error", () => res.destroy()).pipe(res);
        }).catch((error) => {
          if (!controller.signal.aborted && !res.headersSent) {
            send(req, res, 502, `R2 request failed: ${error.message}`, {
              "content-type": "text/plain; charset=utf-8", "cache-control": "no-store",
            });
          }
        });
      return;
    }

    const target = safePath(requestPath, root);
    if (!target) return notFound(req, res);

    fs.stat(target, (err, stat) => {
      if (err) return notFound(req, res);
      if (stat.isDirectory()) {
        const queryIndex = req.url.indexOf("?");
        const query = queryIndex >= 0 ? req.url.slice(queryIndex) : "";
        return send(req, res, 308, "", {
          location: `${requestPath}/${query}`,
          "cache-control": "no-cache",
          "content-length": "0",
        });
      }
      return serveFile(target, req, res);
    });
  });
}

if (require.main === module) {
  const { port, pmtiles } = parseServerArgs(process.argv.slice(2));
  const server = createServer(ROOT, { pmtiles });
  server.listen(port, HOST, () => {
  const url = `http://${HOST}:${port}`;
  process.stdout.write(
    [
      "TracciaBianca webmap dev server",
      `  root : ${ROOT}`,
      `  url  : ${url}/webmap/   (open this)`,
      `  data : ${url}/data/     (atlas.json, cores.geojson)`,
      `  tiles: ${pmtiles === "r2" ? "R2 via local proxy" : `${url}/webmap/tiles/`}`,
      `  range: enabled (PMTiles partial reads)`,
      "  stop : press Ctrl+C",
      "",
    ].join("\n")
  );
  });
}

module.exports = { createServer, parseRange, safePath, parseServerArgs };
