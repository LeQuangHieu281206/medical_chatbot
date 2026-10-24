#!/usr/bin/env bash
# Dong goi du an thanh file zip de chuyen sang may Windows
# (hoac dinh kem vao GitHub Release).
#
# Dung: bash scripts/pack_windows.sh
#
# Zip chua: code (app/, scripts/), requirements.txt, README.md,
#   app/db/chroma_db (vector DB - khong can ingest lai),
#   models/ner_model.zip (model NER), data/processed/.
# Khong chua: .venv, data/raw, __pycache__, models/ner_model/ (ban giai nen).
#
# Luu y: dong Streamlit/Ollama app truoc khi pack de chroma_db khong bi ghi.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/medical_chatbot_windows.zip"
PKG_NAME="medical_chatbot"

cd "$ROOT"

# Kiem tra cac phan quan trong truoc khi dong goi
for f in requirements.txt models/ner_model.zip app/db/chroma_db data/processed; do
    if [ ! -e "$f" ]; then
        echo "CANH BAO: thieu $f - goi zip se khong day du." >&2
    fi
done

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/$PKG_NAME"

# Code + tai lieu
cp -r app "$STAGE/$PKG_NAME/app"
cp -r scripts "$STAGE/$PKG_NAME/scripts"
mkdir -p "$STAGE/$PKG_NAME/data"
cp -r data/processed "$STAGE/$PKG_NAME/data/processed"
mkdir -p "$STAGE/$PKG_NAME/models"
cp models/ner_model.zip "$STAGE/$PKG_NAME/models/"
cp requirements.txt "$STAGE/$PKG_NAME/"
if [ -f README.md ]; then
    cp README.md "$STAGE/$PKG_NAME/"
fi

# Don dep file cache Python
find "$STAGE/$PKG_NAME" -type d -name "__pycache__" -prune -exec rm -rf {} +
find "$STAGE/$PKG_NAME" -type f -name "*.pyc" -delete

rm -f "$OUT"
if command -v zip >/dev/null 2>&1; then
    (cd "$STAGE" && zip -qr "$OUT" "$PKG_NAME")
else
    # Khong co lenh zip thi dung python3 (mac dinh co tren Linux)
    python3 - "$STAGE" "$OUT" <<'PY'
import os, sys, zipfile
stage, out = sys.argv[1], sys.argv[2]
top = os.path.join(stage, "medical_chatbot")
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for root, _dirs, files in os.walk(top):
        for name in files:
            p = os.path.join(root, name)
            z.write(p, os.path.relpath(p, stage))
PY
fi

echo ""
echo "Da tao: $OUT"
du -sh "$OUT"
echo ""
echo "Tiep theo: dinh kem file nay vao GitHub Release (Releases -> Draft a new release)"
echo "hoac chep sang may Windows bang USB/cloud."
