#!/usr/bin/env python3
"""Monthly executive summary email for online purchasing flow.

This script reports previous-month outcomes from the monitor SQLite database,
breaking out success and failure counts by LOB, and attaches CSV exports with
summary and detailed account-level rows.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import logging
import os
import smtplib
import sqlite3
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

from purchasing_site_failure_monitor import load_config, normalize_email_recipients


LOGGER = logging.getLogger("monthly_executive_summary")

LOB_DEFAULTS = ["ga_apolar", "ga_reol", "ga_cpaol", "unknown"]
POLICY_PREFIX_TO_LOB = {
    "RAP": "ga_apolar",
    "RAS": "ga_reol",
    "RAB": "ga_reol",
    "ACP": "ga_cpaol",
    "ACS": "ga_cpaol",
}


@dataclass
class AccountRow:  # pylint: disable=too-many-instance-attributes
    """Denormalized account outcome row used for summary and CSV outputs."""

    payment_id: int
    confirmation_number: str
    email: str
    purchase_time: str
    session_id: str
    status: str
    lob: str
    policy_number: str
    risk_number: str
    processing_time: str
    email_time: str
    reason: str


def setup_logging(verbose: bool) -> None:
    """Configure script logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def parse_args() -> argparse.Namespace:
    """Parse CLI options for monthly summary execution."""
    parser = argparse.ArgumentParser(description="Send monthly executive summary email")
    parser.add_argument(
        "--emails",
        nargs="+",
        required=True,
        help="Recipient emails. Supports repeated values and comma-separated values.",
    )
    parser.add_argument(
        "--config", default="config.yaml", help="Path to YAML config file"
    )
    parser.add_argument(
        "--state-db",
        default=None,
        help="Override SQLite DB path (defaults to config monitor.db_path)",
    )
    parser.add_argument(
        "--as-of",
        default=None,
        help="Optional ISO date/datetime override for period calculation",
    )
    parser.add_argument(
        "--output-dir",
        default="monthly-executive-reports",
        help="Directory where generated CSV report files are saved",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build summary without sending email",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args()


def parse_as_of(value: str | None) -> dt.datetime:
    """Parse optional --as-of value, defaulting to current local datetime."""
    if not value:
        return dt.datetime.now()
    try:
        return dt.datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid --as-of value: {value}") from exc


def previous_month_range(as_of: dt.datetime) -> Tuple[dt.datetime, dt.datetime]:
    """Return [start, end) datetime window for the previous month."""
    this_month_start = as_of.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    prev_month_end = this_month_start
    prev_month_start = (this_month_start - dt.timedelta(days=1)).replace(day=1)
    return prev_month_start, prev_month_end


def infer_lob(lob: str, policy_number: str) -> str:
    """Infer LOB from known policy prefixes when explicit processing LOB is missing."""
    if lob:
        return lob
    prefix = (policy_number or "")[:3].upper()
    return POLICY_PREFIX_TO_LOB.get(prefix, "unknown")


def fetch_rows(
    db_path: str, start_at: dt.datetime, end_at: dt.datetime
) -> List[AccountRow]:
    """Fetch account outcomes for the requested monthly period."""
    query = """
        SELECT
            p.id AS payment_id,
            p.confirmation_number,
            p.email,
            p.purchase_time,
            p.session_id,
            c.status,
            c.details_json,
            pe.lob,
            pe.policy_number,
            pe.risk_number,
            pe.processing_time,
            ee.email_time
        FROM payments p
        JOIN correlations c ON c.payment_id = p.id
        LEFT JOIN processing_events pe ON pe.id = c.processing_event_id
        LEFT JOIN email_events ee ON ee.id = c.email_event_id
        WHERE p.purchase_time >= ?
          AND p.purchase_time < ?
        ORDER BY p.purchase_time ASC
    """

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            query,
            (start_at.isoformat(sep=" "), end_at.isoformat(sep=" ")),
        ).fetchall()

    result: List[AccountRow] = []
    for row in rows:
        raw_status = (row["status"] or "").strip().lower()
        status = "success" if raw_status == "success" else "failure"
        reason = ""
        if row["details_json"]:
            try:
                details = json.loads(row["details_json"])
                reason = str(details.get("reason", ""))
            except json.JSONDecodeError:
                reason = ""

        policy_number = row["policy_number"] or ""
        result.append(
            AccountRow(
                payment_id=int(row["payment_id"]),
                confirmation_number=row["confirmation_number"] or "",
                email=row["email"] or "",
                purchase_time=row["purchase_time"] or "",
                session_id=row["session_id"] or "",
                status=status,
                lob=infer_lob(row["lob"] or "", policy_number),
                policy_number=policy_number,
                risk_number=row["risk_number"] or "",
                processing_time=row["processing_time"] or "",
                email_time=row["email_time"] or "",
                reason=reason,
            )
        )
    return result


def build_counts(rows: Iterable[AccountRow]) -> Dict[str, Dict[str, int]]:
    """Build success/failure totals by LOB."""
    counts: Dict[str, Dict[str, int]] = {
        lob: {"success": 0, "failure": 0} for lob in LOB_DEFAULTS
    }
    for row in rows:
        if row.lob not in counts:
            counts[row.lob] = {"success": 0, "failure": 0}
        counts[row.lob][row.status] += 1
    return counts


def ensure_period_output_dir(root: str, start_at: dt.datetime) -> Path:
    """Create period output folder used for report CSVs."""
    month_key = start_at.strftime("%Y-%m")
    out = Path(root) / month_key
    out.mkdir(parents=True, exist_ok=True)
    return out


def write_summary_csv(path: Path, counts: Dict[str, Dict[str, int]]) -> None:
    """Write summary count rows by LOB."""
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["lob", "success_count", "failure_count", "total_count"])
        for lob in sorted(counts.keys()):
            success = counts[lob]["success"]
            failure = counts[lob]["failure"]
            writer.writerow([lob, success, failure, success + failure])


def write_detail_csv(path: Path, rows: Sequence[AccountRow], status: str) -> None:
    """Write detail account rows for the requested status."""
    selected = [row for row in rows if row.status == status]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "payment_id",
                "confirmation_number",
                "email",
                "purchase_time",
                "session_id",
                "lob",
                "policy_number",
                "risk_number",
                "processing_time",
                "email_time",
                "reason",
            ]
        )
        for row in selected:
            writer.writerow(
                [
                    row.payment_id,
                    row.confirmation_number,
                    row.email,
                    row.purchase_time,
                    row.session_id,
                    row.lob,
                    row.policy_number,
                    row.risk_number,
                    row.processing_time,
                    row.email_time,
                    row.reason,
                ]
            )


def build_email_body(
    start_at: dt.datetime,
    end_at: dt.datetime,
    counts: Dict[str, Dict[str, int]],
    output_dir: Path,
) -> str:
    """Build executive summary email body text."""
    lines: List[str] = []
    lines.append("Online Purchasing Executive Summary")
    lines.append("")
    lines.append(
        "Period: "
        f"{start_at.strftime('%Y-%m-%d')} to "
        f"{(end_at - dt.timedelta(days=1)).strftime('%Y-%m-%d')}"
    )
    lines.append("")
    lines.append("Success and Failure Counts by LOB")
    lines.append("")

    grand_success = 0
    grand_failure = 0
    for lob in sorted(counts.keys()):
        success = counts[lob]["success"]
        failure = counts[lob]["failure"]
        grand_success += success
        grand_failure += failure
        lines.append(
            f"- {lob}: success={success}, failure={failure}, total={success + failure}"
        )

    lines.append("")
    lines.append(
        "Overall: "
        f"success={grand_success}, "
        f"failure={grand_failure}, "
        f"total={grand_success + grand_failure}"
    )
    lines.append("")
    lines.append(f"CSV report directory: {output_dir}")
    return "\n".join(lines)


def add_csv_attachments(msg: EmailMessage, paths: Sequence[Path]) -> None:
    """Attach CSV files to the outbound email message."""
    for path in paths:
        msg.add_attachment(
            path.read_bytes(),
            maintype="text",
            subtype="csv",
            filename=path.name,
        )


def send_summary_email(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    smtp_cfg: Dict[str, object],
    recipients: Sequence[str],
    subject: str,
    body: str,
    attachments: Sequence[Path],
    dry_run: bool,
) -> None:
    """Send executive summary email with CSV attachments."""
    msg = EmailMessage()
    msg["From"] = str(smtp_cfg["from_email"])
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content(body)
    add_csv_attachments(msg, attachments)

    if dry_run:
        LOGGER.info("Dry run enabled; summary email not sent")
        LOGGER.info("Would send to: %s", ", ".join(recipients))
        LOGGER.info("Subject: %s", subject)
        return

    host = str(smtp_cfg["host"])
    port = int(smtp_cfg.get("port", 25))
    username = str(smtp_cfg.get("username", ""))
    password_env = str(smtp_cfg.get("password_env", ""))
    password = os.getenv(password_env, "")

    with smtplib.SMTP(host, port, timeout=30) as server:
        if bool(smtp_cfg.get("use_tls", False)):
            server.starttls()
        if username:
            server.login(username, password)
        server.send_message(msg)


def build_subject(start_at: dt.datetime, smtp_cfg: Dict[str, object]) -> str:
    """Build subject line for monthly summary email."""
    prefix = str(smtp_cfg.get("subject_prefix", "[Online Purchasing Monitor]"))
    month_label = start_at.strftime("%B %Y")
    return f"{prefix} Executive Summary - {month_label}"


def run(args: argparse.Namespace) -> int:  # pylint: disable=too-many-locals
    """Execute monthly summary workflow."""
    recipients = normalize_email_recipients(args.emails)
    if not recipients:
        raise ValueError("At least one valid recipient email is required")

    as_of = parse_as_of(args.as_of)
    start_at, end_at = previous_month_range(as_of)

    config = load_config(args.config)
    smtp_cfg = config["smtp"]
    db_path = args.state_db or config["monitor"]["db_path"]

    rows = fetch_rows(db_path, start_at, end_at)
    counts = build_counts(rows)

    output_dir = ensure_period_output_dir(args.output_dir, start_at)
    summary_csv = output_dir / "summary_by_lob.csv"
    success_csv = output_dir / "accounts_success.csv"
    failure_csv = output_dir / "accounts_failure.csv"

    write_summary_csv(summary_csv, counts)
    write_detail_csv(success_csv, rows, "success")
    write_detail_csv(failure_csv, rows, "failure")

    subject = build_subject(start_at, smtp_cfg)
    body = build_email_body(start_at, end_at, counts, output_dir)

    send_summary_email(
        smtp_cfg=smtp_cfg,
        recipients=recipients,
        subject=subject,
        body=body,
        attachments=[summary_csv, success_csv, failure_csv],
        dry_run=args.dry_run,
    )

    LOGGER.info("Monthly summary completed for %s", start_at.strftime("%Y-%m"))
    LOGGER.info("Rows evaluated: %d", len(rows))
    return 0


def main() -> int:
    """CLI wrapper with top-level exception handling."""
    args = parse_args()
    setup_logging(args.verbose)
    try:
        return run(args)
    except Exception as exc:  # pylint: disable=broad-except
        LOGGER.exception("Monthly summary failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
