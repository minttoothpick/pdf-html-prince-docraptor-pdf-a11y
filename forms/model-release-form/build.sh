#!/bin/zsh

set -euo pipefail

cd "$(dirname "$0")"

PRINCE="${PRINCE:-$HOME/prince-16.2/bin/prince}"

OUTPUT_DIR="pdf_test"
OUTPUT_FILE="$OUTPUT_DIR/model-release-form-local-test.pdf"

mkdir -p "$OUTPUT_DIR"

"$PRINCE" \
  --pdf-forms \
  --pdf-profile=PDF/UA-1 \
  --no-subset-fonts \
  model-release-form.html \
  -o "$OUTPUT_FILE"

echo
echo "Created: $OUTPUT_FILE"
echo
