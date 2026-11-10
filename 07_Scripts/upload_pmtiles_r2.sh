#!/bin/sh
# Upload e sincronizzazione PMTiles per la webmap TracciaBianca.
#
# Con uno o piu' argomenti carica i file su Cloudflare R2; senza argomenti
# sincronizza soltanto il manifest con il contenuto attuale del bucket. In
# entrambi i casi il manifest risultante viene pubblicato su R2 e diventa
# visibile nella webmap online al successivo caricamento della pagina.
#
# Uso:
#   07_Scripts/upload_pmtiles_r2.sh mappa.pmtiles [altra.pmtiles ...]
#   07_Scripts/upload_pmtiles_r2.sh              # solo sincronizzazione

set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RCLONE_REMOTE="${RCLONE_REMOTE:-tracciabianca-r2}"
R2_BUCKET="${R2_BUCKET:-tracciabianca-pmtiles}"
R2_PUBLIC_BASE="${R2_PUBLIC_BASE:-https://pub-3e95fc6969fb409e83c7226568f91a90.r2.dev}"
R2_CORS_ORIGIN="${R2_CORS_ORIGIN:-https://tel-la.github.io}"

SOURCE_MANIFEST="$SCRIPT_DIR/interactive_map_src/webmap/pmtiles-manifest.json"
PUBLIC_MANIFEST="$PROJECT_ROOT/docs/webmap/pmtiles-manifest.json"
ATLAS="$PROJECT_ROOT/docs/data/atlas.json"
SYNC_HELPER="$SCRIPT_DIR/sync_pmtiles_manifest.py"

PMTILES_CACHE="public, max-age=31536000, immutable"
MANIFEST_CACHE="no-cache, max-age=0, must-revalidate"

usage() {
  cat <<EOF
Uso: $(basename "$0") [FILE.pmtiles ...]

Con file:    upload multipart, verifica e sincronizzazione del manifest.
Senza file:  riconcilia il manifest con i PMTiles gia' presenti su R2.
EOF
}

if [ "$#" -eq 1 ] && { [ "$1" = "-h" ] || [ "$1" = "--help" ]; }; then
  usage
  exit 0
fi

# Dipendenze minime e configurazione locale delle credenziali.
for command_name in rclone curl python3; do
  command -v "$command_name" >/dev/null 2>&1 || {
    echo "Errore: comando '$command_name' non trovato." >&2
    exit 1
  }
done
if ! rclone listremotes 2>/dev/null | grep -Fqx "$RCLONE_REMOTE:"; then
  echo "Errore: configura prima il remote rclone '$RCLONE_REMOTE'." >&2
  exit 1
fi

# Validare tutti gli input prima di iniziare: se un percorso e' errato non
# viene caricato neppure il primo file della serie.
for pmtiles_file in "$@"; do
  [ -s "$pmtiles_file" ] || {
    echo "Errore: file assente o vuoto: $pmtiles_file" >&2
    exit 1
  }
  case "$pmtiles_file" in
    *.pmtiles) ;;
    *)
      echo "Errore: estensione diversa da .pmtiles: $pmtiles_file" >&2
      exit 1
      ;;
  esac
done

TEMP_DIR="$(mktemp -d -t tracciabianca-r2.XXXXXX)"
trap 'rm -rf "$TEMP_DIR"' EXIT HUP INT TERM

require_header() {
  headers="$1"
  expected="$2"
  printf '%s\n' "$headers" | grep -Fqi "$expected" || {
    echo "Errore: header atteso non trovato: $expected" >&2
    exit 1
  }
}

upload_and_verify() {
  pmtiles_file="$1"
  object_name="$(basename "$pmtiles_file")"
  file_size="$(wc -c < "$pmtiles_file" | tr -d '[:space:]')"
  destination="$RCLONE_REMOTE:$R2_BUCKET/$object_name"
  public_url="${R2_PUBLIC_BASE%/}/$object_name"

  echo "Caricamento di $object_name ($file_size byte)..."
  rclone copyto "$pmtiles_file" "$destination" \
    --s3-no-check-bucket \
    --s3-upload-cutoff 100Mi \
    --s3-chunk-size 64Mi \
    --s3-upload-concurrency 4 \
    --immutable \
    --metadata \
    --metadata-set "cache-control=$PMTILES_CACHE" \
    --metadata-set "content-type=application/octet-stream" \
    --progress \
    --stats 10s

  # Il viewer usa richieste Range: leggere 16 KiB prova dimensione, CORS e
  # metadati senza scaricare l'intero archivio.
  range_end=16383
  if [ "$file_size" -le "$range_end" ]; then
    range_end=$((file_size - 1))
  fi
  headers_file="$TEMP_DIR/pmtiles-headers.txt"
  http_status="$(curl -sS \
    -D "$headers_file" \
    -o /dev/null \
    -w '%{http_code}' \
    -H "Origin: $R2_CORS_ORIGIN" \
    -H "Range: bytes=0-$range_end" \
    "$public_url")"
  headers="$(tr -d '\r' < "$headers_file")"

  [ "$http_status" = "206" ] || {
    echo "Errore: risposta HTTP $http_status invece di 206." >&2
    exit 1
  }
  require_header "$headers" "Content-Range: bytes 0-$range_end/$file_size"
  require_header "$headers" "Accept-Ranges: bytes"
  require_header "$headers" "Access-Control-Allow-Origin: $R2_CORS_ORIGIN"
  require_header "$headers" "Cache-Control: $PMTILES_CACHE"
  echo "Verifica PMTiles completata: $public_url"
}

for pmtiles_file in "$@"; do
  upload_and_verify "$pmtiles_file"
done

# R2 e' la fonte autorevole. La lista include dimensioni e nomi degli oggetti;
# il helper ricava cella e zoom dal contratto dei nomi versionati, aggiunge le
# nuove celle e rimuove dal manifest quelle senza piu' alcun PMTiles su R2.
REMOTE_LIST="$TEMP_DIR/r2-pmtiles.json"
rclone lsjson "$RCLONE_REMOTE:$R2_BUCKET" \
  --files-only \
  --max-depth 1 \
  --include '*.pmtiles' > "$REMOTE_LIST"

python3 "$SYNC_HELPER" \
  --atlas "$ATLAS" \
  --source-manifest "$SOURCE_MANIFEST" \
  --public-manifest "$PUBLIC_MANIFEST" < "$REMOTE_LIST"

# Il manifest cambia nel tempo, quindi non deve usare la cache immutabile degli
# archivi. --ignore-times forza l'aggiornamento anche se la dimensione coincide.
rclone copyto "$SOURCE_MANIFEST" \
  "$RCLONE_REMOTE:$R2_BUCKET/pmtiles-manifest.json" \
  --s3-no-check-bucket \
  --ignore-times \
  --metadata \
  --metadata-set "cache-control=$MANIFEST_CACHE" \
  --metadata-set "content-type=application/json"

# Ultima verifica: il JSON pubblico su R2 deve essere identico a quello locale.
REMOTE_MANIFEST="$TEMP_DIR/public-pmtiles-manifest.json"
curl -fsS \
  -H "Origin: $R2_CORS_ORIGIN" \
  -H 'Cache-Control: no-cache' \
  "${R2_PUBLIC_BASE%/}/pmtiles-manifest.json?ts=$(date +%s)" \
  -o "$REMOTE_MANIFEST"
cmp "$SOURCE_MANIFEST" "$REMOTE_MANIFEST" || {
  echo "Errore: il manifest pubblico R2 non coincide con quello locale." >&2
  exit 1
}

echo "Manifest R2 pubblicato e verificato."
echo "Webmap: https://tel-la.github.io/TracciaBianca/webmap/"
