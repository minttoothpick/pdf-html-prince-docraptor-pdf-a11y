#!/usr/bin/env python3

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

HERE = Path(__file__).resolve().parent

HTML_FILE = HERE / "transcript-form.html"
CSS_FILE = HERE / "transcript-form.css"
LOGO_FILE = HERE / "assets" / "otc-career-logo.png"


# ============================================================
# COMMAND-LINE OPTIONS
# ============================================================

parser = argparse.ArgumentParser(
    description="Build the OTC transcript form with DocRaptor."
)

parser.add_argument(
    "--production",
    action="store_true",
    help=(
        "Create a non-test DocRaptor document. "
        "This counts against the monthly document allowance."
    ),
)

args = parser.parse_args()

test_mode = not args.production


# ============================================================
# API KEY
# ============================================================

api_key = os.environ.get("DOCRAPTOR_API_KEY")

if not api_key:
    sys.exit(
        "\nDOCRAPTOR_API_KEY is not set.\n\n"
        "Run this first:\n\n"
        '  read -s "DOCRAPTOR_API_KEY?DocRaptor API key: "\n'
        "  export DOCRAPTOR_API_KEY\n"
        "  echo\n"
    )


# ============================================================
# CHECK SOURCE FILES
# ============================================================

for path in (HTML_FILE, CSS_FILE, LOGO_FILE):
    if not path.exists():
        sys.exit(f"Required file not found: {path}")


# ============================================================
# BUILD SELF-CONTAINED HTML
# ============================================================

html = HTML_FILE.read_text(encoding="utf-8")
css = CSS_FILE.read_text(encoding="utf-8")


# Replace:
#
# <link rel="stylesheet" href="transcript-form.css">
#
# with the actual CSS.

stylesheet_pattern = re.compile(
    r'<link\b'
    r'(?=[^>]*\brel=["\']stylesheet["\'])'
    r'(?=[^>]*\bhref=["\']transcript-form\.css["\'])'
    r'[^>]*>',
    flags=re.IGNORECASE,
)

html, css_replacements = stylesheet_pattern.subn(
    "<style>\n" + css + "\n</style>",
    html,
    count=1,
)

if css_replacements != 1:
    sys.exit(
        "Could not find the transcript-form.css <link> element "
        "in transcript-form.html."
    )


# Convert the local OTC logo into an embedded PNG data URI.

logo_bytes = LOGO_FILE.read_bytes()
logo_base64 = base64.b64encode(logo_bytes).decode("ascii")
logo_uri = f"data:image/png;base64,{logo_base64}"

html, logo_replacements = re.subn(
    r'src=["\']assets/otc-career-logo\.png["\']',
    f'src="{logo_uri}"',
    html,
    count=1,
    flags=re.IGNORECASE,
)

if logo_replacements != 1:
    sys.exit(
        "Could not find assets/otc-career-logo.png "
        "in transcript-form.html."
    )


# ============================================================
# DOCRAPTOR REQUEST
# ============================================================

payload = {
    "type": "pdf",

    # True = unlimited test document, but watermarked.
    # False = production document, counts against plan allowance.
    "test": test_mode,

    "name": "OTC South Campus Transcript Request",

    # Pin the current DocRaptor pipeline for reproducible output.
    # Pipeline 10.1 currently uses Prince 15.1.
    "pipeline": "10.1",

    "document_content": html,

    "prince_options": {
        # Generate tagged PDF/UA output.
        "profile": "PDF/UA-1",

        # Use print CSS.
        "media": "print",

        # We already found locally that disabling font subsetting
        # eliminated the CIDSet PDF/UA failure.
        "no_subset_fonts": True,
    },
}


# DocRaptor uses HTTP Basic authentication:
# API key = username
# password = blank

credentials = base64.b64encode(
    f"{api_key}:".encode("utf-8")
).decode("ascii")


request = urllib.request.Request(
    "https://api.docraptor.com/docs",
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Basic {credentials}",
        "User-Agent": "OTC-PDF-Remediation/1.0",
    },
    method="POST",
)


# ============================================================
# OUTPUT
# ============================================================

if test_mode:
    output_file = HERE / "docraptor-test.pdf"
    mode_label = "TEST"
else:
    output_file = HERE / "docraptor-production.pdf"
    mode_label = "PRODUCTION"


print()
print(f"Sending {mode_label} document to DocRaptor...")


try:
    with urllib.request.urlopen(request, timeout=120) as response:
        pdf_bytes = response.read()
        page_count = response.headers.get("X-DocRaptor-Num-Pages")

except urllib.error.HTTPError as error:
    body = error.read().decode("utf-8", errors="replace")

    print()
    print(f"DocRaptor returned HTTP {error.code}:")
    print()
    print(body)
    print()

    sys.exit(1)

except urllib.error.URLError as error:
    sys.exit(f"\nCould not connect to DocRaptor:\n{error}\n")

except Exception as error:
    sys.exit(f"\nDocRaptor request failed:\n{error}\n")


# Basic safety check: a PDF should begin with %PDF-

if not pdf_bytes.startswith(b"%PDF-"):
    sys.exit(
        "\nDocRaptor returned data that does not appear to be a PDF.\n"
    )


output_file.write_bytes(pdf_bytes)


print(f"Created: {output_file}")

if page_count:
    print(f"Pages:   {page_count}")

if test_mode:
    print("Mode:    TEST")
    print("Note:    Test PDFs are watermarked.")
    print()
    print("When everything looks correct, run:")
    print()
    print("  python3 build_docraptor.py --production")
else:
    print("Mode:    PRODUCTION")
    print("Note:    This uses one document from your monthly allowance.")

print()