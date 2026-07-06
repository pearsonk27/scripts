#!/usr/bin/env python3
"""
build_rab_single_decs.py - Build Single-Dec PDFs from RAB policy declarations.

Phase 1: Setup & Data Parsing
  Step 1.1 - Initialize the script structure (imports, constants, CLI)
  Step 1.2 - Parse icustomer.csv (^ delimiter, column mapping, RAB + CA state filter)
  Step 1.3 - Build lookup of RAB policies from CSV rows

Phase 2: Location & Matching
  Step 2.1 - Locate source policy PDFs on disk
  Step 2.2 - Match CSV entries to PDFs (supports test, full production, and bare-code formats)

Phase 3: Page Selection & Output Generation (always page 1)
  Step 3.1 - Extract only page 1 (0-indexed) from each matched PDF
  Step 3.2 - Create single-declaration PDF and write output

Roadmap: build-rab-single-decs/ROADMAP.md
Design:    build-rab-single-decs/DESIGN.md
"""

import argparse
import csv
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import fitz
from pendulum import datetime  # PyMuPDF


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# CSV column indices (0-based)
COL_RISK_NUM = 0
COL_COPRO_CODE = 15
COL_POLICY_NUM = 22
COL_STATE = 47

# RAB policy pattern: RAB followed by any 7 non-dash chars then -YY
RAB_PATTERN_STR = r"^RAB\S{7}-\d{2}$"
RAB_PATTERN = re.compile(RAB_PATTERN_STR)

# Substring pattern to locate RAB policy numbers inside filenames.
# Matches "RAB" + 7 alphanumeric characters + "-YY" anywhere in a string.
RAB_SUBSTR_PATTERN = re.compile(r"RAB[A-Za-z0-9]{7}-\d{2}")

# Test-file filename pattern: {risk_num}-RAB{code}-{year}-DEC_...
# risk_num is the field at column 0 (e.g. "TENC91-1")
TEST_FILE_RAB_PATTERN = re.compile(
    r"^(.+)-"
    r"(RAB[A-Za-z0-9]{7}-\d{2})"
    r"-DEC_.+\.pdf$",
    re.IGNORECASE,
)

# Production filename pattern with embedded full RAB: _DEC_{copro}_RAB{code}-{year}.pdf
# Also handles filenames starting directly with DEC_ (no leading underscore).
PROD_FILE_RAB_PATTERN = re.compile(
    r"(?:_|^)DEC_[^_]+_(RAB[A-Za-z0-9]{7}-\d{2})\.pdf$",
    re.IGNORECASE,
)

# Bare-code production filename pattern.
# Filename contains only the 7-char bare code (no RAB prefix / -YY suffix).
# Also captures the copro segment between DEC_ and the 7-char bare code.
# Handles both "_DEC_xxx_BBB.pdf" and "DEC_CCC_aaaaaaa.pdf" file names.
PATTERN_BARE_RAB = re.compile(r"(?:_|^)DEC_([^_]+?)_(\w{7})\.pdf$")

# Output prefix for single-dec files: replaces _DEC_ with _SINGLEDEC_
SINGLEDEC_PREFIX = "_SINGLEDEC_"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class RabPolicyInfo:
    """Parsed CSV row containing an RAB policy."""

    risk_num: str           # column 0 - firm code prefix (e.g. SCHT91-1)
    copro_code: str         # column 15 - co-producer code (e.g. HHL01-A)
    rab_full: str           # column 22 - full policy number (e.g. RAB3082802-26)
    rab_code_only: str      # digits/chars between RAB and -YY (e.g. 3082802)
    policy_year: str        # last 2 digits of the year (e.g. 26)
    state: str              # column 47 - policy state (must be "CA")
    row_index: int          # original 1-based row number in CSV (header=1)


@dataclass
class PolicyPdfInfo:
    """A RAB policy matched to its declaration PDF on disk."""

    source_pdf_path: Path
    policy_info: RabPolicyInfo
    match_mode: str = ""  # "test" | "production" for logging


@dataclass
class ProcessingResults:
    """Cumulative counts and summaries for the end-of-run report."""

    success_count: int = 0
    not_found_count: int = 0
    error_count: int = 0
    not_found_policies: List[RabPolicyInfo] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    matched_pdfs: List[PolicyPdfInfo] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Step 1.1 - Argument parsing & logging setup
# ---------------------------------------------------------------------------


def parse_arguments() -> argparse.Namespace:
    """Parse and return CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Generate single-declaration PDFs from RAB policy declaration files.",
    )
    parser.add_argument(
        "--csv",
        default=None,
        help="Path to the input CSV datasource (default: <root>/icustomer.csv).",
    )
    parser.add_argument(
        "--root",
        default=None,
        help="Root directory to search for PDFs and locate icustomer.csv.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable detailed logging.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the run without creating any output files.",
    )
    return parser.parse_args()


def setup_logging(verbose: bool) -> None:
    """Configure root logger with INFO (or DEBUG) level."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


# ---------------------------------------------------------------------------
# Step 1.2 - Parse icustomer.csv
# ---------------------------------------------------------------------------


def parse_csv(csv_path: Path) -> List[RabPolicyInfo]:
    """Read CSV, filter rows with RAB policies in column 22 **and** state CA in column 47.

    The CSV uses ``^`` as the field delimiter.  Rows whose column 22 value
    matches the pattern ``^RAB\\S{7}-\\d{2}$`` **and** whose column 47 value
    is ``CA`` are kept; all others are silently skipped.  A *RAB* row starts with
    the literal prefix ``RAB`` - policies with different prefixes (e.g. RAP, RAS)
    are excluded.

    Parameters
    ----------
    csv_path : Path
        Absolute or relative path to the CSV file.

    Returns
    -------
    List[RabPolicyInfo]
        Filtered list of RAB policy rows (state == "CA" only).

    Raises
    ------
    FileNotFoundError
        If *csv_path* does not exist.
    """
    if not csv_path.is_file():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    rab_policies: List[RabPolicyInfo] = []
    skipped_non_ca = 0

    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh, delimiter="^")
        # Skip header row (row index 0)
        next(reader, None)

        for row_idx, row in enumerate(reader, start=1):
            if len(row) <= COL_POLICY_NUM:
                continue  # malformed / short row

            policy_num = row[COL_POLICY_NUM].strip()

            # Must match the RAB pattern
            if not RAB_PATTERN.match(policy_num):
                continue

            # Must really start with "RAB" (not RAP, RAS, etc.)
            if not policy_num.startswith("RAB"):
                continue

            # --- Filter: only California accounts --------------------------
            if len(row) <= COL_STATE:
                continue  # malformed / short row - no state column available
            state = row[COL_STATE].strip()
            if state != "CA":
                skipped_non_ca += 1
                logger.debug(
                    "Row %d: skipping non-CA account (state=%s) for %s",
                    row_idx, state, policy_num,
                )
                continue

            risk_num = row[COL_RISK_NUM].strip()
            copro_code = row[COL_COPRO_CODE].strip()

            # Extract rab_code_only: strip "RAB" prefix and "-YY" suffix
            # e.g. "RAB3082802-26" -> "3082802"
            rab_code_only = policy_num[3:-3]
            policy_year = policy_num[-2:]

            policy_info = RabPolicyInfo(
                risk_num=risk_num,
                copro_code=copro_code,
                rab_full=policy_num,
                rab_code_only=rab_code_only,
                policy_year=policy_year,
                state=state,
                row_index=row_idx,
            )
            rab_policies.append(policy_info)

    logger.info(
        "Parsed CSV: found %d RAB CA policy(s) in %s (skipped %d non-CA)",
        len(rab_policies), csv_path, skipped_non_ca,
    )
    return rab_policies


# ---------------------------------------------------------------------------
# Step 1.3 - Build lookup dictionaries
# ---------------------------------------------------------------------------


def build_lookups(
    policies: List[RabPolicyInfo],
) -> Tuple[Dict[str, RabPolicyInfo], Dict[str, str]]:
    """Build a full-RAB lookup and a bare-code reverse lookup.

    Returns
    -------
    (rab_full_lookup, rab_bare_lookup)
        *rab_full_lookup* maps ``rab_full`` -> ``RabPolicyInfo``
            e.g. ``"RAB3082940-26"`` -> policy info
        *rab_bare_lookup* maps the **bare** 7-char RAB code to
            the full policy number string used as a key in *rab_full_lookup*.
            e.g. ``"3082940"`` -> ``"RAB3082940-26"``
    """
    lookup: Dict[str, RabPolicyInfo] = {}
    bare_lookup: Dict[str, str] = {}  # bare code -> full rab_full (key for lookup)
    for pol in policies:
        lookup[pol.rab_full] = pol
        bare_lookup[pol.rab_code_only] = pol.rab_full
    logger.info("Built RAB CA lookup with %d entry(ies).", len(lookup))
    return lookup, bare_lookup


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    """CLI entry point. Returns exit code (0 = success)."""
    args = parse_arguments()
    setup_logging(args.verbose)

    # Resolve default paths - look for test data directory alongside icustomer.csv
    if args.root:
        root_dir = Path(args.root)
    else:
        # Default: current working directory
        root_dir = Path.cwd()

    if args.csv:
        csv_path = Path(args.csv)
    else:
        default_csv_name = "icustomer.csv"
        csv_path = root_dir / default_csv_name

    # Validate directories/files
    if not csv_path.is_file():
        logger.error("CSV file not found: %s", csv_path)
        return 1

    if not root_dir.is_dir():
        logger.error("Root directory not found: %s", root_dir)
        return 1

    # Phase 1 - Steps 1.2 & 1.3
    policies = parse_csv(csv_path)
    lookup, bare_rab_lookup = build_lookups(policies)

    if not policies:
        logger.warning("No RAB CA policies found in the CSV. Nothing to process.")
        return 0

    # Summary at this stage
    logger.info(
        "Phase 1 complete: %d RAB CA policy(s) parsed and built into lookup.",
        len(policies),
    )

    # Phase 2 - Steps 2.1 & 2.2
    results = phase2_locate_and_match(root_dir, lookup, bare_rab_lookup)

    if not results.matched_pdfs:
        logger.warning("No PDFs found for any RAB CA policy. Nothing to process.")
        return 0

    logger.info(
        "Phase 2 complete: %d/%d RAB CA policy(s) matched to PDF on disk.",
        len(results.matched_pdfs),
        len(lookup),
    )

    if args.verbose and results.not_found_count:
        logger.info(
            "%d RAB CA policy(s) not found on disk: %s",
            results.not_found_count,
            ", ".join(p.rab_full for p in results.not_found_policies),
        )

    # Phase 3 — Extract page 1 (declarations) from each matched PDF
    results = phase3_extract_and_output(results, dry_run=args.dry_run)

    logger.info(
        "Final summary: %d succeeded, %d not found on disk, %d errors",
        results.success_count,
        results.not_found_count,
        results.error_count,
    )

    return 0


# ---------------------------------------------------------------------------
# Phase 2 — Location & Matching
# ---------------------------------------------------------------------------


def _is_pdf(path: Path) -> bool:
    """Return True if *path* has a .pdf extension (case-insensitive)."""
    return path.is_file() and path.suffix.lower() == ".pdf"


def phase2_locate_and_match(
    root_dir: Path,
    lookup: Dict[str, RabPolicyInfo],
    bare_rab_lookup: Dict[str, str],
) -> ProcessingResults:
    """Phase 2 — Walk the filesystem and match CSV RAB CA policies to PDFs.

    Matching strategy (tried in order):

    1. **Test-file format**: ``{risk_num}-RAB{code}-{year}-DEC_...pdf``
       Captures full ``rab_full`` via ``TEST_FILE_RAB_PATTERN`` group 2.

    2. **Full production format**: ``*_DEC_{copro}_RAB{code}-{year}.pdf``
       Captures ``rab_full`` via ``PROD_FILE_RAB_PATTERN`` group 1.

    3. **Bare-code production format** (new): ``*_DEC_{copro_code}_7char.pdf``
       Only the 7-character code is in the filename; we reverse-lookup the full
       RAB number from *bare_rab_lookup* built during Phase&nbsp;1.

    Parameters
    ----------
    root_dir : Path
        Root directory to walk recursively for PDF files.
    lookup : Dict[str, RabPolicyInfo]
        Mapping of ``rab_full -> RabPolicyInfo`` built from the CSV.
    bare_rab_lookup : Dict[str, str]
        Reverse mapping of bare 7-char RAB code (e.g. "3082940") to full
        policy number string (e.g. "RAB3082940-YY").

    Returns
    -------
    ProcessingResults
        Updated counters with matched and unmatched information.
    """
    results = ProcessingResults()
    rab_set: Set[str] = set(lookup.keys())  # RAB numbers we're looking for
    seen_rab: Dict[str, Path] = {}  # rab_full -> first-found PDF path

    logger.info("Walking root directory to locate and match PDFs: %s", root_dir)

    for dirpath, _dirnames, filenames in os.walk(root_dir):
        for fname in filenames:
            if not fname.lower().endswith(".pdf"):
                continue

            # Match order (priority):
            # 1. Test-file format with full RAB embedded
            m = TEST_FILE_RAB_PATTERN.search(fname)
            if m:
                rab_full = m.group(2)
                match_mode = "test"
            else:
                # 2. Full production format (_DEC_{copro}_RAB{code}-{year}.pdf)
                pm = PROD_FILE_RAB_PATTERN.search(fname)
                if pm:
                    rab_full = pm.group(1)
                    match_mode = "production"
                else:
                    # 3. Bare-code production format (no RAB prefix / -YY suffix)
                    #    e.g. "something_DEC_xxx_3082940.pdf"
                    bm = PATTERN_BARE_RAB.search(fname)
                    if bm:
                        copro_segment = bm.group(1)  # e.g. 'CALI001'
                        bare_code = bm.group(2)     # e.g. '3082940'
                        rab_full = bare_rab_lookup.get(bare_code)
                        if rab_full is not None:
                            policy = lookup[rab_full]
                            if hasattr(policy, 'copro_code') and copro_segment == policy.copro_code:
                                match_mode = "production"
                        else:
                            logger.debug("Bare code '%s' in '%s' not found", bare_code, fname)
                            continue
                    else:
                        # 4. Last resort — substring search for full RAB anywhere
                        sb = RAB_SUBSTR_PATTERN.search(fname)
                        if sb:
                            rab_full = sb.group(0)
                            match_mode = "substring"
                        else:
                            logger.debug("No pattern matched '%s'", fname)
                            continue

            if rab_full in seen_rab:
                # Already found a PDF for this RAB number; keep the first one.
                continue

            if rab_full not in rab_set:
                continue  # Not one of our CSV policies

            pdf_path = Path(dirpath) / fname
            seen_rab[rab_full] = pdf_path
            logger.info(
                "Found PDF for %s : \x1b[4m%s\x1b[0m (mode=%s)",
                rab_full,
                pdf_path,
                match_mode,
            )

    # Build matched list and not-found list
    for rab_full, pdf_path in seen_rab.items():
        policy_info = lookup[rab_full]
        results.matched_pdfs.append(
            PolicyPdfInfo(
                source_pdf_path=pdf_path,
                policy_info=policy_info,
                match_mode="test" if TEST_FILE_RAB_PATTERN.search(pdf_path.name) else "production",
            )
        )

    for rab_full in rab_set:
        if rab_full not in seen_rab:
            results.not_found_count += 1
            results.not_found_policies.append(lookup[rab_full])
            logger.debug("Policy %s not found on disk", rab_full)

    return results


# ---------------------------------------------------------------------------
# Phase 3 — Declarations Page Extraction (always page 1)
# ---------------------------------------------------------------------------


def build_output_path(source_path: Path) -> Path:
    """Build the output path by replacing ``_DEC_`` with ``_SINGLEDEC_``.

    Handles both test-file style names (``TENC91-...-DEC_b.email.pdf``) and
    bare-code production names (``ABC_DEC_xxx_3082940.pdf``).

    Examples
    --------
    >>> build_output_path(Path("foo/TENC91-RAB3082802-DEC_b.email.pdf"))
    Path('foo/TENC91-RAB3082802-SINGLEDEC_b.email.pdf')
    >>> build_output_path(Path("foo/ABC_DEC_xxx_3082940.pdf"))
    Path('foo/ABC_SINGLEDEC_xxx_3082940.pdf')
    """
    new_name = source_path.name.replace("DEC_", "SINGLEDEC_", 1)
    return source_path.with_name(new_name)


def phase3_extract_and_output(
    results: ProcessingResults,
    dry_run: bool = False,
) -> ProcessingResults:
    """Phase 3 — Extract only the declarations page (page 1, index 0) from each PDF.

    For every ``PolicyPdfInfo`` in *results.matched_pdfs*:

    #. Open the source PDF with PyMuPDF (``fitz``).
    #. Insert only page 0 (declarations page) into a new document.
    #. Write the output file by replacing ``_DEC_`` with ``_SINGLEDEC_`` in the filename.
    #. Track and report results.

    Parameters
    ----------
    results : ProcessingResults
        Result object from Phase 2 with matched PDFs.
    dry_run : bool
        If True, log what *would* be done without creating or modifying any files.

    Returns
    -------
    ProcessingResults
        Updated results with output written and counters incremented.
    """
    mode_label = "[DRY RUN]" if dry_run else ""
    logger.info("Phase 3 — Declarations Page Extraction (always page 1) %s", mode_label)
    total = len(results.matched_pdfs)

    if total == 0:
        return results

    pages_to_extract = [0]  # always just the first page (0-indexed)

    for i, pdf_info in enumerate(results.matched_pdfs, start=1):
        source_path = pdf_info.source_pdf_path

        logger.info(
            "[%d/%d] Processing %s  [extracting page 1]",
            i, total, source_path.name,
        )

        out_path = build_output_path(source_path)

        # --- Skip if output exists and is newer than source ------------------
        try:
            if out_path.is_file():
                src_mtime = source_path.stat().st_mtime
                dst_mtime = out_path.stat().st_mtime
                if dst_mtime >= src_mtime:
                    logger.info(
                        "[%d/%d] Skipping %s (output is up-to-date), source: %s (%.1fs) -> dest: %s (%.1fs)",
                        i, total, out_path.name,
                        source_path.resolve(), src_mtime, out_path.resolve(), dst_mtime,
                    )
                    results.success_count += 1
                    continue
        except OSError as exc:
            logger.warning(
                "[%d/%d] Could not stat output file %s: %s",
                (i, total, out_path.name, exc),
            )
            src_doc.close()
            results.error_count += 1
            results.errors.append(f"Could not stat {out_path.name}: {exc}")
            continue

        # --- Open source and collect selected pages -------------------------
        try:
            src_doc = fitz.open(source_path)
        except Exception as exc:
            results.error_count += 1
            results.errors.append(f"Error opening {source_path.name}: {exc}")
            logger.error("Could not open PDF %s: %s", source_path, exc)
            continue

        # Validate that page 0 exists
        if len(src_doc) < 1:
            results.error_count += 1
            results.errors.append(
                f"{source_path.name} — document has no pages"
            )
            logger.error("PDF %s is empty", source_path)
            src_doc.close()
            continue

        selected_pages = [src_doc[0]]  # declarations page (1st page)

        # --- Create new single-declaration PDF ------------------------------
        try:
            if dry_run:
                logger.info(
                    "[%d/%d] Would write output -> %s (1 page)",
                    i, total, out_path.name,
                )
                results.success_count += 1
                continue

            out_doc = fitz.open()  # blank document

            # Insert the first page into the new document
            for page in selected_pages:
                out_doc.insert_pdf(src_doc, from_page=page.number, to_page=page.number)

            out_doc.save(str(out_path), garbage=4, deflate=True)
            out_doc.close()
        except Exception as exc:
            results.error_count += 1
            results.errors.append(f"Error writing {out_path.name}: {exc}")
            logger.error("Could not write single-dec PDF %s: %s", out_path, exc)
            src_doc.close()
            continue

        src_doc.close()

        # --- Track success --------------------------------------------------
        results.success_count += 1
        logger.info(
            "  Wrote output -> %s (1 page)", out_path.name
        )

    # Summary for Phase 3
    logger.info(
        "Phase 3 complete: %d single-dec PDF(s) created.", results.success_count,
    )
    return results


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    raise SystemExit(main())
