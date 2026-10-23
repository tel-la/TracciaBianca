# Handoff — mappe scialpinismo, workflow 1.3

Stato aggiornato il 19 ottobre 2026. L’obiettivo corrente è produrre MBTiles offline zona per zona; la generazione del sito dell’Atlante non è prioritaria.

## Flusso autorevole

Il percorso ordinario è: disponibilità DTM e OSM → preparazione/aggiornamento di una zona → controllo QGIS → export del range scelto → collaudo offline. La GUI propone zoom 12–16. Non avviare produzioni massive: ogni esportazione riguarda una sola area; la preparazione dell’Atlante accetta al massimo due celle adiacenti per verificare la continuità.

`area.json` è la configurazione autorevole. Gli originali condivisi e il catalogo stanno in `##_aree/_archivio_comune`; i dati derivati, il progetto e gli output stanno nella singola area. Le annotazioni e i GPX sono separati dai layer rigenerabili.

## DTM

La base continua è `dtm/originali/hrdtm5m/HRDTM5m`. Le fonti locali più precise sono organizzate in:

- `dtm/originali/AltoAdige/`: ritaglio a circa 2,5 m, EPSG:25832;
- `dtm/originali/Veneto_HQ/`: tre raster a 5 m, con CRS esplicitato nel catalogo;
- `dtm/originali/tinitaly/`: materiale supplementare non ancora registrato per uso automatico.

La selezione automatica conserva il DTM base e ordina il mosaico dal meno al più dettagliato. Ogni fonte viene riproiettata e allineata alla griglia dell’area; `srcNodata` e `dstNodata` sono gestiti esplicitamente. Il dato fine sovrascrive quindi la base solo nei pixel validi. La validazione blocca la produzione se il perimetro più il margine tecnico contiene NoData.

Le fonti Alto Adige e Veneto hanno superato un controllo tecnico di raster, passo, quote e NoData. Licenza e datum verticale vanno ancora completati dove `fonti.json` lo segnala. Per una nuova fonte registrare CRS, passo, risoluzione nativa, NoData, copertura, unità verticali, origine e licenza. WMS e hillshade non sono DTM numerici.

La verifica Lago Maggiore–Friuli è in `06_documentazione/COPERTURA_DTM_LAGO_MAGGIORE_FRIULI.txt`: non risultano zone italiane totalmente prive di DTM, grazie alla base locale nazionale; restano invece molte acquisizioni regionali ad alta risoluzione da fare prima delle rispettive celle.

## OSM e cartografia

Le sorgenti OSM locali sono tutti i pacchetti `osm/*.osm.pbf`, catalogati in `fonti.json` sotto `osm_sources` e selezionati automaticamente per copertura. Se un’area interessa più pacchetti, l’estrazione li unisce eliminando i duplicati. L’estrazione conserva punti, linee e multipoligoni; include edifici, ruderi, fabbricati rurali, rifugi, idrografia, impianti, strade, sentieri, vegetazione e aree abitate. A zoom 12–15 il layer delle aree abitate rende leggibili nuclei e conglomerati; gli edifici compaiono alle scale di dettaglio.

Tipografia corrente:

- rifugi, paesi/città e strade: +25% esclusivamente agli zoom 13–15;
- rifugi a zoom 12: 5,75 pt; zoom 13–15: 14,375 pt; zoom 16+: 11,5 pt;
- strade: 12,25 pt a zoom 13–15, 9,8 pt altrove;
- centri abitati: 15,625 pt a zoom 13–15, 12,5 pt altrove;
- altri toponimi: 13,75 pt a zoom 13–15, 11 pt altrove.

I master di strade, riferimenti e rifugi in `03_styles` vengono riscritti dal codice durante la costruzione del progetto. Questo evita che un QML precedente annulli la gerarchia tipografica corrente. Le due celle pilota sono state riallineate; le MBTiles già esportate non sono state rigenerate e riceveranno lo stile nuovo soltanto al prossimo export.

## Output e nomenclatura

Le edizioni usano `YYYYMMDDThhmmssZ`, con suffisso progressivo solo per collisioni nello stesso secondo. I file distribuiti hanno nomi leggibili, per esempio `ALP_E127_N073_agordino-san-martino_20261019T154743Z_01_z12-16.mbtiles`. Cache DTM e VRT dichiarano EPSG, risoluzione e intervallo dei tasselli; gli estratti OSM dichiarano il bounding box.

La cache DTM contiene 101 GeoTIFF e nessun duplicato SHA-256. I due gruppi conservati non sono duplicati: sono elaborazioni in EPSG:32632 ed EPSG:32633. I file `.DS_Store` sono stati rimossi.

## Verifiche e limiti

38 test del workflow passano. I controlli coprono selezione e sovrapposizione DTM, NoData, OSM poligonale, stili multiscala, export e integrità MBTiles. Restano da fare per ogni nuova edizione il controllo visivo, l’importazione su dispositivo, la modalità aereo e la verifica delle licenze effettive.

Comandi:

```sh
07_Scripts/qgis_python.sh 07_Scripts/tests/test_workflow.py
07_Scripts/qgis_python.sh 07_Scripts/tests/test_atlas.py
07_Scripts/qgis_python.sh 07_Scripts/verifica_workspace.py
```

Guida operativa: `06_documentazione/GUIDA_RAPIDA.md`. Gestione celle: `06_documentazione/ATLANTE_ALPINO.md`.
