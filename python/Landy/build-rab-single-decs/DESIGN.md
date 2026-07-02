# Design: Build RAB Single Dec File Generator (CA Only)

## Goal

Given a CSV datasource (`icustomer.csv`) containing insurance accounts, identify all policies with **RAB** full account numbers in column 22 (`policy_num`) where the state is **"CA"**, locate the corresponding declaration PDF files on disk, extract **only page 1** (declarations) from each, and produce single-declaration PDFs for each.

## Input: CSV Format (`icustomer.csv`)

### Delimiter

The `CSV` is **pipe-and-caret delimited**: fields are separated by `^`. The first line (header) does NOT have a row-prefix, all data lines start with a company prefix and pipe, e.g.:

```
Header: risk_num^firm_name[1]^firm_name[2]...  
Data rows start with something like `SCH` etc
```

### Key Columns (0-indexed)

| Index | Header | Description |
|-------|--------|-------------|
| 0 | risk_num | Row identifier and firm code prefix, e.g. `WN$SCHT91-1...` where the value in this field maps to the beginning of PDF filenames |
| 15 | copro_code | Co-producer code used in PDF filename construction (e.g., PHL01-A, PINI001) |
| 22 | policy_num | Full policy number, format: `RAB{digits}-{yy}`, e.g. `RAB3082802-26` |
| 25 | state     | State code - **only "CA" accounts are processed** |

### Identifying RAB Policies

A row represents a relevant policy if:
1. Column 22 contains a valid RAB format (`RAB{7chars}-{yy}`) starting with `RAB` followed by exactly 7 non-dash characters, then `-` then 2-digit year: `^RAB\S{7}-\d{2}$` (e.g. RAB3082802-26)
2. Column 25 contains **"CA"** (California only)

## Output Naming Convention

For each source policy PDF, the output file is placed in the **same directory** with a similar name except instead of `DEC_` it will have `SINGLEDEC`:

```text
{source_pdf_filename} → {new_filename.pdf}
```

### Examples
- Source: `TENC91-1-RAB3082802-26_DEC_b.tenzercommercial@gmail.com.pdf`
  - Output: `TENC91-1-RAB3082802-26_SINGLEDEC_b.tanzercommercial@gmail.com.pdf`

## Source PDF Location & Naming Pattern (Production)

The full declaration PDFs live in subdirectories following one of these patterns:

| Format | Pattern |
|--------|---------|
| Full RAB | `*/webdocs/{directs\|agents}/{mm}/_DEC_{co-producer_code}_RAB{code}-{yy}.pdf` |
| Bare-code (no RAB prefix) | `*/webdocs/.../_DEC_{copro_code}_{7-char-code}.pdf` |

Both formats are supported — files may use `_DEC_` or start directly with `DEC_`:
- `DEC_CALI001_3082940.pdf`
- `someprefix_DEC_xxx_RAB3082802-26.pdf`

e.g., the test files sit directly in the project root as `TENC91-1-RAB3082802-26-DEC_b.tenzercommercial@gmail.com.pdf`.

### Searching Strategy (Production)

Multi-step approach:
1. **Build a reverse lookup** from CSV: map each bare 7-char RAB code → full policy number.
2. **Walk all subdirectories** to find PDF files matching each RAB CA policy number.
3. Matching is tried in this order per filename:
   - **Test format**: `{risk_num}-RAB{code}-{year}-DEC_...pdf` — captures full RAB directly.
   - **Full production** (`_DEC_...RAB{code}-{year}.pdf`) — captures full RAB from regex group.
   - **Bare-code production** (`_DEC_{copro}_7char.pdf`) — reverse-lookup the bare code.
   - **Substring search**: last resort, any occurrence of `RAB…-YY` anywhere in the name.
4. Once found, produce single dec in same directory.

## Declarations Page Selection - Always Page 1

Since the form type will always be known/predefined as FormType 1, **only page 1 (0-indexed: page 0)** is extracted from each matched PDF. No form type detection is required.

No pages to extract (missing FormType) error handling is not needed for this use case since extraction is deterministic.

## Error Handling & Unprocessable Files

- If a policy number from the CSV cannot be found in any file on disk → log/warning with that account's details
- Process continues for all other files after reporting

## Dependencies

- `pymupdf` (PyMuPDF) — PDF page extraction
- Standard library: `csv`, `re`, `os`, `pathlib`, etc.

## Test Data

Three test files are provided in:

```
/Users/kristoferpearson/Dev/Landy/Projects/SingleDecsForRab_20260618/
├── <TENC91-1-RAB3082802-26-DEC_b.tenzercommercial@gmail.com.pdf>
├── <KELR91-1-RAB3083328-26-DEC_ncreokelley@bellsouth.net.pdf>
└── <DESW91-1-RAB4449642-26-DEC_michelle@desertwavepm.com.pdf>
```

These three files and the CSV `icustomer.csv` are used for local testing. **Note:** Only CA accounts from the CSV will be processed.

## File Structure

```text
build-rab-single-decs/
├── DESIGN.md               # Design document — goals, inputs/outputs, rules
├── ROADMAP.md              # This document — phased step-by-step plan
└── build_rab_single_decs.py  # The implementation script