# Guida rapida — workflow 1.3

Per installazione, requisiti minimi e primo avvio da un clone GitHub, vedere
[`HOWTO.md`](../HOWTO.md).

## Preparare o aggiornare una zona

1. Avvia `Avvia_Scialpinismo.command`.
2. Verifica che DTM e pacchetto OSM coprano la zona e il margine tecnico. Gli originali comuni stanno in `##_aree/_archivio_comune/dtm/originali`; non copiarli nelle singole aree.
3. Per una zona nuova usa **Prepara area**. Per l’atlante seleziona una cella, oppure al massimo due celle adiacenti, e usa **Prepara celle selezionate**.
4. Per una zona esistente usa **Aggiorna area** sul relativo `area.json`.
5. Controlla il progetto agli zoom 12–16, soprattutto edifici, aree abitate, rifugi, nomi e continuità del rilievo.
6. Usa **Esporta offline** e scegli il range richiesto. Il default proposto è 12–16.
7. Copia sul dispositivo tutti e soli i file elencati in `output/mbtiles/LEGGIMI_PRODUZIONE_CORRENTE.txt` e collaudali in modalità aereo.

Il workflow è intenzionalmente sequenziale: non esiste un comando che prepari o esporti tutto l’arco alpino. Ogni esecuzione riguarda una zona; due celle adiacenti servono soltanto a verificare la continuità.

L’export crea per impostazione predefinita un solo file MBTiles per area. **Suddividi per peso** è una scelta opzionale; quando viene selezionata, il limite MB deve essere inserito nella finestra. Il vecchio limite automatico di 600 MB non è più applicato.

## DTM: base e integrazioni locali

`hrdtm5m` è la base continua italiana. Le fonti Alto Adige 2,5 m e Veneto 5 m registrate in `fonti.json` vengono sovrapposte automaticamente quando intersecano la zona. Per i riquadri di confine, il DMR 1 m ARSO della Slovenia, l'ALS-DGM 1 m BEV dell'Austria e swissALTI3D 2 m di swisstopo vengono acquisiti automaticamente e conservati nella cache comune; l'OSM resta indipendente e non viene esteso da queste integrazioni. Il motore:

- conserva anche il DTM base sotto il dato più fine;
- riproietta ogni fonte nel CRS metrico dell’area;
- allinea le celle alla stessa griglia;
- usa `-9999` come NoData, quindi il dato fine sostituisce la base solo dove è valido;
- per ARSO scarica una sola volta i tasselli da 10 km necessari, senza acquisire l'intero DTM sloveno;
- per BEV individua i COG correnti tramite l'indice ATOM, ne legge via HTTP Range soltanto la finestra richiesta e la conserva in tasselli da 10 km, senza scaricare i file da 50 km completi;
- per swisstopo interroga l'API STAC, scarica una sola volta i piccoli COG 2 m da 1 km che intersecano l'area e li conserva in `dtm/originali/swissalti3d_2m`; la versione 0,5 m non viene usata perché sovradimensionata rispetto alla griglia del progetto;
- corregge le sole micro-cuciture di riproiezione fra DTM confinanti quando esiste una quota valida entro 20 m; i vuoti altimetrici più ampi restano NoData e continuano a bloccare l’area;
- se un raster è memorizzato su una griglia più fitta della sua risoluzione reale, lo normalizza prima al passo nativo e soltanto dopo lo interpola sulla griglia comune: questo evita pendenze e curve “a scacchiera” senza scartare i DTM realmente più precisi;
- chiude automaticamente le sottili fessure di giunzione tra DTM nazionali confinanti fino a 60 m; i vuoti territoriali più estesi restano NoData e continuano a bloccare l'export;
- blocca l’export se restano celle senza quota nel perimetro e nel margine tecnico;
- può accettare una copertura parziale usando il campo **NoData DTM massimo (%)** nelle finestre **Prepara area**, **Aggiorna area** o **Esporta offline**. La scelta viene scritta automaticamente in `area.json`; se specificata durante l’export, il plugin aggiorna prima i derivati. I NoData restano vuoti e vengono dichiarati nei metadati, senza quote sintetiche.

Prima di aggiungere un nuovo DTM, documentare almeno CRS, passo, NoData, unità verticali, copertura, origine e licenza in `fonti.json`. Un WMS o un hillshade non sostituiscono un raster DTM numerico.

## Grafica corrente

- A zoom 12–15 le aree OSM abitate aiutano a leggere nuclei e conglomerati; nel dettaglio compaiono gli edifici.
- A zoom 13–15 i testi di rifugi, paesi/città e strade sono al 125% della dimensione ordinaria. Zoom 12 e zoom 16+ mantengono le dimensioni previste dalla gerarchia precedente.
- A zoom 15 compaiono le quote direttrici ogni 100 m; da zoom 16 anche le intermedie.
- Il massimo zoom non aumenta l’accuratezza del DTM. Zoom 18 richiede copertura verificata nativa sotto 5 m.

I master QML in `03_styles/auto_*.qml` sono sincronizzati dal codice per strade, toponimi e rifugi, così le generazioni future usano la stessa tipografia.

## Nomi e output

Le nuove edizioni usano timestamp UTC leggibili, senza suffissi casuali, per esempio:

`ALP_E127_N073_agordino-san-martino_20261019T154743Z_01_z12-16.mbtiles`

Le cache comuni esplicitano CRS, risoluzione o bounding box. Non rinominare a mano un MBTiles senza aggiornare catalogo, metadati e checksum.

## Controlli

```sh
07_Scripts/qgis_python.sh 07_Scripts/tests/test_workflow.py
07_Scripts/qgis_python.sh 07_Scripts/tests/test_atlas.py
07_Scripts/qgis_python.sh 07_Scripts/verifica_workspace.py
```

Approfondimenti: `HANDOFF_PROGETTAZIONE_MAPPE.md`, `06_documentazione/ATLANTE_ALPINO.md` e `06_documentazione/COPERTURA_DTM_LAGO_MAGGIORE_FRIULI.txt`.
