#!/bin/sh
set -e

HERE="$(cd "$(dirname "$0")" && pwd)"

prince \
  --pdf-forms \
  --pdf-profile=PDF/UA-1 \
  --no-subset-fonts \
  "$HERE/transcript-form.html" \
  -o "$HERE/transcript-form.pdf"

echo "Created: $HERE/transcript-form.pdf"