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
# CAMPUS CONFIGURATION
# ============================================================

CAMPUSES = {
    "east": {
        "campus_name": "East Campus",
        "attn": "Records Request Department",
        "street": "11550 Lokanotosa Trail",
        "city_state_zip": "Orlando, FL 32817",
        "slug": "east-campus",
    },

    "main": {
        "campus_name": "Main Campus",
        "attn": "Records Request Department",
        "street": "301 W Amelia St",
        "city_state_zip": "Orlando, FL 32801",
        "slug": "main-campus",
    },

    "south": {
        "campus_name": "South Campus",
        "attn": "Records Department",
        "street": "2900 W Oak Ridge Rd",
        "city_state_zip": "Orlando, FL 32809",
        "slug": "south-campus",
    },

    "west": {
        "campus_name": "West Campus",
        "attn": "Records Department",
        "street": "2010 Ocoee Apopka Rd",
        "city_state_zip": "Ocoee, FL 34761",
        "slug": "west-campus",
    },
}


# ============================================================
# COMMAND-LINE OPTIONS
# ============================================================

parser = argparse.ArgumentParser(
    description="Build an OTC transcript request form with DocRaptor."
)

parser.add_argument(
    "--campus",
    required=True,
    choices=CAMPUSES.keys(),
    help="Campus version to generate: east, main, south, or west.",
)

parser.add_argument(
    "--production",
    action="store_true",
    help=(
        "Create a production DocRaptor document. "
        "This counts against the monthly document allowance."
    ),
)

args = parser.parse_args()

campus = CAMPUSES[args.campus]
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
# LOAD SOURCE
# ============================================================

html = HTML_FILE.read_text(encoding="utf-8")
css = CSS_FILE.read_text(encoding="utf-8")


# ============================================================
# INSERT CAMPUS-SPECIFIC CONTENT
# ============================================================

replacements = {
    "{{CAMPUS_NAME}}": campus["campus_name"],
    "{{ATTN}}": campus["attn"],
    "{{STREET}}": campus["street"],
    "{{CITY_STATE_ZIP}}": campus["city_state_zip"],
}

for placeholder, value in replacements.items():
    if placeholder not in html:
        sys.exit(
            f"Required template placeholder not found: {placeholder}"
        )

    html = html.replace(placeholder, value)


# Make sure no template placeholders remain accidentally.

remaining_placeholders = re.findall(r"\{\{[^}]+\}\}", html)

if remaining_placeholders:
    sys.exit(
        "Unresolved template placeholders remain:\n"
        + "\n".join(remaining_placeholders)
    )


# ============================================================
# EMBED CSS
# ============================================================

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


# ============================================================
# EMBED LOGO
# ============================================================

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
# OUTPUT DIRECTORIES / FILE
# ============================================================

TEST_OUTPUT_DIR = HERE / "pdf_test"
PRODUCTION_OUTPUT_DIR = HERE / "pdf_production"

if test_mode:
    output_dir = TEST_OUTPUT_DIR
    output_file = (
        output_dir
        / f"transcript-request-{campus['slug']}-test.pdf"
    )
    mode_label = "TEST"
else:
    output_dir = PRODUCTION_OUTPUT_DIR
    output_file = (
        output_dir
        / f"transcript-request-{campus['slug']}.pdf"
    )
    mode_label = "PRODUCTION"

# Create the output directory if it does not already exist.
output_dir.mkdir(parents=True, exist_ok=True)


# ============================================================
# DOCRAPTOR REQUEST
# ============================================================

payload = {
    "type": "pdf",
    "test": test_mode,

    "name": (
        "Orange Technical College - "
        f"{campus['campus_name']} Transcript Request"
    ),

    # Keep using the exact pipeline that produced our
    # successful PDF/UA test.
    "pipeline": "10.1",

    "document_content": html,

    "prince_options": {
        "profile": "PDF/UA-1",
        "media": "print",
        "no_subset_fonts": True,
    },
}


# ============================================================
# AUTHENTICATION
# ============================================================

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
# BUILD
# ============================================================

print()
print(f"Campus: {campus['campus_name']}")
print(f"Mode:   {mode_label}")
print()
print("Sending document to DocRaptor...")


try:
    with urllib.request.urlopen(request, timeout=120) as response:
        pdf_bytes = response.read()
        page_count = response.headers.get(
            "X-DocRaptor-Num-Pages"
        )

except urllib.error.HTTPError as error:
    body = error.read().decode(
        "utf-8",
        errors="replace",
    )

    print()
    print(f"DocRaptor returned HTTP {error.code}:")
    print()
    print(body)
    print()

    sys.exit(1)

except urllib.error.URLError as error:
    sys.exit(
        f"\nCould not connect to DocRaptor:\n{error}\n"
    )

except Exception as error:
    sys.exit(
        f"\nDocRaptor request failed:\n{error}\n"
    )


# ============================================================
# VERIFY RESPONSE LOOKS LIKE PDF
# ============================================================

if not pdf_bytes.startswith(b"%PDF-"):
    sys.exit(
        "\nDocRaptor returned data that does not appear "
        "to be a PDF.\n"
    )


# ============================================================
# SAVE
# ============================================================

output_file.write_bytes(pdf_bytes)

print()
print(f"Created: {output_file}")

if page_count:
    print(f"Pages:   {page_count}")

if test_mode:
    print("Mode:    TEST — does not use a production credit.")
else:
    print("Mode:    PRODUCTION — uses one production credit.")

print()