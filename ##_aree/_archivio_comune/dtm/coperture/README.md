# Coperture geografiche leggere

Questa cartella contiene maschere in GeoJSON usate per limitare l'acquisizione
dei DTM remoti e quattro geometrie sorgente conservate per documentare la
provenienza. I file sono piccoli e versionati; non contengono quote né
sostituiscono i raster DTM originali.

Le geometrie sono espresse in coordinate geografiche WGS 84 / CRS84. Le
maschere operative sono richiamate dal registro locale `fonti.json`; i file
`*-region-01m-4326-2024.geojson` sono materiale sorgente e non sono letti
direttamente dal workflow.

## Maschere operative

| File | Ruolo e origine | Licenza e attribuzione |
| --- | --- | --- |
| `AT-BEV-VGD-gst-20251001.geojson` | Confine austriaco derivato da BEV Verwaltungsgrenzen, edizione 2025-10-01; limita il DTM ALS-DGM. | CC BY 4.0; attribuzione: `© BEV` |
| `CH-swissBOUNDARIES3D-2026.geojson` | Confine nazionale da swissBOUNDARIES3D, revisione 2026; limita swissALTI3D. | Geodati e geoservizi gratuiti swisstopo (OGD); attribuzione: `© swisstopo` |
| `FR-IGN-ADMIN-EXPRESS-20261015.geojson` | Maschera alpina derivata da IGN ADMIN EXPRESS 4.0, edizione 2026-10-15; limita RGE ALTI. | Licence Ouverte / Open Licence 2.0; attribuzione: `© IGN – ADMIN EXPRESS®` |
| `SI-OSM-20261019-BEV-20251001.geojson` | Confine sloveno ricavato dall'estratto Geofabrik del 2026-10-19 e ritagliato sul confine BEV del 2025-10-01; limita ARSO DMR. | Dati OpenStreetMap ODbL 1.0 e confini BEV CC BY 4.0; attribuzione: `© OpenStreetMap contributors, estratto Geofabrik; © BEV` |

## Geometrie sorgente GISCO

I file seguenti sono estratti nazionali del dataset GISCO Countries 2024,
scala 1:1 000 000 e CRS EPSG:4326:

- `AT-region-01m-4326-2024.geojson`;
- `CH-region-01m-4326-2024.geojson`;
- `FR-region-01m-4326-2024.geojson`;
- `SI-region-01m-4326-2024.geojson`.

La Commissione europea concede per questi dati un diritto d'uso e trattamento
non esclusivo e non trasferibile, subordinato all'uso non commerciale e alla
citazione della fonte. Consultare sempre le
[condizioni ufficiali GISCO per le unita amministrative](https://ec.europa.eu/eurostat/en/web/gisco/geodata/administrative-units)
prima di riutilizzare o ridistribuire i file.

Attribuzione richiesta:

> © EuroGeographics for the administrative boundaries

L'inclusione in questa repository documenta il materiale usato durante la
preparazione delle maschere e non estende né sostituisce i diritti concessi dai
rispettivi titolari. La licenza generale del progetto non prevale sulle
condizioni specifiche dei dataset elencati qui.
