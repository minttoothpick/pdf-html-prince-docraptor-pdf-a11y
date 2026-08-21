#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")"
PDF="${1:-transcript-form.pdf}"

echo "=== qpdf ==="
qpdf --check "$PDF" || true

echo ""
echo "=== veraPDF PDF/UA-1 ==="
verapdf -f ua1 --format text -v "$PDF" || true
