#!/bin/zsh

set -euo pipefail

cd "$(dirname "$0")"

PDF_DIR="forms/transcript-request-forms/pdf_production"

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
  PDFs=("$PDF_DIR"/*.pdf)

  if [[ ! -e "${PDFs[1]}" ]]; then
    echo "No production PDFs found in $PDF_DIR"
    exit 1
  fi

  for PDF in "${PDFs[@]}"; do
    validate_pdf "$PDF"
  done
fi