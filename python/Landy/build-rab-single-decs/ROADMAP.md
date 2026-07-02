# Roadmap: Build RAB Single Dec File Generator

## Phase 1 — Setup & Data Parsing ( ✅ DONE )

### Step 1.1: Initialize the script structure ( ✅ DONE )

- Create `build_rab_single_decs.py` with imports, constants, and argument parsing
- Accept command-line arguments for CSV path (with default to local test data) and output root directory
- Validate that required directories exist

### Step 1.2: Parse `icustomer.csv` ( ✅ DONE )

- Open the CSV file (delimiter is `^`, not standard comma)
- Skip any header rows; data rows start with a prefix code followed by `|`, but column indices are fixed (0-indexed):
  - **Column 0 (`risk_num`)** → firm code prefix (matches PDF filename prefix like `TENC91-1`)
  - **Column 15 (`copro_code`)** → co-producer code  
  - **Column 22 (`policy_num`)** → full RAB policy number like `RAB3082802-26`
- Filter rows where column 22 matches the pattern `^RAB\S{7}-\d{2}$` (exactly 7 characters, alphanumerical because these codes can start with 'E')

### Step 1.3: Build lookup of RAB policies ( ✅ DONE )

- For each qualifying row, extract:
  - `rab_full`: the full policy number from col[22] (e.g., `RAB3082802-26`)
  - `rab_code_only`: strip the prefix and suffix (e.g., `3082802` or `E082802`)
  - `policy_year`: the last 2 digits (e.g., `26`)
  - `firm_prefix`: field[0] value used for PDF naming prefix
- Store mappings in dictionaries/lists for easy lookup

---

## Phase 2 — Location & Matching ( ✅ DONE )

### Step 2.1: Locate source policy PDFs on disk ( ✅ DONE )

- Walk the file system from a base root directory (passed as argument) into all subdirectories
- For each `.pdf` file found, check if it contains an RAB policy number via substring matching on filename
- Use pattern: `^.{7}-RAB\d{7}-\d{2}-DEC_.+\.pdf$` to match production filenames
- Also handle test files which follow a slightly different naming (`TENC91-1-RAB3082802-26-DEC_b.tenzercommercial@gmail.com.pdf`)

### Step 2.2: Match CSV entries to PDFs ( ✅ DONE )

- For each RAB policy in the CSV, search for its corresponding `.pdf` on disk  
- On match: record `(source_pdf_path, row_data)` tuple
- On no match: count and log a warning ("Policy {rab_full} not found on disk")

---

## Phase 3 — FormType Detection & PDF Processing ( ✅ DONE )

### Step 3.1: Open each PDF and extract text from its first page ( ✅ DONE )

- Use PyMuPDF (`fitz.open()`) to load the full policy PDF
- Extract all text from page 0 (first page = declarations page)

### Step 3.2: Detect FormType from extracted text ( ✅ DONE )

Search for these exact strings in the declarations page:

1. `"CYL 6000 (07 22)"` → pages 1‒3
2. `"D43101 (03/15)"` → page 1
3. `"D43181 (03/15)"` → page 1  
4. `"D43101 NY (04/21)"` → pages 1‒2

### Step 3.3: If no form type found — stop processing that file ( ✅ DONE )

- Log the filename that could not be processed with a clear warning message
- Continue with the next file in the list (do not abort the entire run)

---

## Phase 4 — Page Selection & Output Generation ( ✅ DONE )

### Step 4.1: Extract the appropriate pages based on FormType detected ( ✅ DONE )

```python
if formtype == "CYL 6000 (07 22)":
    pages_to_extract = [0, 1, 2]   # 0-indexed → pages 1, 2, 3
elif formtype in ("D43101 (03/15)", "D43181 (03/15)"):
    pages_to_extract = [0]           # page 1 only
elif formtype == "D43101 NY (04/21)":
    pages_to_extract = [0, 1]        # pages 1‒2
```

### Step 4.2: Create single-declare PDF ( ✅ DONE )

- Instantiate a new `fitz.Document()` (blank)
- Insert selected pages from the source document into the new document
- Write output to same directory as source with `_SINGLEDEC_` replacing `_DEC_` in the filename
- Example: `TENC91-1-RAB3082802-26-DEC_b.tenzercommercial@gmail.com.pdf` →  
  `TENC91-1-RAB3082802-26-SINGLEDEC_b.tenzercommercial@gmail.com.pdf`

### Step 4.3: Track and report results ( ✅ DONE )

Maintain counters and logs for:

- Policies processed successfully
- Policies where PDF was not found on disk
- Policies where form type could not be detected  
- Any errors encountered during PDF processing

---

## Phase 5 — Testing & Validation ( ⬜ TODO )

### Test Strategy (uses local test data) ( ⬜ TODO )

1. **Test file matching**: Confirm all 3 test files are located and mapped correctly from CSV → disk paths
2. **FormType detection**: Verify that the script can identify which pages to extract for each test PDF
3. **Single-dec generation**: Verify the output files have correct content (correct number of pages) and naming
4. **Error scenarios**: Test with intentionally misnamed or malformed files to confirm graceful handling

---

## Phase 6 — Production Readiness ( ⬜ TODO )

### Step 6.1: Command-line arguments ( ⬜ TODO )

- `--csv PATH` → path to the CSV datasource (default: local test file)
- `--root PATH` → root directory to search for PDFs (default: project test path)
- `--verbose / -v` → enable detailed logging

### Step 6.2: Error resilience ( ⬜ TODO )

- Wrap each PDF in try/except so one failure doesn't halt the run
- Track and report all failures at script termination

### Step 6.3: Logging ( ⬜ TODO )

- Progress logging (e.g., `Processing {n}/total...`)
- Summary at end: `{success} succeeded, {failed_no_pdf} not found, {failed_formtype} no form type detected`

---
