# Atlante TracciaBianca — griglia delle aree di analisi

La griglia `ALP35_OVERLAP2_LAEA_v2` comprende 94 nuclei: 86 alpini, dalle Alpi occidentali e marittime al Friuli, e 8 nell'Appennino centrale, fra Gran Sasso, Sirente–Velino, Maiella e Monti Marsicani. Il codice della griglia resta invariato per compatibilità con i pacchetti esistenti. I prefissi delle celle sono `ALP` e `APP` rispettivamente.

## Geometria

- CRS della griglia: EPSG:3035.
- Riquadro finale di analisi: 35 × 35 km.
- Nucleo esclusivo: 31 × 31 km.
- Fascia aggiunta: 2 km su ciascun lato del nucleo.
- Passo della griglia: 31 km.
- Sovrapposizione tra due riquadri adiacenti: 4 km complessivi.

La fascia di 2 km appartiene a ciascun riquadro. Per questo due riquadri confinanti condividono 2 km da una parte e 2 km dall’altra, cioè una fascia comune di 4 km.

## Estensioni del 29 ottobre 2026

Le due immagini di riferimento sono `Screenshot 2026-10-29 alle 19.25.32.png` (Alpi occidentali e marittime) e `Screenshot 2026-10-29 alle 19.26.12.png` (Appennino centrale). I contorni disegnati sono indicativi: `07_Scripts/extend_atlas_regions.py` ne registra i vertici e seleziona un nucleo quando almeno il 10% della sua superficie interseca il contorno. Il risultato è riproducibile con `--dry-run`. Le 31 nuove celle alpine usano esattamente l'origine e il passo della griglia esistente; anche le 8 appenniniche usano la stessa griglia EPSG:3035 per mantenere una codifica uniforme.

Per scelta editoriale sono escluse definitivamente `ALP_E134_N074`, `ALP_E133_N076`, `ALP_E133_N077`, `ALP_E133_N078` e `ALP_E133_N079`. La cella `APP_E149_N067` è aggiunta esplicitamente a sud di `APP_E149_N068`, oltre il contorno indicativo della seconda immagine. I nomi delle celle pianificate sono univoci e mantenuti nello script di estensione, così una rigenerazione non reintroduce duplicati.

Lo script aggiorna la griglia, i GeoJSON, il catalogo locale e i nomi delle località; non prepara aree né esporta MBTiles. Le celle nuove sono `planned` e non hanno URL di download finché non vengono pubblicate. Il sito GitHub Pages si aggiorna separatamente con `07_Scripts/build_interactive_map.py --repository <checkout>`.
Se l'archivio locale `atlante_griglia_v2.json` non è presente in un nuovo checkout, lo script ricostruisce la griglia a partire dal catalogo leggero versionato in `08_Atlante/catalogo.json`.

Prima di esportare celle appenniniche occorre registrare un estratto OSM che copra l'Appennino centrale: gli estratti attuali non arrivano a queste latitudini. Per le celle alpine transfrontaliere verso la Francia occorre inoltre verificare e, dove necessario, integrare la copertura DTM. Queste esigenze riguardano i dati di produzione delle future mappe, non la visualizzazione dei nuclei nell'indice.

## Creare la griglia in QGIS

1. Avviare `Avvia_Scialpinismo.command`.
2. Aprire **Plugin → Scialpinismo locale → Crea o estendi griglia atlante**.
3. Lasciare vuota l’estensione per usare il dominio predefinito Lago Maggiore–Friuli.
4. Lasciare attivo **Conserva solo riquadri con montagne rilevate dal DTM**.
5. Usare normalmente quota minima 600 m e superficie minima sopra quota 1%.

Il filtro campiona il DTM verificato, preferibilmente `hrdtm5m`, e conserva i riquadri che contengono una superficie montana significativa. Estensione e soglie sono modificabili dalla finestra QGIS.

La composizione editoriale applica le esclusioni definite in `EXCLUDED_CELL_IDS` in
`07_Scripts/scialpinismo/atlas.py`, comprese le cinque celle eliminate qui sopra, e conserva
sempre `ALP_E136_N083`. Le eccezioni restano attive nelle rigenerazioni successive.

Gli output vettoriali sono:

- `##_aree/_archivio_comune/atlante_griglia_v2.gpkg`, layer `celle_analisi` e `nuclei`;
- `08_Atlante/griglia.gpkg`, copia autonoma degli stessi layer;
- `08_Atlante/celle_analisi.geojson`, riquadri 35 × 35 km in WGS84.
- `08_Atlante/localita.geojson`, un punto di riferimento leggibile per ogni riquadro.

`celle_analisi` è il layer da usare per generare le aree. `nuclei` mostra invece le porzioni da 31 × 31 km senza sovrapposizione.

Il layer **Località OSM** viene compilato automaticamente leggendo tutti gli estratti
`.osm.pbf` presenti nell'archivio comune. Per ogni nucleo sceglie una località nota o
popolosa; se nessun dato OSM copre il riquadro usa il settore montuoso/geografico come
ripiego. I campi `source` e `sector` rendono verificabile la provenienza del nome. Un
nome assegnato manualmente con **Rinomina cella atlante** non viene sovrascritto.

## Generare le aree di analisi

1. Aggiungere `atlante_griglia_v2.gpkg` a QGIS.
2. Selezionare uno o due elementi del layer `celle_analisi`.
3. Avviare **Prepara celle selezionate** e attivare **Solo elementi selezionati**.
4. Il workflow crea una normale cartella in `##_aree/<cell_id>` con `area.json`, derivati e progetto QGIS.
5. Controllare il progetto e usare **Esporta offline**. La modalità predefinita produce un solo MBTiles per riquadro.

La preparazione resta limitata a due celle adiacenti per esecuzione, così DTM, OSM e resa cartografica possono essere verificati progressivamente. La griglia completa viene invece generata tutta insieme.

## CLI equivalente

```sh
07_Scripts/qgis_python.sh 07_Scripts/workflow.py grid
07_Scripts/qgis_python.sh 07_Scripts/workflow.py prepare-cells ALP_E143_N085 ALP_E144_N085
07_Scripts/qgis_python.sh 07_Scripts/workflow.py export '##_aree/ALP_E143_N085' --mode single
```

Per disattivare il filtro delle montagne usare `grid --all-cells`. Le opzioni `--min-elevation` e `--min-mountain-percent` corrispondono ai campi della finestra QGIS.

## Catalogo e quadro di unione

**Genera catalogo e quadro di unione** crea `08_Atlante/quadro_unione.qgz`, il PDF e i file GeoJSON del catalogo. Non genera automaticamente MBTiles: ogni riquadro viene esportato separatamente con il normale strumento **Esporta offline**.
