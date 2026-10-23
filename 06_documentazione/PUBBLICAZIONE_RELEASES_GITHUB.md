# Pubblicazione incrementale delle mappe su GitHub Releases

Questo documento è il riferimento operativo per pubblicare gli MBTiles di
TracciaBianca e mantenere sincronizzata la mappa interattiva Leaflet.

## Modello editoriale

Le Release sono **incrementali**, non sono archivi completi dell'intero atlante.
Ogni Release contiene soltanto:

- celle pubblicate per la prima volta;
- nuove edizioni di celle già pubblicate;
- SHA256SUMS.txt;
- release-manifest.json.

Le celle non cambiate non vengono duplicate. Le Release precedenti restano
disponibili, mentre la mappa interattiva rimanda sempre all'edizione pubblicata
più recente di ogni cella.

### Versioni

- fase beta: v0.1.0-beta.1, v0.1.0-beta.2, ...;
- prima versione stabile: v0.1.0;
- aggiunta di nuove celle: incremento minor, per esempio v0.2.0;
- sola correzione o nuova edizione: incremento patch, per esempio v0.2.1.

## Quando una mappa è pronta

Ogni nuovo export che conclude la validazione tecnica automatica viene salvato
direttamente con publication_status: release_ready. Non sono richiesti test
manuali ripetuti per Android, iOS, GPXSee, hosting o licenze.

Restano automatici e obbligatori:

- apertura e integrità SQLite;
- decodifica delle immagini;
- copertura e partizionamento delle tessere;
- dimensione effettiva del file;
- SHA-256;
- limite GitHub di 2 GiB per singolo asset.

Il contenuto cartografico MBTiles segue la licenza dichiarata nel README
pubblico: Creative Commons Attribution-NonCommercial-ShareAlike 4.0
International (CC BY-NC-SA 4.0).

Una mappa release_ready non è ancora scaricabile. Diventa published soltanto
dopo che il relativo asset è presente in una Release GitHub pubblica.

## 1. Audit delle celle presenti

Dalla radice di QGIS_Scialpinismo:

~~~sh
python3 07_Scripts/prepare_github_release.py audit
~~~

Senza identificativi, il comando considera soltanto le cartelle
##_aree/ALP_E…_N… effettivamente presenti. Per una selezione:

~~~sh
python3 07_Scripts/prepare_github_release.py audit \
  ALP_E143_N084 ALP_E143_N085 ALP_E144_N084
~~~

Ogni export tecnicamente valido deve risultare READY.

## 2. Preparare il pacchetto editoriale

Il comando ricalcola gli SHA-256, verifica dimensioni e metadati e si arresta
se un file è mancante, alterato o supera il limite per asset:

~~~sh
python3 07_Scripts/prepare_github_release.py prepare \
  --tag v0.1.0-beta.1 \
  --title "Offline Alpine Maps — Beta 1" \
  --output release_staging/v0.1.0-beta.1 \
  ALP_E143_N084 ALP_E143_N085 ALP_E144_N084
~~~

La cartella di staging contiene soltanto file leggeri:

- RELEASE_NOTES.md;
- SHA256SUMS.txt;
- release-manifest.json.

Gli MBTiles non vengono copiati né aggiunti a Git. Il comando stampa la riga
gh release create completa con i percorsi originali degli asset.

## 3. Creare prima una bozza

Installare e autenticare GitHub CLI una sola volta:

~~~sh
brew install gh
gh auth login
~~~

Eseguire il comando stampato dal preparatore. La forma è:

~~~sh
gh release create v0.1.0-beta.1 \
  --repo tel-la/TracciaBianca \
  --target main \
  --draft \
  --prerelease \
  --title "Offline Alpine Maps — Beta 1" \
  --notes-file release_staging/v0.1.0-beta.1/RELEASE_NOTES.md \
  PERCORSO_MAPPA_1.mbtiles \
  PERCORSO_MAPPA_2.mbtiles \
  PERCORSO_MAPPA_3.mbtiles \
  release_staging/v0.1.0-beta.1/SHA256SUMS.txt \
  release_staging/v0.1.0-beta.1/release-manifest.json
~~~

Controllare la bozza:

~~~sh
gh release view v0.1.0-beta.1 \
  --repo tel-la/TracciaBianca \
  --json tagName,name,isDraft,isPrerelease,assets,url
~~~

Poi pubblicare:

~~~sh
gh release edit v0.1.0-beta.1 \
  --repo tel-la/TracciaBianca \
  --draft=false
~~~

## 4. Registrare la Release e rigenerare Leaflet

Solo dopo che la Release è pubblica:

~~~sh
python3 07_Scripts/prepare_github_release.py mark-published \
  --tag v0.1.0-beta.1 \
  --repository github/TracciaBianca \
  ALP_E143_N084 ALP_E143_N085 ALP_E144_N084
~~~

Il comando legge la Release dall'API pubblica di GitHub, verifica che non sia
una bozza e confronta nome e byte di ogni asset. Poi aggiorna i cataloghi locali
con tag e URL esatti, imposta publication_status: published e rigenera docs/.

Controlli finali:

~~~sh
python3 -m unittest \
  07_Scripts/tests/test_interactive_map.py \
  07_Scripts/tests/test_prepare_github_release.py
node --check github/TracciaBianca/docs/app.js
git -C github/TracciaBianca diff --check
~~~

Infine:

~~~sh
git -C github/TracciaBianca add README.md RELEASES.md docs
git -C github/TracciaBianca commit -m "Update atlas for v0.1.0-beta.1"
git -C github/TracciaBianca push origin main
~~~

## Release successive

Per ogni integrazione:

1. esportare le nuove celle: saranno automaticamente release_ready;
2. selezionare soltanto le celle nuove o aggiornate;
3. scegliere il tag successivo;
4. preparare e pubblicare la nuova Release incrementale;
5. eseguire mark-published per le sole celle incluse;
6. pubblicare la nuova versione di docs/.

Non modificare una Release già pubblicata e non sostituire un asset esistente
con lo stesso nome. Una nuova edizione riceve un nuovo nome e una nuova Release.

## Stato attuale

Le celle ALP_E143_N084, ALP_E143_N085 e ALP_E144_N084 sono tecnicamente valide
e impostate come release_ready. Possono entrare nella prossima Release senza
ulteriori collaudi manuali.
