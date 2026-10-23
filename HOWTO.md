# Come lavorare con TracciaBianca

Questa guida descrive come scaricare il codice, predisporre l'ambiente locale e
usare il workflow QGIS senza alterare i dati già prodotti. Per le operazioni
quotidiane consultare anche
[`06_documentazione/GUIDA_RAPIDA.md`](06_documentazione/GUIDA_RAPIDA.md), mentre
[`07_Scripts/README.md`](07_Scripts/README.md) documenta i comandi e la
configurazione avanzata.

## Requisiti minimi

La configurazione operativa supportata è:

- macOS;
- Git 2.23 o successivo;
- QGIS 3.44.14 o successivo, installato come applicazione in
  `/Applications/QGIS.app`;
- almeno 60 GB liberi, con 100 GB consigliati quando si conservano più sorgenti,
  cache ed edizioni MBTiles.

Il plugin dichiara QGIS 3.34 come soglia minima delle API. Le versioni da 3.34 a
3.43 non sono però considerate pienamente supportate dal lanciatore macOS senza
un collaudo specifico. L'ambiente usato per il collaudo corrente comprende QGIS
3.44.14, Python 3.12.11, GDAL 3.13.3, NumPy 2.5.2, Pillow 12.3.0 e SQLite
3.53.4.

L'installazione ufficiale di QGIS fornisce già Python, GDAL, Processing, PyQt,
NumPy, Pillow e SQLite: non occorre installarli separatamente. QuickOSM è
facoltativo e serve soltanto per le query di approfondimento presenti in
`05_queries_quickosm/`; il workflow ordinario usa gli estratti PBF locali.

## Scaricare il codice

```sh
git clone https://github.com/tel-la/TracciaBianca.git
cd TracciaBianca
```

Il repository contiene codice, stili, template, documentazione e il quadro
dell'atlante. Non contiene i grandi dataset territoriali, le cache di lavoro, i
file `area.json` e `fonti.json` locali né gli MBTiles prodotti.

## Preparare i dati locali

Il sistema completo richiede sorgenti con licenza e copertura adeguate all'area:

- un DTM numerico locale, con CRS, risoluzione, NoData, datum verticale,
  provenienza e licenza noti;
- uno o più estratti OpenStreetMap `.osm.pbf` che coprano area e margine;
- facoltativamente GPX e altre sorgenti specifiche dell'area.

Conservare le sorgenti comuni sotto `##_aree/_archivio_comune/`, seguendo
[`SCHEMA_STRUTTURA_QGIS_SCIALPINISMO.txt`](SCHEMA_STRUTTURA_QGIS_SCIALPINISMO.txt).
Questi dati sono deliberatamente esclusi da Git. Non copiare o rinominare alla
cieca configurazioni provenienti da un altro computer: i percorsi, le licenze e
la copertura devono essere verificati localmente.

## Primo avvio

1. Verificare che QGIS sia disponibile in `/Applications/QGIS.app`.
2. Rendere eseguibile il lanciatore, se il sistema ha rimosso il permesso:

   ```sh
   chmod +x Avvia_Scialpinismo.command 07_Scripts/qgis_python.sh
   ```

3. Fare doppio clic su `Avvia_Scialpinismo.command`.
4. In QGIS usare **Prepara area** per una nuova zona oppure **Aggiorna area** per
   una zona già configurata.
5. Controllare il progetto generato prima di avviare **Esporta offline**.

Se QGIS si trova altrove, impostare `SCIALPINISMO_QGIS_APP` per il lanciatore e
`SCIALPINISMO_QGIS_BUNDLE` per i comandi da terminale. Il dettaglio è in
[`07_Scripts/README.md`](07_Scripts/README.md).

## Flusso di lavoro consigliato

Lavorare su una sola area alla volta, oppure su non più di due celle adiacenti
dell'atlante. Dopo la preparazione:

1. controllare copertura e NoData del DTM;
2. verificare sentieri, edifici, idrografia, toponimi e continuità del rilievo;
3. esportare normalmente agli zoom 12–16;
4. usare soltanto i file elencati in
   `output/mbtiles/LEGGIMI_PRODUZIONE_CORRENTE.txt`;
5. provare gli MBTiles sul dispositivo in modalità aereo prima dell'uso sul
   terreno.

Non eseguire lavorazioni massive sull'intero arco alpino. Le scelte geometriche
e operative dell'atlante sono descritte in
[`06_documentazione/ATLANTE_ALPINO.md`](06_documentazione/ATLANTE_ALPINO.md).

## Verifiche senza modificare i dati

I test che importano QGIS devono essere eseguiti con il Python incluso nel
bundle QGIS:

```sh
07_Scripts/qgis_python.sh 07_Scripts/tests/test_workflow.py
07_Scripts/qgis_python.sh 07_Scripts/tests/test_atlas.py
07_Scripts/qgis_python.sh 07_Scripts/verifica_workspace.py
```

L'audit può segnalare sorgenti territoriali mancanti o riferimenti esterni non
disponibili: leggere il rapporto prima di intervenire. Non correggere
automaticamente percorsi, progetti QGIS o registri delle fonti.

## Aggiornare il clone

Prima di modificare il codice, preservare eventuali cambi locali e integrare il
branch remoto senza riscrivere la cronologia:

```sh
git status
git fetch origin
git pull --rebase origin main
```

Se `git status` mostra file modificati, effettuare prima un commit oppure usare
temporaneamente `git stash push -u`. In presenza di conflitti, risolverli file
per file e ripetere i test; non usare `git reset --hard`, `git clean` o push
forzati per aggirare il problema.

Prima di ogni commit verificare che non siano inclusi dati locali, credenziali,
`area.json`, `fonti.json`, MBTiles, cache o file temporanei:

```sh
git status --short
git diff --cached --name-only
```
