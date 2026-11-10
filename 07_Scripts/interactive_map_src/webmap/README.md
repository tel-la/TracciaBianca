# TracciaBianca · Webmap PMTiles

Viewer raster **MapLibre GL JS + PMTiles** per l’atlante TracciaBianca. La
pagina è pubblicata in `docs/webmap/` accanto alla mappa Leaflet esistente e
riutilizza `docs/data/atlas.json` e `docs/data/cores.geojson`.

Questa fase non converte, genera o pubblica archivi PMTiles. Il viewer funziona
anche quando gli archivi non sono ancora disponibili.

## Sorgente e output

La sorgente versionata si trova in:

```text
07_Scripts/interactive_map_src/webmap/
```

`07_Scripts/build_interactive_map.py` la copia in `docs/webmap/` insieme al
resto del sito GitHub Pages. Non modificare soltanto la copia generata: la
successiva ricostruzione del sito la sostituirebbe.

Le librerie sono vendorizzate e non richiedono npm:

- MapLibre GL JS 4.7.1, licenza BSD-3-Clause;
- PMTiles 4.5.0 UMD, licenza BSD-3-Clause.

## Sviluppo locale

Il server serve `docs/` come radice e supporta richieste HTTP Range:

```bash
node docs/webmap/dev-server.js
# http://127.0.0.1:8080/webmap/
```

È possibile scegliere un’altra porta:

```bash
PORT=9000 node docs/webmap/dev-server.js
```

Gli archivi locali vanno inseriti in `docs/webmap/tiles/`. `.pmtiles` e
`.mbtiles` sono ignorati da Git e non vengono inclusi dal builder. Per rendere
visibile una cella, aggiungerla anche a `pmtiles-manifest.json`.

## Manifest e caricamento lazy

`pmtiles-manifest.json` è il piccolo indice delle celle che dispongono davvero
di un archivio. Il viewer lo carica una sola volta insieme al catalogo e mostra
soltanto le celle elencate. Non esegue richieste preventive verso tutti gli
archivi: header, directory e tile vengono letti solamente quando il centro
della mappa entra in una cella circa 1,8 livelli prima del suo `minzoom`. Un
archivio che parte da z12 mostra così una breve anteprima sottocampionata da
zoom mappa 10,2; a zoom 11 torna automaticamente alla scala raster standard.
Tutte le celle disponibili che intersecano il viewport vengono mantenute
visibili insieme, ciascuna con source e layer indipendenti. Quando una cella
esce dalla vista il relativo raster viene rimosso; tornando alla vista generale
vengono rimossi tutti. La scheda informativa e il download MBTiles si aprono
soltanto cliccando il riquadro con il codice della cella; il resto della
superficie resta dedicato alla navigazione della mappa.

Ogni voce può indicare esplicitamente file, dimensione e intervallo zoom:

```json
{
  "schema_version": 1,
  "sheets": {
    "ALP_E131_N078": {
      "file": "ALP_E131_N078_queyras-nord-orientale_20261108T212807Z_01_z12-16.pmtiles",
      "bytes": 622675695,
      "minzoom": 12,
      "maxzoom": 16
    }
  }
}
```

Se `file` viene omesso, il viewer cerca il primo pacchetto `.mbtiles` della
cella nel catalogo e ne cambia soltanto l’estensione in `.pmtiles`.

Esempio:

```text
ALP_E144_N084_cortina-d-ampezzo-dolomiti-cadore_20261023T132827Z_01_z12-16.mbtiles
ALP_E144_N084_cortina-d-ampezzo-dolomiti-cadore_20261023T132827Z_01_z12-16.pmtiles
```

Se un archivio deve avere un nome diverso, aggiungere un override in
`config.js`:

```js
sheetFiles: {
  ALP_E144_N084: "cortina.pmtiles",
},
```

Le celle non pubblicate o non presenti nel manifest non vengono visualizzate e
non producono richieste PMTiles. Un errore di caricamento non blocca basemap,
griglia, ricerca o pannello; rientrando nella cella o riselezionandola il viewer
ritenta la lettura.

## Ricerca geografica

La ricerca prova prima i nomi e gli identificativi delle celle disponibili. Se
non trova corrispondenze interroga Nominatim/OpenStreetMap e può quindi
raggiungere anche località non coperte da PMTiles. Le richieste OSM sono
vincolate al rettangolo complessivo delle celle presenti nel manifest,
allargato di 20 km in ogni direzione; lo stesso controllo viene ripetuto nel
browser prima di mostrare i risultati.

## Configurazione dev e publish

`config.js` espone una configurazione runtime:

```js
window.TB_CONFIG = {
  env: "auto", // "auto" | "dev" | "publish"
  pmtilesBases: {
    dev: "./tiles/",
    publish: "",
  },
  pmtilesManifests: {
    dev: "./pmtiles-manifest.json",
    publish: "https://tiles.example/pmtiles-manifest.json",
  },
  sheetFiles: {},
};
```

Con `env: "auto"`, `localhost`, `127.0.0.1` e `::1` usano `dev`; ogni altro
host usa `publish`. Prima della pubblicazione impostare `publish` sull’URL
pubblico del bucket o del dominio R2, terminato da `/`.

GitHub Pages continua a servire HTML, JavaScript, catalogo e GeoJSON. In
sviluppo usa il manifest locale; la pagina pubblicata legge invece il manifest
R2, così aggiunte e rimozioni diventano visibili senza un nuovo commit GitHub.

## Upload e sincronizzazione R2

Il comando seguente carica uno o più file, verifica Range/CORS, ricostruisce le
due copie locali del manifest dall'elenco reale del bucket e pubblica su R2 il
manifest usato dalla webmap online:

```bash
07_Scripts/upload_pmtiles_r2.sh prima.pmtiles seconda.pmtiles
```

Senza file esegue soltanto la riconciliazione. È il comando da usare dopo aver
cancellato manualmente oggetti da R2:

```bash
07_Scripts/upload_pmtiles_r2.sh
```

R2 è la fonte autorevole: una cella senza più PMTiles viene rimossa dal
manifest; se esistono più edizioni della stessa cella viene scelta quella con
il timestamp più recente nel nome. Il manifest R2 usa `no-cache`, mentre i
PMTiles versionati conservano la cache immutabile di un anno.

## Requisiti R2, Range e CORS

L’endpoint deve accettare richieste a intervalli e restituire:

- `206 Partial Content` per `Range: bytes=...`;
- `Accept-Ranges: bytes`;
- un `Content-Range` coerente con l’archivio;
- CORS per l’origine GitHub Pages, ad esempio
  `https://tel-la.github.io` o il dominio personalizzato effettivo.

Per la produzione usare un dominio personalizzato collegato al bucket, non il
dominio di sviluppo `r2.dev`. Impostare sugli archivi versionati un header come
`Cache-Control: public, max-age=31536000, immutable` e non applicare
`Content-Encoding` al file PMTiles.

Cloudflare limita normalmente la cache CDN a oggetti di 512 MB sui piani Free,
Pro e Business. Gli archivi più grandi continuano a funzionare tramite Range
Requests, ma non beneficiano della cache edge: quando possibile conviene
comprimerli o suddividerli sotto tale soglia durante la futura generazione.

Una configurazione CORS R2 indicativa è:

```json
[
  {
    "AllowedOrigins": ["https://tel-la.github.io"],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedHeaders": ["Range"],
    "ExposeHeaders": ["Accept-Ranges", "Content-Length", "Content-Range", "ETag"],
    "MaxAgeSeconds": 3600
  }
]
```

Verifica preliminare di un archivio pubblico:

```bash
curl -I "https://tiles.example/archivio.pmtiles"
curl -i -H "Range: bytes=0-16383" "https://tiles.example/archivio.pmtiles" -o /dev/null
```

La seconda risposta deve essere `206`, non `200`, e deve includere
`Content-Range`.

## Controlli

```bash
python3 -m unittest 07_Scripts/tests/test_interactive_map.py
node --test 07_Scripts/tests/test_webmap_server.js
node --check 07_Scripts/interactive_map_src/webmap/app.js
node --check 07_Scripts/interactive_map_src/webmap/config.js
node --check 07_Scripts/interactive_map_src/webmap/dev-server.js
```

Checklist prima della pubblicazione:

1. ricostruire `docs/` con il builder;
2. aprire `/webmap/` tramite il server locale;
3. verificare che siano mostrate soltanto le celle elencate nel manifest;
4. verificare che l’avvio e la vista generale non generino richieste verso gli archivi PMTiles;
5. senza cliccare, portare il centro della mappa dentro una cella a zoom 10,2 e verificare anteprima e tile Range z12;
6. inquadrare due o più celle contigue e verificare che i rispettivi raster siano visibili insieme;
7. cercare una località esterna alle celle ma interna al margine di 20 km;
8. provare lo stesso archivio su R2 dall’origine GitHub Pages;
9. controllare console, layout desktop/mobile, tastiera ed `Esc`.
