# Strumenti del workflow locale

Avvio ordinario: `Avvia_Scialpinismo.command`. Carica il provider nella sessione QGIS senza installare file nel profilo globale. Strumenti: **Prepara area**, **Aggiorna area**, **Esporta offline**. Il plugin convenzionale è disponibile tramite `scialpinismo/metadata.txt` e `classFactory`; per quel caso impostare `SCIALPINISMO_ROOT` alla cartella principale.

## Comandi macOS

Dalla cartella principale:

```sh
07_Scripts/qgis_python.sh 07_Scripts/workflow.py init
07_Scripts/qgis_python.sh 07_Scripts/workflow.py list
07_Scripts/qgis_python.sh 07_Scripts/workflow.py prepare 03_lagazuoi --bbox 11.97 46.50 12.07 46.59
07_Scripts/qgis_python.sh 07_Scripts/workflow.py update '##_aree/03_lagazuoi'
07_Scripts/qgis_python.sh 07_Scripts/workflow.py check '##_aree/03_lagazuoi'
07_Scripts/qgis_python.sh 07_Scripts/workflow.py export '##_aree/03_lagazuoi'
```

Il BBOX è ovest, sud, est, nord in WGS84. CRS metrico con `--crs`, default EPSG:32633. `--source ID` è ripetibile; senza opzione si usano le sorgenti verificate con copertura disponibile. Il profilo predefinito è 12–16; lo zoom 17 resta selezionabile come dettaglio grafico e il 18 richiede DTM nativo verificato sotto 5 m su area e margine. Per un identificativo esistente usare `update`.

Il wrapper usa il bundle QGIS macOS presente, con GDAL e Python inclusi. Per un'altra installazione impostare `SCIALPINISMO_QGIS_BUNDLE` alla directory Contents, adattando il wrapper se cambia la struttura del bundle. Il lanciatore GUI usa `SCIALPINISMO_QGIS_APP`. Il lanciatore passa esplicitamente `SCIALPINISMO_SCRIPT` all'app con `open --env`: l'avvio non dipende da `__file__` o dalla cartella corrente. Dalla console si può impostare la variabile globale `SCIALPINISMO_SCRIPT` al percorso completo dello script; sono supportati anche il parametro `--code` e, come ultimo ripiego, la cartella corrente. Il percorso è validato prima dell'avvio e conservato nel callback Qt.

## Configurazione e sorgenti

`area.json` definisce perimetro WKT, CRS, fonti, margine, intervallo curve ed export. Cambiando fonti, perimetro o master QML, usare Aggiorna area prima di esportare. Annotazioni manuali nel layer dedicato; GPX in `input/tracce_gpx`.

Il registro autorevole delle sorgenti è `##_aree/_archivio_comune/fonti.json`. I percorsi sono relativi all'archivio. Per nuove fonti copiare una volta i dati in `dtm/originali`, registrare provenienza/versione, licenza, CRS, risoluzione nativa, griglia, datum/unità, copertura WGS84 e verifica, poi eseguire `init`. Non attivare `verified` per dati non validati. L'inizializzazione usa soltanto file locali: nessuna ricerca in Downloads. Tutti i file `osm/*.osm.pbf` vengono catalogati in `osm_sources`; per ogni area il workflow seleziona automaticamente i pacchetti che ne intersecano il perimetro e il margine, unendoli e rimuovendo i duplicati OSM. Il campo singolo `osm` resta solo come alias compatibile con versioni precedenti.

Quando più DTM verificati intersecano l’area, il mosaico conserva la sorgente di base e applica le fonti più fini per ultime senza ridurre l’intera area alla risoluzione peggiore. La griglia finale usa il passo più fine realmente disponibile; la risoluzione informativa di ogni sorgente resta però distinta e governa il supporto fisico usato per pendenza e hillshade.

Il servizio ARSO sloveno va letto a 1 m: richieste `exportImage` direttamente a 2–5 m possono restituire solo NoData anche dove `identify` trova quote valide. Il workflow scarica blocchi LERC2 a 1 m, normalizza i segnaposto `-3` e `-1e10`, poi ricampiona localmente e salva i tasselli da 10 km. La firma della cache invalida i vecchi tasselli ARSO; la validazione blocca anche quote fuori dall’intervallo plausibile prima di generare le curve.

Le sovrapposizioni vengono confrontate su una griglia antialias. Una regressione robusta su pendenza e orientamento separa gli spostamenti planimetrici `dx/dy` dall’offset verticale `dz`; una correzione additiva a bassa frequenza agisce soltanto entro 500 m dal bordo. La seamline esclude localmente i residui oltre 8 m e raccorda la componente lenta per 20–60 m, mentre il micro-rilievo della fonte fine cambia sorgente in una fascia ancora più stretta. Il controllo finale impedisce che la fusione aggiunga più di 5° o generi una nuova classe ≥30° quando entrambi gli ingressi restano sotto 25°. Campioni, NMAD, spostamenti, residui e celle escluse sono registrati in `rapporto.json`. Il NoData dichiarato continua a impedire a un ritaglio locale di cancellare la base nei propri vuoti.

L’ombreggiatura multidirezionale mantiene sempre come illuminazione principale un sole con altezza 45° e azimut 315°: questa direzione pesa il 70% del risultato. Gli azimut 225°, 270° e 360° forniscono soltanto il restante 30% di riempimento, senza cambiare la direzione dominante.

La politica predefinita resta rigorosa. Nelle finestre **Prepara area**, **Aggiorna area** ed **Esporta offline**, il campo **NoData DTM massimo (%)** scrive automaticamente la scelta in `area.json`: `0` richiede copertura completa; un valore positivo consente l’export entro quella soglia. In Aggiorna/Esporta, lasciando il campo vuoto si conserva la scelta esistente. Se la soglia viene cambiata da Esporta, il plugin aggiorna automaticamente DTM, derivati e progetto prima di produrre gli MBTiles. Il limite massimo configurabile è 10%; un DTM senza celle valide o oltre soglia resta bloccato. Il workflow non inventa quote: percentuale e numero di celle mancanti vengono riportati in `rapporto.json`, `catalogo_mbtiles.json` e negli avvisi di produzione.

`catalogo.gpkg` visualizza coperture e aree. COG condivisi da 10 km in `dtm/tasselli/<fonte>/epsg-<codice>_r<passo>m`, VRT relativi con estensione dei tasselli nel nome. L'area riceve dati locali compressi con panoramiche. Stato incrementale in `elaborati/stato.json`, fonti e risultati in `rapporto.json`. Le impronte usano dimensione e mtime: non conservarli artificialmente sostituendo una sorgente. Un lock impedisce lavorazioni simultanee. Temporanei `.partial*` si sovrascrivono riprendendo una fase; rimuoverli solo dopo verifica del completamento.

## Grafica e MBTiles

I master `03_styles/auto_*.qml` vengono applicati senza sovrascrivere le scale calcolate per l'area. Quote Curved / OnLine a distanza zero: a zoom 15 sole direttrici 100 m, 9 pt normali; da 16 direttrici 10,2 pt grassetto e intermedie 20 m 7,2 pt. Le aree OSM residenziali/commerciali rendono leggibili i nuclei abitati agli zoom 12–15; le sagome degli edifici subentrano nel dettaglio. Le soglie 14/15 e 15/16 sono variabili di progetto e di layer, usate anche nel rendering Processing.

Agli zoom 13–15 i testi di rifugi, paesi/città e strade sono aumentati del 25%; zoom 12 e zoom 16+ restano invariati. I relativi master sono sincronizzati dal codice a ogni costruzione del progetto.

I nomi dei bivacchi e dei ripari compaiono da zoom 16, nello stesso arancione `#ee870b` dell'icona; agli zoom 12–15 resta visibile soltanto l'icona.

I parcheggi OSM (`amenity=parking`) sono rappresentati da zoom 14 con un segnale blu bordato di bianco e una `P` bianca; da zoom 16 il segnale usa la variante compatta per non coprire i dettagli circostanti. Da zoom 16 le etichette delle vette OSM con campo `ele` riportano anche la quota in metri.

Da 16 la saturazione HSV delle pendenze è aumentata del 20%, mantenendo alfa e soglie. Isoipse: RGB ×0,75, alfa invariato, spessore ×1,15. Dettagli, altre simbologie e limiti sono nell'handoff.

Export PNG RGBA, 256 px, 96 DPI, opaco all'interno e trasparente fuori dal perimetro. La finestra **Esporta offline** chiede zoom minimo e massimo (default 12–16, intervallo ammesso 12–18) e produce per impostazione predefinita un solo MBTiles per area. La suddivisione geografica è opzionale: deve essere scelta esplicitamente e richiede di indicare il limite MB nella stessa finestra; non esiste più una soglia predefinita di 600 MB. Eliminazione delle tessere fuori competenza e verifica delle immagini e di SQLite restano sempre attive. `catalogo_mbtiles.json` e `LEGGIMI_PRODUZIONE_CORRENTE.txt` elencano i file correnti. Rimuovere le vecchie serie dal telefono.

## Verifiche

```sh
07_Scripts/qgis_python.sh 07_Scripts/tests/test_workflow.py
07_Scripts/qgis_python.sh 07_Scripts/verifica_workspace.py
07_Scripts/qgis_python.sh 07_Scripts/anteprime_cartografiche.py '##_aree/01_Cortina'
```

L'audit controlla fonti e materiali supplementari, tutti i QGZ, collegamenti locali/online, VRT relativi e symlink. I software installati e i file temporanei di prova non sono dipendenze territoriali del progetto.

## Atlante alpino

La griglia v2 genera le aree montane Lago Maggiore–Friuli in EPSG:3035. Ogni `cella_analisi` misura 35 × 35 km; il passo è 31 km, quindi ogni cella si estende 2 km oltre il proprio nucleo su ciascun lato e condivide 4 km con l’adiacente. Il filtro DTM, configurabile dalla finestra QGIS, esclude i settori senza montagne. Gli output vettoriali sono `##_aree/_archivio_comune/atlante_griglia_v2.gpkg`, `08_Atlante/griglia.gpkg` e `08_Atlante/celle_analisi.geojson`.

`prepare-cells` accetta una cella o al massimo due celle adiacenti e crea normali aree utilizzabili da **Aggiorna area** ed **Esporta offline**; non esporta automaticamente. Ogni export riguarda una sola area e produce normalmente un solo MBTiles. CLI: `grid`, `prepare-cells`, `rename-cell`, `atlas`, `publish-cell`.

I nuovi export sono conservati in edizioni; leggere sempre `output/mbtiles/catalogo_mbtiles.json` per i percorsi correnti. Guida completa: `06_documentazione/ATLANTE_ALPINO.md`.
