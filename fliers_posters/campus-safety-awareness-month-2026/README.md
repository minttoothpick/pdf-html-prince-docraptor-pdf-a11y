# OTC Campus Safety poster: accessible PDF workflow

The production PDF should be generated with DocRaptor/Prince using the
`PDF/UA-1` profile. Do not use a browser's **Print to PDF** command for the
website download; browser output can preserve the visual design while losing
the document tags, alternative text, language, and reliable reading order.

## Source of truth

- Edit `poster-v2.template.html`.
- Keep images and fonts in `assets/`.
- Run `node build.mjs` to create the self-contained HTML in `output/`.
- Do not hand-edit the generated HTML; rebuilding would overwrite those edits.

The HTML already includes a document language and title, one logical heading
outline, semantic sections and lists, meaningful image alternative text, live
links, and print CSS for a single US Letter page. Decorative graphics are
excluded from Prince's PDF tag tree, and descriptive `aria-label` values are
passed to Prince as alternative text.

## 1. Create a watermarked test PDF

No account key is needed for a test build:

```bash
cd work/otc-safety-poster
python3 build_accessible_pdf.py
```

Output:

`output/pdf/otc-campus-safety-awareness-poster-preview.pdf`

DocRaptor test PDFs are watermarked and are for layout and tag inspection only.

## 2. Create the production PDF

Set the key in the shell; do not paste it into the Python file or commit it.

macOS/Linux:

```bash
export DOCRAPTOR_API_KEY="your-real-key"
python3 build_accessible_pdf.py --production
```

PowerShell:

```powershell
$env:DOCRAPTOR_API_KEY = "your-real-key"
python build_accessible_pdf.py --production
```

Output:

`output/pdf/otc-campus-safety-awareness-poster-accessible.pdf`

The script rebuilds the HTML first, submits the complete self-contained file,
selects DocRaptor pipeline 10.1 / Prince 15.1, uses print media, selects the
`PDF/UA-1` profile, disables network fetching, and refuses to save an output if
the converter reports anything other than one page.

To convert a separately supplied self-contained HTML file:

```bash
python3 build_accessible_pdf.py --production \
  --input path/to/poster.html \
  --output path/to/poster.pdf
```

## 3. Validate before publishing

Selecting a PDF/UA profile creates tags, but it does not by itself prove that
the content order and descriptions are correct. Use all of these checks:

1. Open the PDF in Adobe Acrobat Pro and run **Accessibility Check**.
2. In Acrobat's **Tags** panel, confirm the reading order starts with the OTC
   identity and poster title, then moves through the hero, the four actions,
   the six tips, Safety Resources, the Campus Safety Hub, partner logos, and the
   EEO statement.
3. Confirm one `H1`, then logical `H2` and `H3` levels; lists should appear as
   `L` / `LI` structures and the 12 meaningful images as `Figure` tags with
   useful alternative text.
4. Tab through and activate all seven destinations: OTC home, 911, campus
   contacts, FortifyFL, Campus Safety Hub, EEO statement, and the OCPS phone
   number.
5. Inspect at 100% zoom and print one Letter-size proof. Nothing should clip,
   overlap, or spill onto a second page.
6. Run a PDF/UA validator such as PAC or CommonLook PDF Validator. Treat any
   automated result as a starting point and still perform the manual tag-order
   and link checks above.

Recommended release filename:

`otc-campus-safety-awareness-month.pdf`

