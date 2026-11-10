/*
 * TracciaBianca webmap — runtime configuration
 * ---------------------------------------------------------------------------
 * Loaded before app.js so tile hosting can change without changing the viewer.
 *
 * env="auto" selects the local tile directory on localhost, 127.0.0.1 and
 * ::1; every other hostname uses the public base. Leave publish empty until a
 * Range- and CORS-capable endpoint (for example Cloudflare R2) is available.
 *
 * pmtilesManifests selects a local manifest in development and the live R2
 * manifest after publishing. A listed cell normally resolves its filename
 * from that index or by changing its catalogue MBTiles extension to .pmtiles.
 * Use sheetFiles only for explicit runtime overrides.
 */
window.TB_CONFIG = {
  env: "auto", // "auto" | "dev" | "publish"
  pmtilesBases: {
    dev: "./tiles/",
    publish: "https://pub-3e95fc6969fb409e83c7226568f91a90.r2.dev/",
  },
  pmtilesManifests: {
    dev: "./pmtiles-manifest.json",
    publish: "https://pub-3e95fc6969fb409e83c7226568f91a90.r2.dev/pmtiles-manifest.json",
  },
  sheetFiles: {},
};
