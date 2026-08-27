#!/bin/zsh

set -euo pipefail

cd "$(dirname "$0")"

PRINCE="${PRINCE:-$HOME/prince-16.2/bin/prince}"

OUTPUT_DIR="pdf_test"
OUTPUT_FILE="$OUTPUT_DIR/ged-consent-form-local-test.pdf"

mkdir -p "$OUTPUT_DIR"

"$PRINCE" \
  --pdf-forms \
  --pdf-profile=PDF/UA-1 \
  --no-subset-fonts \
  ged-consent-form.html \
  -o "$OUTPUT_FILE"

echo
echo "Created: $OUTPUT_FILE"
echo