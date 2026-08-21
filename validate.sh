#!/bin/zsh

set -euo pipefail

cd "$(dirname "$0")"

validate_pdf() {
  local PDF="$1"

  echo ""
  echo "========================================"
  echo "$PDF"
  echo "========================================"

  echo ""
  echo "=== qpdf ==="
  qpdf --check "$PDF" || true

  echo ""
  echo "=== veraPDF PDF/UA-1 ==="
  verapdf -f ua1 --format text -v "$PDF" || true
}

if [[ $# -gt 0 ]]; then
  validate_pdf "$1"
else
  for PDF in pdf_production/*.pdf; do
    validate_pdf "$PDF"
  done
fi