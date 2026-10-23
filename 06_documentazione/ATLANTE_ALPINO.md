# Atlante alpino — griglia delle aree di analisi

La griglia `ALP35_OVERLAP2_LAEA_v2` serve a pianificare e creare le aree cartografiche dell’arco alpino italiano dal Lago Maggiore al Friuli.

## Geometria

- CRS della griglia: EPSG:3035.
- Riquadro finale di analisi: 35 × 35 km.
- Nucleo esclusivo: 31 × 31 km.
- Fascia aggiunta: 2 km su ciascun lato del nucleo.
- Passo della griglia: 31 km.
- Sovrapposizione tra due riquadri adiacenti: 4 km complessivi.

La fascia di 2 km appartiene a ciascun riquadro. Per questo due riquadri confinanti condividono 2 km da una parte e 2 km dall’altra, cioè una fascia comune di 4 km.

## Creare la griglia in QGIS

1. Avviare `Avvia_Scialpinismo.command`.
2. Aprire **Plugin → Scialpinismo locale → Crea o estendi griglia atlante**.
3. Lasciare vuota l’estensione per usare il dominio predefinito Lago Maggiore–Friuli.
4. Lasciare attivo **Conserva solo riquadri con montagne rilevate dal DTM**.
5. Usare normalmente quota minima 600 m e superficie minima sopra quota 1%.

Il filtro campiona il DTM verificato, preferibilmente `hrdtm5m`, e conserva i riquadri che contengono una superficie montana significativa. Estensione e soglie sono modificabili dalla finestra QGIS.

La composizione editoriale applica inoltre le eccezioni concordate: esclude
`ALP_E135_N080`, `ALP_E144_N086`, `ALP_E146_N082` e `ALP_E147_N082`, e conserva
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
