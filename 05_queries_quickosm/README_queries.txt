QUERIES QUICKOSM — ISTRUZIONI
==============================

1. Inquadra l'area in QGIS.
2. Apri Vector > QuickOSM > QuickOSM.
3. Vai nella scheda Query / Raw query.
4. Imposta Canvas extent (oppure usa un layer area_lavoro).
5. Apri il file .txt desiderato in questa cartella, copia il contenuto e incollalo nella query.
6. Imposta il timeout nelle opzioni di QuickOSM, ad esempio 60-90 s.
7. Esegui la query e salva il risultato in aree/<nome_zona>/vettori/ come GeoPackage.

REGOLE IMPORTANTI
-----------------
- Le query usano {{bbox}}: QuickOSM lo sostituisce usando l'estensione scelta.
- Non aggiungere [out:json][timeout:...]; se QuickOSM gestisce output e timeout separatamente.
- Usa aree limitate per ridurre timeout e risultati inutili.
- Verifica la tabella attributi: highway, sac_scale, name, ref, surface e tracktype.
- L'assenza di sac_scale non implica che un sentiero sia facile.
- I dati OpenStreetMap sono collaborativi: verifica sempre le informazioni importanti con fonti locali/ufficiali.
