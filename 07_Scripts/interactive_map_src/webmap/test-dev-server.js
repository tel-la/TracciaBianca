"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const http = require("node:http");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");
const { createServer, parseServerArgs } = require("./dev-server.js");

function get(port, pathname, headers = {}) {
  return new Promise((resolve, reject) => {
    http.get({ hostname: "127.0.0.1", port, path: pathname, headers }, (response) => {
      const chunks = [];
      response.on("data", (chunk) => chunks.push(chunk));
      response.on("end", () => resolve({
        status: response.statusCode,
        headers: response.headers,
        body: Buffer.concat(chunks).toString(),
      }));
    }).on("error", reject);
  });
}

async function serve(server, callback) {
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  try {
    await callback(server.address().port);
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
}

test("CLI selects local or R2 and rejects unknown options", () => {
  assert.deepEqual(parseServerArgs([], undefined), { port: 8080, pmtiles: "local" });
  assert.deepEqual(parseServerArgs(["--pmtiles=r2", "9000"], undefined),
    { port: 9000, pmtiles: "r2" });
  assert.throws(() => parseServerArgs(["--pmtiles=other"], undefined), /Unknown server option/);
});

test("R2 mode uses the publish URLs through the localhost proxy", async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "webmap-r2-test-"));
  fs.mkdirSync(path.join(root, "webmap"));
  const config = "window.TB_CONFIG = { pmtilesBases: { dev: './tiles/', "
    + "publish: 'https://example.invalid/maps/' }, pmtilesManifests: { "
    + "dev: './pmtiles-manifest.json', publish: 'https://example.invalid/catalog.json' } };";
  fs.writeFileSync(path.join(root, "webmap", "config.js"), config);
  const calls = [];
  const fetchUpstream = async (url, options) => {
    calls.push({ url: String(url), range: options.headers.Range });
    if (String(url).endsWith("catalog.json")) {
      return new Response('{"sheets":{}}', { headers: { "content-type": "application/json" } });
    }
    return new Response("tile", { status: 206, headers: {
      "content-range": "bytes 0-3/100", "content-length": "4",
    } });
  };
  try {
    await serve(createServer(root), async (port) => {
      assert.equal((await get(port, "/webmap/config.js")).body, config);
    });
    await serve(createServer(root, { pmtiles: "r2", fetchUpstream }), async (port) => {
      const configResponse = await get(port, "/webmap/config.js?v=1");
      assert.equal(configResponse.status, 200);
      assert.match(configResponse.body, /pmtilesBases\.dev = '\.\/r2\/'/);
      assert.match(configResponse.body, /pmtilesManifests\.dev = '\.\/r2\/pmtiles-manifest\.json'/);
      assert.equal(configResponse.headers["cache-control"], "no-store");
      assert.equal((await get(port, "/webmap/r2/pmtiles-manifest.json")).body,
        '{"sheets":{}}');
      const tile = await get(port, "/webmap/r2/sheet.pmtiles", { Range: "bytes=0-3" });
      assert.equal(tile.status, 206);
      assert.equal(tile.headers["content-range"], "bytes 0-3/100");
      assert.equal(tile.body, "tile");
      assert.equal((await get(port, "/webmap/r2/%2e%2e%2fsecret")).status, 404);
    });
    assert.deepEqual(calls, [
      { url: "https://example.invalid/catalog.json", range: undefined },
      { url: "https://example.invalid/maps/sheet.pmtiles", range: "bytes=0-3" },
    ]);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});
