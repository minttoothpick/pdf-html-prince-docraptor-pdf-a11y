# OTC Transcript Request PDF Generator

Generates accessible, fillable transcript request PDFs for Orange Technical College campuses from one shared semantic HTML/CSS source.

Campus-specific names and mailing addresses are inserted automatically by `build_docraptor.py`.

## Gettin it started

`source .venv/bin/activate`

## Files

- `transcript-form.html` — shared form markup
- `transcript-form.css` — shared PDF layout and styles
- `build_docraptor.py` — generates campus-specific PDFs through DocRaptor
- `validate.sh` — runs qpdf and veraPDF PDF/UA-1 validation
- `build.sh` — original local Prince build, retained for reference/testing
- `assets/` — shared images
- `pdf_test/` — DocRaptor test PDFs
- `pdf_production/` — final production PDFs

## Requirements

- Python 3
- DocRaptor account and API key
- qpdf and veraPDF for validation
- Prince is optional; `build.sh` is retained only for local/reference use

## Set the DocRaptor API Key

Before generating PDFs, load the API key into the current Terminal session:

```bash
read -s "DOCRAPTOR_API_KEY?DocRaptor API key: "
export DOCRAPTOR_API_KEY
echo
```

Do not store the API key in the source files or commit it to version control.

## Generate Test PDFs

Test PDFs are watermarked and do not use production credits.

Generate all four campuses:

```bash
for campus in east main south west; do
  python3 build_docraptor.py --campus "$campus"
done
```

Outputs are saved in:

```text
pdf_test/
```

Review all four PDFs before generating production versions.

## Generate Production PDFs

After the test PDFs look correct, generate all four final PDFs:

```bash
for campus in east main south west; do
  python3 build_docraptor.py --campus "$campus" --production
done
```

Outputs are saved in:

```text
pdf_production/
```

Production documents count against the DocRaptor account's document allowance.

## Validate PDFs

Validate all production PDFs:

```bash
./validate.sh
```

Or validate one specific PDF:

```bash
./validate.sh pdf_production/transcript-request-east-campus.pdf
```

Final PDFs should pass:

- qpdf structural validation
- veraPDF PDF/UA-1 validation

## Updating the Forms

For changes that apply to every campus, edit:

```text
transcript-form.html
transcript-form.css
```

For campus names, mailing addresses, or Records Department wording, edit the `CAMPUSES` configuration in:

```text
build_docraptor.py
```

Current campus variants are:

- East Campus
- Main Campus
- South Campus
- West Campus

Always generate and review test PDFs first, then generate production PDFs.
