"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const http = require("node:http");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  createServer,
  parseRange,
  safePath,
} = require("../interactive_map_src/webmap/dev-server.js");

function request(port, requestPath, options = {}) {
  return new Promise((resolve, reject) => {
    const req = http.request({
      host: "127.0.0.1",
      port,
      path: requestPath,
      method: options.method || "GET",
      headers: options.headers || {},
    }, (res) => {
      const chunks = [];
      res.on("data", (chunk) => chunks.push(chunk));
      res.on("end", () => resolve({
        status: res.statusCode,
        headers: res.headers,
        body: Buffer.concat(chunks),
      }));
    });
    req.on("error", reject);
    req.end();
  });
}

test("parseRange handles bounded, open and suffix byte ranges", () => {
  assert.deepEqual(parseRange("bytes=2-5", 10), { start: 2, end: 5 });
  assert.deepEqual(parseRange("bytes=4-", 10), { start: 4, end: 9 });
  assert.deepEqual(parseRange("bytes=-3", 10), { start: 7, end: 9 });
  assert.deepEqual(parseRange("bytes=8-99", 10), { start: 8, end: 9 });
  assert.equal(parseRange("bytes=10-", 10), null);
  assert.equal(parseRange("bytes=5-2", 10), null);
  assert.equal(parseRange("bytes=0-1,4-5", 10), null);
});

test("safePath rejects decoded path traversal", () => {
  const root = path.join(os.tmpdir(), "webmap-safe-root");
  assert.equal(safePath("/../secret", root), null);
  assert.equal(safePath("/%2e%2e/secret", root), null);
  assert.equal(safePath("/%ZZ", root), null);
  assert.equal(safePath("/data/file.bin", root), path.join(root, "data/file.bin"));
});

test("server supports GET, HEAD, byte ranges and HTTP errors", async (t) => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "tracciabianca-webmap-"));
  fs.writeFileSync(path.join(root, "index.html"), "webmap", "utf8");
  fs.writeFileSync(path.join(root, "sample.bin"), Buffer.from("0123456789"));

  const server = createServer(root);
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  t.after(async () => {
    await new Promise((resolve) => server.close(resolve));
    fs.rmSync(root, { recursive: true, force: true });
  });
  const port = server.address().port;

  const full = await request(port, "/sample.bin");
  assert.equal(full.status, 200);
  assert.equal(full.headers["accept-ranges"], "bytes");
  assert.equal(full.body.toString(), "0123456789");

  const bounded = await request(port, "/sample.bin", { headers: { Range: "bytes=2-5" } });
  assert.equal(bounded.status, 206);
  assert.equal(bounded.headers["content-range"], "bytes 2-5/10");
  assert.equal(bounded.body.toString(), "2345");

  const suffix = await request(port, "/sample.bin", { headers: { Range: "bytes=-3" } });
  assert.equal(suffix.status, 206);
  assert.equal(suffix.body.toString(), "789");

  const head = await request(port, "/sample.bin", { method: "HEAD" });
  assert.equal(head.status, 200);
  assert.equal(head.headers["content-length"], "10");
  assert.equal(head.body.length, 0);

  const invalid = await request(port, "/sample.bin", { headers: { Range: "bytes=50-" } });
  assert.equal(invalid.status, 416);
  assert.equal(invalid.headers["content-range"], "bytes */10");

  assert.equal((await request(port, "/%2e%2e/secret")).status, 404);
  assert.equal((await request(port, "/sample.bin", { method: "POST" })).status, 405);
});
