#!/bin/sh
# Upload riproducibile di un archivio PMTiles nel bucket Cloudflare R2.
#
# Preparazione una tantum (le credenziali non vanno mai scritte qui):
#   1. eseguire `rclone config`;
#   2. creare un remote S3 chiamato `tracciabianca-r2`;
#   3. scegliere provider Cloudflare e inserire Access Key, Secret Key e
#      endpoint R2 dell'account.
#
# Uso:
#   07_Scripts/upload_pmtiles_r2.sh percorso/mappa.pmtiles

set -eu

# Questi valori descrivono il servizio attuale. Possono essere sostituiti
# tramite variabili d'ambiente senza modificare lo script; sara' utile quando
# R2 verra' collegato a un dominio personalizzato.
RCLONE_REMOTE="${RCLONE_REMOTE:-tracciabianca-r2}"
R2_BUCKET="${R2_BUCKET:-tracciabianca-pmtiles}"
R2_PUBLIC_BASE="${R2_PUBLIC_BASE:-https://pub-3e95fc6969fb409e83c7226568f91a90.r2.dev}"
R2_CORS_ORIGIN="${R2_CORS_ORIGIN:-https://tel-la.github.io}"
CACHE_CONTROL="public, max-age=31536000, immutable"

usage() {
  echo "Uso: $(basename "$0") FILE.pmtiles"
}

if [ "$#" -eq 1 ] && { [ "$1" = "-h" ] || [ "$1" = "--help" ]; }; then
  usage
  exit 0
fi
if [ "$#" -ne 1 ]; then
  usage >&2
  exit 2
fi

PMTILES_FILE="$1"

# Controlli locali: fallire prima di avviare un trasferimento costoso.
command -v rclone >/dev/null 2>&1 || {
  echo "Errore: rclone non e' installato." >&2
  exit 1
}
command -v curl >/dev/null 2>&1 || {
  echo "Errore: curl non e' installato." >&2
  exit 1
}
[ -s "$PMTILES_FILE" ] || {
  echo "Errore: file assente o vuoto: $PMTILES_FILE" >&2
  exit 1
}
case "$PMTILES_FILE" in
  *.pmtiles) ;;
  *)
    echo "Errore: il file deve avere estensione .pmtiles." >&2
    exit 1
    ;;
esac

# Il remote contiene le credenziali nel file di configurazione di rclone,
# fuori dal repository. Object Read & Write deve essere limitato al bucket.
if ! rclone listremotes 2>/dev/null | grep -Fqx "$RCLONE_REMOTE:"; then
  echo "Errore: configura prima il remote rclone '$RCLONE_REMOTE'." >&2
  echo "Endpoint: https://a8db8dd2867748a35ca0ef6a94e19059.r2.cloudflarestorage.com" >&2
  exit 1
fi

OBJECT_NAME="$(basename "$PMTILES_FILE")"
FILE_SIZE="$(wc -c < "$PMTILES_FILE" | tr -d '[:space:]')"
DESTINATION="$RCLONE_REMOTE:$R2_BUCKET/$OBJECT_NAME"
PUBLIC_URL="${R2_PUBLIC_BASE%/}/$OBJECT_NAME"

echo "Caricamento di $OBJECT_NAME ($FILE_SIZE byte)..."

# Oltre 100 MiB rclone usa il multipart. Le parti da 64 MiB vengono inviate
# quattro alla volta. --immutable impedisce di sovrascrivere per errore un
# oggetto che usa gia' lo stesso nome versionato.
rclone copyto "$PMTILES_FILE" "$DESTINATION" \
  --s3-no-check-bucket \
  --s3-upload-cutoff 100Mi \
  --s3-chunk-size 64Mi \
  --s3-upload-concurrency 4 \
  --immutable \
  --metadata \
  --metadata-set "cache-control=$CACHE_CONTROL" \
  --metadata-set "content-type=application/octet-stream" \
  --progress \
  --stats 10s

# PMTiles dipende dalle richieste HTTP Range. Il test legge soltanto i primi
# 16 KiB e verifica anche CORS, dimensione totale e cache immutabile.
HEADERS_FILE="$(mktemp -t tracciabianca-r2-headers.XXXXXX)"
trap 'rm -f "$HEADERS_FILE"' EXIT HUP INT TERM

HTTP_STATUS="$(curl -sS \
  -D "$HEADERS_FILE" \
  -o /dev/null \
  -w '%{http_code}' \
  -H "Origin: $R2_CORS_ORIGIN" \
  -H 'Range: bytes=0-16383' \
  "$PUBLIC_URL")"
HEADERS="$(tr -d '\r' < "$HEADERS_FILE")"

require_header() {
  printf '%s\n' "$HEADERS" | grep -Fqi "$1" || {
    echo "Errore: header atteso non trovato: $1" >&2
    exit 1
  }
}

[ "$HTTP_STATUS" = "206" ] || {
  echo "Errore: risposta HTTP $HTTP_STATUS invece di 206." >&2
  exit 1
}
require_header "Content-Range: bytes 0-16383/$FILE_SIZE"
require_header "Accept-Ranges: bytes"
require_header "Access-Control-Allow-Origin: $R2_CORS_ORIGIN"
require_header "Cache-Control: $CACHE_CONTROL"

echo "Upload e verifica completati: HTTP 206, Range, CORS e cache corretti."
echo "URL pubblico: $PUBLIC_URL"
echo "Ricorda di aggiungere il file al manifest PMTiles prima del publishing."
