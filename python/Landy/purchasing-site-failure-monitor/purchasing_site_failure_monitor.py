#!/usr/bin/env python3
"""Online purchasing flow monitor.

This script is designed for scheduled execution (for example, hourly). It ingests
three log sources, correlates flow completion, stores outcomes in SQLite, and
sends alert emails only when actionable failures are found.
"""

# pylint: disable=line-too-long,too-many-lines

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import logging
import os
import re
import smtplib
import sqlite3
import tempfile
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import paramiko
import yaml


LOGGER = logging.getLogger("purchasing_flow_monitor")

CONFIRMATION_RE = re.compile(r"^[A-Za-z0-9]{8}$")
LARAVEL_LINE_RE = re.compile(r"^\[(?P<ts>[^\]]+)\]\s+\S+:\s+(?P<msg>.*)$")
SESSION_TRAILER_RE = re.compile(r"\s+(\{\"SessionID\":\"(?P<session>[^\"]+)\"\})\s*$")

PROCESSING_RE = re.compile(
    r"^(?P<ts>\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2})\s+\w+\s+(?P<lob>\S+)\s+\[[^\]]*\]\s+"
    r"Processing Confirmation Number:\s*(?P<conf>[A-Za-z0-9]{8}),\s*Policy Number\s*(?P<policy>\S+)"
)
RISK_RE = re.compile(
    r"^(?P<ts>\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2})\s+\w+\s+(?P<lob>\S+)\s+\[[^\]]*\]\s+"
    r"Risk Number\s+(?P<risk>\S+)\s+assigned/found for Confirmation Number:\s*(?P<conf>[A-Za-z0-9]{8}),\s*"
    r"Policy Number\s*(?P<policy>\S+)"
)
RUNNING_RE = re.compile(r"^Running:\s+(?P<ts>.+)$")
EMAIL_LINE_RE = re.compile(r"^Sending out Policy for:\s+(?P<risk>\S+)\s+-\s+(?P<kind>.+)$")


@dataclass
class PaymentRecord:
    """Normalized payment success event extracted from purchasing logs."""

    confirmation_number: str
    email: str
    purchase_time: dt.datetime
    session_id: str
    source_file: str
    source_excerpt: str


@dataclass
class ProcessingRecord:
    """Normalized processing-server event keyed by confirmation number."""

    confirmation_number: str
    policy_number: Optional[str]
    risk_number: Optional[str]
    processing_time: dt.datetime
    lob: Optional[str]
    source_file: str
    source_excerpt: str


@dataclass
class EmailRecord:
    """Normalized emailing-server event keyed by risk number."""

    risk_number: str
    email_time: dt.datetime
    kind: str
    source_file: str
    source_excerpt: str


@dataclass
class CorrelationOutcome:
    """Correlation result for a single payment across all flow stages."""

    payment_id: int
    status: str
    processing_event_id: Optional[int]
    email_event_id: Optional[int]
    details: Dict[str, Any]


def setup_logging(verbose: bool) -> None:
    """Configure standard console logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Online policy purchasing flow monitor")
    parser.add_argument(
        "--emails",
        nargs="+",
        required=True,
        help="Recipient emails. Supports repeated values and comma-separated values.",
    )
    parser.add_argument("--config", default="config.yaml", help="Path to YAML config file")
    parser.add_argument(
        "--state-db",
        default=None,
        help="Override SQLite DB path (defaults to config monitor.db_path)",
    )
    parser.add_argument(
        "--output-root",
        default=None,
        help="Override evidence output root path (defaults to config monitor.output_root)",
    )
    parser.add_argument(
        "--lookback-hours",
        type=int,
        default=None,
        help="Override source lookback window for this run",
    )
    parser.add_argument(
        "--now",
        default=None,
        help="Optional ISO datetime override for deterministic testing",
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not send outbound alert email")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args()


def normalize_email_recipients(raw_values: Sequence[str]) -> List[str]:
    """Normalize mixed space/comma recipient input into a unique ordered list."""
    result: List[str] = []
    seen = set()
    for chunk in raw_values:
        for part in chunk.split(","):
            email = part.strip()
            if not email:
                continue
            if email not in seen:
                seen.add(email)
                result.append(email)
    return result


def parse_now(override: Optional[str]) -> dt.datetime:
    """Return current time, optionally from ISO override string."""
    if not override:
        return dt.datetime.now()
    try:
        return dt.datetime.fromisoformat(override)
    except ValueError as exc:
        raise ValueError(f"Invalid --now value: {override}") from exc


def deep_merge(base: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge dict values."""
    merged = dict(base)
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def default_config() -> Dict[str, Any]:
    """Default monitor configuration."""
    return {
        "monitor": {
            "db_path": "monitor_state.sqlite3",
            "output_root": r"\\ix200\pdf_files\ONLINE_PURCHASING_FAILURES",
            "grace_hours": 2,
            "first_run_lookback_hours": 24,
        },
        "purchasing": {
            "host": "",
            "port": 22,
            "username": "",
            "key_path": "",
            "password_env": "PURCHASING_SFTP_PASSWORD",
            "log_dir": "/var/www/html/storage/logs",
            "current_log_prefix": "laravel.log",
        },
        "processing": {
            "base_path": r"\\ix200\pdf_files\garf\Scheduled-Jobs-Logs",
            "lobs": ["ga_apolar", "ga_reol", "ga_cpaol"],
        },
        "emailing": {
            "host": "",
            "port": 22,
            "username": "",
            "key_path": "",
            "password_env": "EMAIL_SFTP_PASSWORD",
            "log_dir": "/home/sendmail/logs",
            "file_prefix": "send_policies_",
        },
        "smtp": {
            "host": "",
            "port": 25,
            "username": "",
            "password_env": "SMTP_PASSWORD",
            "use_tls": False,
            "from_email": "purchasing-monitor@local",
            "subject_prefix": "[Online Purchasing Monitor]",
        },
    }


def load_config(path: str) -> Dict[str, Any]:
    """Load configuration from YAML and merge with defaults."""
    config = default_config()
    cfg_path = Path(path)
    if cfg_path.exists():
        with cfg_path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}
            if not isinstance(loaded, dict):
                raise ValueError("Config file must contain a YAML object at root")
            config = deep_merge(config, loaded)
    return config


def require_config_fields(config: Dict[str, Any], keys: Iterable[Tuple[str, str]]) -> None:
    """Validate required config values for non-empty strings."""
    missing: List[str] = []
    for section, key in keys:
        value = config.get(section, {}).get(key)
        if not value:
            missing.append(f"{section}.{key}")
    if missing:
        raise ValueError("Missing required config values: " + ", ".join(missing))


class SQLiteStore:
    """SQLite persistence layer for run state, source events, and outcomes."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def close(self) -> None:
        """Close the underlying SQLite connection."""

        self.conn.close()

    def _init_schema(self) -> None:
        """Create or update the SQLite schema used by the monitor."""

        cur = self.conn.cursor()
        cur.executescript(
            """
            PRAGMA journal_mode=WAL;

            CREATE TABLE IF NOT EXISTS run_state (
                state_key TEXT PRIMARY KEY,
                state_value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                confirmation_number TEXT NOT NULL,
                email TEXT NOT NULL,
                purchase_time TEXT NOT NULL,
                session_id TEXT,
                source_file TEXT,
                source_excerpt TEXT,
                created_at TEXT NOT NULL,
                UNIQUE (confirmation_number, purchase_time, session_id)
            );

            CREATE TABLE IF NOT EXISTS processing_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                confirmation_number TEXT NOT NULL,
                policy_number TEXT,
                risk_number TEXT,
                processing_time TEXT NOT NULL,
                lob TEXT,
                source_file TEXT,
                source_excerpt TEXT,
                created_at TEXT NOT NULL,
                UNIQUE (confirmation_number, processing_time, policy_number, risk_number)
            );

            CREATE TABLE IF NOT EXISTS email_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                risk_number TEXT NOT NULL,
                email_time TEXT NOT NULL,
                kind TEXT NOT NULL,
                source_file TEXT,
                source_excerpt TEXT,
                created_at TEXT NOT NULL,
                UNIQUE (risk_number, email_time, kind)
            );

            CREATE TABLE IF NOT EXISTS correlations (
                payment_id INTEGER PRIMARY KEY,
                status TEXT NOT NULL,
                processing_event_id INTEGER,
                email_event_id INTEGER,
                details_json TEXT NOT NULL,
                last_evaluated_at TEXT NOT NULL,
                alert_sent_at TEXT,
                alert_fingerprint TEXT,
                FOREIGN KEY(payment_id) REFERENCES payments(id)
            );

            CREATE INDEX IF NOT EXISTS idx_payments_purchase_time ON payments(purchase_time);
            CREATE INDEX IF NOT EXISTS idx_payments_confirmation ON payments(confirmation_number);
            CREATE INDEX IF NOT EXISTS idx_processing_confirmation ON processing_events(confirmation_number);
            CREATE INDEX IF NOT EXISTS idx_processing_risk ON processing_events(risk_number);
            CREATE INDEX IF NOT EXISTS idx_email_risk ON email_events(risk_number);
            """
        )
        self.conn.commit()

    def get_state(self, key: str) -> Optional[str]:
        """Return a saved run-state value by key, if present."""

        row = self.conn.execute(
            "SELECT state_value FROM run_state WHERE state_key = ?",
            (key,),
        ).fetchone()
        return row[0] if row else None

    def set_state(self, key: str, value: str) -> None:
        """Persist a run-state key/value pair."""

        self.conn.execute(
            "INSERT INTO run_state(state_key, state_value) VALUES(?, ?) "
            "ON CONFLICT(state_key) DO UPDATE SET state_value = excluded.state_value",
            (key, value),
        )
        self.conn.commit()

    def upsert_payment(self, item: PaymentRecord, created_at: dt.datetime) -> int:
        """Insert a payment record if new and return its stable row id."""

        self.conn.execute(
            """
            INSERT OR IGNORE INTO payments(
                confirmation_number, email, purchase_time, session_id,
                source_file, source_excerpt, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.confirmation_number,
                item.email,
                item.purchase_time.isoformat(sep=" "),
                item.session_id,
                item.source_file,
                item.source_excerpt,
                created_at.isoformat(sep=" "),
            ),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT id FROM payments WHERE confirmation_number = ? AND purchase_time = ? AND session_id = ?",
            (
                item.confirmation_number,
                item.purchase_time.isoformat(sep=" "),
                item.session_id,
            ),
        ).fetchone()
        assert row is not None
        return int(row["id"])

    def upsert_processing(self, item: ProcessingRecord, created_at: dt.datetime) -> int:
        """Insert a processing event if new and return its stable row id."""

        self.conn.execute(
            """
            INSERT OR IGNORE INTO processing_events(
                confirmation_number, policy_number, risk_number, processing_time,
                lob, source_file, source_excerpt, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.confirmation_number,
                item.policy_number,
                item.risk_number,
                item.processing_time.isoformat(sep=" "),
                item.lob,
                item.source_file,
                item.source_excerpt,
                created_at.isoformat(sep=" "),
            ),
        )
        self.conn.commit()
        row = self.conn.execute(
            """
            SELECT id FROM processing_events
            WHERE confirmation_number = ? AND processing_time = ?
              AND IFNULL(policy_number, '') = IFNULL(?, '')
              AND IFNULL(risk_number, '') = IFNULL(?, '')
            """,
            (
                item.confirmation_number,
                item.processing_time.isoformat(sep=" "),
                item.policy_number,
                item.risk_number,
            ),
        ).fetchone()
        assert row is not None
        return int(row["id"])

    def upsert_email(self, item: EmailRecord, created_at: dt.datetime) -> int:
        """Insert an email event if new and return its stable row id."""

        self.conn.execute(
            """
            INSERT OR IGNORE INTO email_events(
                risk_number, email_time, kind, source_file, source_excerpt, created_at
            ) VALUES(?, ?, ?, ?, ?, ?)
            """,
            (
                item.risk_number,
                item.email_time.isoformat(sep=" "),
                item.kind,
                item.source_file,
                item.source_excerpt,
                created_at.isoformat(sep=" "),
            ),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT id FROM email_events WHERE risk_number = ? AND email_time = ? AND kind = ?",
            (item.risk_number, item.email_time.isoformat(sep=" "), item.kind),
        ).fetchone()
        assert row is not None
        return int(row["id"])

    def load_payments_for_evaluation(self, now: dt.datetime, grace_hours: int) -> List[sqlite3.Row]:
        """Load payments old enough to evaluate against failure criteria."""

        cutoff = now - dt.timedelta(hours=grace_hours)
        return list(
            self.conn.execute(
                "SELECT * FROM payments WHERE purchase_time <= ? ORDER BY purchase_time ASC",
                (cutoff.isoformat(sep=" "),),
            ).fetchall()
        )

    def find_processing_for_payment(self, confirmation_number: str, purchase_time: dt.datetime) -> Optional[sqlite3.Row]:
        """Find the best matching processing event for a payment confirmation."""

        rows = self.conn.execute(
            """
            SELECT * FROM processing_events
            WHERE confirmation_number = ?
              AND processing_time >= ?
            ORDER BY processing_time ASC
            LIMIT 1
            """,
            (
                confirmation_number,
                (purchase_time - dt.timedelta(hours=1)).isoformat(sep=" "),
            ),
        ).fetchall()
        if rows:
            return rows[0]
        return self.conn.execute(
            "SELECT * FROM processing_events WHERE confirmation_number = ? ORDER BY processing_time DESC LIMIT 1",
            (confirmation_number,),
        ).fetchone()

    def find_email_for_risk(self, risk_number: str, processing_time: dt.datetime) -> Optional[sqlite3.Row]:
        """Find a matching Full Policy email event for a risk number."""

        rows = self.conn.execute(
            """
            SELECT * FROM email_events
            WHERE risk_number = ?
              AND kind LIKE '%Full Policy%'
              AND email_time >= ?
            ORDER BY email_time ASC
            LIMIT 1
            """,
            (
                risk_number,
                (processing_time - dt.timedelta(hours=1)).isoformat(sep=" "),
            ),
        ).fetchall()
        if rows:
            return rows[0]
        return None

    def upsert_correlation(self, outcome: CorrelationOutcome, now: dt.datetime) -> None:
        """Create or update correlation status for a payment."""

        self.conn.execute(
            """
            INSERT INTO correlations(
                payment_id, status, processing_event_id, email_event_id,
                details_json, last_evaluated_at
            ) VALUES(?, ?, ?, ?, ?, ?)
            ON CONFLICT(payment_id) DO UPDATE SET
                status = excluded.status,
                processing_event_id = excluded.processing_event_id,
                email_event_id = excluded.email_event_id,
                details_json = excluded.details_json,
                last_evaluated_at = excluded.last_evaluated_at
            """,
            (
                outcome.payment_id,
                outcome.status,
                outcome.processing_event_id,
                outcome.email_event_id,
                json.dumps(outcome.details, ensure_ascii=True),
                now.isoformat(sep=" "),
            ),
        )
        self.conn.commit()

    def get_unalerted_failures(self) -> List[sqlite3.Row]:
        """Return failures that have not yet triggered an alert."""

        return list(
            self.conn.execute(
                """
                SELECT c.*, p.confirmation_number, p.email, p.purchase_time, p.session_id,
                       pe.policy_number, pe.risk_number, pe.processing_time
                FROM correlations c
                JOIN payments p ON p.id = c.payment_id
                LEFT JOIN processing_events pe ON pe.id = c.processing_event_id
                WHERE c.status IN ('missing_processing', 'missing_email')
                  AND c.alert_sent_at IS NULL
                ORDER BY p.purchase_time ASC
                """
            ).fetchall()
        )

    def mark_alert_sent(self, payment_id: int, sent_at: dt.datetime, fingerprint: str) -> None:
        """Mark a correlation row as alerted so future runs do not duplicate alerts."""

        self.conn.execute(
            "UPDATE correlations SET alert_sent_at = ?, alert_fingerprint = ? WHERE payment_id = ?",
            (sent_at.isoformat(sep=" "), fingerprint, payment_id),
        )
        self.conn.commit()


def open_sftp_client(cfg: Dict[str, Any]) -> Tuple[paramiko.SSHClient, paramiko.SFTPClient]:
    """Open SSH/SFTP with key auth and password fallback."""
    host = cfg["host"]
    port = int(cfg.get("port", 22))
    username = cfg["username"]
    key_path = cfg.get("key_path")
    password = os.getenv(cfg.get("password_env", ""), "")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    errors: List[str] = []
    if key_path:
        try:
            client.connect(hostname=host, port=port, username=username, key_filename=key_path, timeout=20)
            return client, client.open_sftp()
        except Exception as exc:  # pylint: disable=broad-except
            errors.append(f"key auth failed: {exc}")

    try:
        client.connect(hostname=host, port=port, username=username, password=password, timeout=20)
        return client, client.open_sftp()
    except Exception as exc:  # pylint: disable=broad-except
        errors.append(f"password auth failed: {exc}")
        client.close()
        raise RuntimeError(f"Unable to connect to {host}. Details: {'; '.join(errors)}") from exc


def list_remote_files(sftp: paramiko.SFTPClient, directory: str) -> List[Tuple[str, int]]:
    """List remote files with mtime."""
    LOGGER.debug("Listing remote directory: %s", directory)
    entries: List[Tuple[str, int]] = []
    try:
        for attr in sftp.listdir_attr(directory):
            LOGGER.debug("  Found: %s (mtime=%s)", attr.filename, attr.st_mtime)
            entries.append((attr.filename, int(attr.st_mtime)))
    except IOError as e:
        LOGGER.error("Failed to list directory %s: %s", directory, e)
        raise
    return entries


def download_remote_file(sftp: paramiko.SFTPClient, remote_path: str, local_path: Path) -> None:
    """Download a remote file to local path."""
    local_path.parent.mkdir(parents=True, exist_ok=True)
    LOGGER.debug("Downloading remote file: %s -> %s", remote_path, local_path)
    try:
        sftp.get(remote_path, str(local_path))
    except IOError as e:
        LOGGER.error("Failed to download %s: %s", remote_path, e)
        raise


def fetch_purchasing_logs(  # pylint: disable=too-many-locals
    cfg: Dict[str, Any], temp_dir: Path
) -> List[Path]:
    """Fetch current laravel log and latest compressed rolled log."""
    ssh, sftp = open_sftp_client(cfg)
    try:
        directory = cfg["log_dir"]
        entries = list_remote_files(sftp, directory)
        if not entries:
            raise RuntimeError("No files found in purchasing log directory")

        current_candidates = [e for e in entries if e[0] == cfg.get("current_log_prefix", "laravel.log")]
        rolled_candidates = [e for e in entries if e[0].endswith(".gz") and e[0].startswith("laravel.log")]

        targets: List[str] = []
        if current_candidates:
            targets.append(current_candidates[0][0])
        if rolled_candidates:
            rolled_candidates.sort(key=lambda x: x[1], reverse=True)
            targets.append(rolled_candidates[0][0])

        if not targets:
            raise RuntimeError("Could not identify purchasing log files to fetch")

        downloaded: List[Path] = []
        for name in targets:
            remote = f"{directory.rstrip('/')}/{name}"
            local = temp_dir / "purchasing" / name
            download_remote_file(sftp, remote, local)
            if local.suffix == ".gz":
                extracted = local.with_suffix("")
                with gzip.open(local, "rb") as src, extracted.open("wb") as dst:
                    dst.write(src.read())
                downloaded.append(extracted)
            else:
                downloaded.append(local)
        return downloaded
    finally:
        sftp.close()
        ssh.close()


def month_keys(now: dt.datetime) -> List[str]:
    """Return current and previous YYYYMM keys for month boundary handling."""
    current = now.strftime("%Y%m")
    first_day = now.replace(day=1)
    prev = (first_day - dt.timedelta(days=1)).strftime("%Y%m")
    if prev == current:
        return [current]
    return [current, prev]


def fetch_processing_logs(cfg: Dict[str, Any], now: dt.datetime) -> List[Path]:
    """Resolve processing log files from direct filesystem access."""
    base = Path(cfg["base_path"])
    result: List[Path] = []
    for month in month_keys(now):
        for lob in cfg["lobs"]:
            path = base / f"{lob}_{month}.log"
            if path.exists():
                result.append(path)
    if not result:
        raise RuntimeError(f"No processing log files found in {base}")
    return result


def fetch_email_logs(cfg: Dict[str, Any], now: dt.datetime, temp_dir: Path) -> List[Path]:
    """Fetch emailing server log files for current and previous month."""
    ssh, sftp = open_sftp_client(cfg)
    try:
        directory = cfg["log_dir"]
        prefix = cfg.get("file_prefix", "send_policies_")
        result: List[Path] = []
        for month in month_keys(now):
            filename = f"{prefix}{month}.log"
            remote = f"{directory.rstrip('/')}/{filename}"
            local = temp_dir / "emailing" / filename
            try:
                download_remote_file(sftp, remote, local)
                result.append(local)
            except Exception:  # pylint: disable=broad-except
                LOGGER.warning("Emailing log not found or unreadable: %s", remote)
        if not result:
            raise RuntimeError("No emailing log files downloaded")
        return result
    finally:
        sftp.close()
        ssh.close()


def parse_laravel_ts(raw: str) -> dt.datetime:
    """Parse laravel timestamp format."""
    return dt.datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")


def parse_payment_success_logs(  # pylint: disable=too-many-locals
    paths: Sequence[Path], start_at: dt.datetime, end_at: dt.datetime
) -> List[PaymentRecord]:
    """Parse purchasing logs for accepted payment entries."""
    records: List[PaymentRecord] = []
    for path in paths:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                m = LARAVEL_LINE_RE.match(line.strip())
                if not m:
                    continue
                ts = parse_laravel_ts(m.group("ts"))
                if ts < (start_at - dt.timedelta(hours=2)) or ts > end_at:
                    continue
                msg = m.group("msg")
                session_id = ""
                session_match = SESSION_TRAILER_RE.search(msg)
                if session_match:
                    session_id = session_match.group("session")
                    msg = msg[: session_match.start()].strip()
                if not msg.startswith("Payment success data "):
                    continue
                payload_raw = msg[len("Payment success data ") :].strip()
                try:
                    payload = json.loads(payload_raw)
                except json.JSONDecodeError:
                    LOGGER.debug("Skipping unparsable Payment success data line in %s", path)
                    continue

                std = payload.get("data", {}).get("stdClass", {})
                status = str(std.get("payment_status", "")).lower()
                confirmation = str(std.get("braintree_id", "")).strip()
                if status != "success":
                    continue
                if not CONFIRMATION_RE.match(confirmation):
                    continue
                email = str(std.get("email", "")).strip()
                if not email:
                    continue
                purchase_time_raw = str(std.get("created_at", "")).strip()
                try:
                    purchase_time = dt.datetime.strptime(purchase_time_raw, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    purchase_time = ts
                if purchase_time < start_at or purchase_time > end_at:
                    continue

                records.append(
                    PaymentRecord(
                        confirmation_number=confirmation,
                        email=email,
                        purchase_time=purchase_time,
                        session_id=session_id,
                        source_file=str(path),
                        source_excerpt=line.strip()[:1200],
                    )
                )
    return records


def parse_processing_logs(  # pylint: disable=too-many-locals
    paths: Sequence[Path], start_at: dt.datetime, end_at: dt.datetime
) -> List[ProcessingRecord]:
    """Parse processing server logs for confirmation and risk mapping events."""
    base_events: Dict[str, ProcessingRecord] = {}

    for path in paths:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                text = line.rstrip("\n")
                m_proc = PROCESSING_RE.match(text)
                if m_proc:
                    ts = dt.datetime.strptime(m_proc.group("ts"), "%m/%d/%Y %H:%M:%S")
                    if ts < (start_at - dt.timedelta(days=1)) or ts > (end_at + dt.timedelta(days=1)):
                        continue
                    conf = m_proc.group("conf")
                    key = f"{conf}|{m_proc.group('policy')}"
                    base_events[key] = ProcessingRecord(
                        confirmation_number=conf,
                        policy_number=m_proc.group("policy"),
                        risk_number=(base_events[key].risk_number if key in base_events else None),
                        processing_time=ts,
                        lob=m_proc.group("lob"),
                        source_file=str(path),
                        source_excerpt=text[:1200],
                    )
                    continue

                m_risk = RISK_RE.match(text)
                if not m_risk:
                    continue
                ts = dt.datetime.strptime(m_risk.group("ts"), "%m/%d/%Y %H:%M:%S")
                if ts < (start_at - dt.timedelta(days=1)) or ts > (end_at + dt.timedelta(days=1)):
                    continue
                conf = m_risk.group("conf")
                policy = m_risk.group("policy")
                risk = m_risk.group("risk")
                key = f"{conf}|{policy}"
                if key in base_events:
                    current = base_events[key]
                    current.risk_number = risk
                    current.processing_time = min(current.processing_time, ts)
                    if not current.source_excerpt:
                        current.source_excerpt = text[:1200]
                else:
                    base_events[key] = ProcessingRecord(
                        confirmation_number=conf,
                        policy_number=policy,
                        risk_number=risk,
                        processing_time=ts,
                        lob=m_risk.group("lob"),
                        source_file=str(path),
                        source_excerpt=text[:1200],
                    )
    return list(base_events.values())


def parse_email_logs(paths: Sequence[Path], start_at: dt.datetime, end_at: dt.datetime) -> List[EmailRecord]:
    """Parse emailing logs for Full Policy sends keyed by risk number."""
    records: List[EmailRecord] = []
    for path in paths:
        current_run_ts: Optional[dt.datetime] = None
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                text = line.strip()
                run_match = RUNNING_RE.match(text)
                if run_match:
                    ts_raw = run_match.group("ts")
                    try:
                        current_run_ts = dt.datetime.strptime(ts_raw, "%a %b %d %H:%M:%S %Y")
                    except ValueError:
                        current_run_ts = None
                    continue
                email_match = EMAIL_LINE_RE.match(text)
                if not email_match:
                    continue
                if current_run_ts is None:
                    continue
                if current_run_ts < (start_at - dt.timedelta(days=1)) or current_run_ts > (end_at + dt.timedelta(days=1)):
                    continue
                records.append(
                    EmailRecord(
                        risk_number=email_match.group("risk"),
                        email_time=current_run_ts,
                        kind=email_match.group("kind"),
                        source_file=str(path),
                        source_excerpt=text[:1200],
                    )
                )
    return records


def evaluate_correlations(store: SQLiteStore, now: dt.datetime, grace_hours: int) -> None:
    """Correlate payments with processing and emailing status outcomes."""
    for payment in store.load_payments_for_evaluation(now, grace_hours):
        purchase_time = dt.datetime.fromisoformat(payment["purchase_time"])
        processing = store.find_processing_for_payment(payment["confirmation_number"], purchase_time)

        if not processing:
            outcome = CorrelationOutcome(
                payment_id=int(payment["id"]),
                status="missing_processing",
                processing_event_id=None,
                email_event_id=None,
                details={"reason": "No matching confirmation found in processing logs"},
            )
            store.upsert_correlation(outcome, now)
            continue

        risk_number = processing["risk_number"]
        if not risk_number:
            outcome = CorrelationOutcome(
                payment_id=int(payment["id"]),
                status="missing_email",
                processing_event_id=int(processing["id"]),
                email_event_id=None,
                details={"reason": "Processing entry found but risk number not available"},
            )
            store.upsert_correlation(outcome, now)
            continue

        processing_time = dt.datetime.fromisoformat(processing["processing_time"])
        email_evt = store.find_email_for_risk(risk_number, processing_time)
        if not email_evt:
            outcome = CorrelationOutcome(
                payment_id=int(payment["id"]),
                status="missing_email",
                processing_event_id=int(processing["id"]),
                email_event_id=None,
                details={"reason": "No Full Policy email found for risk number"},
            )
            store.upsert_correlation(outcome, now)
            continue

        outcome = CorrelationOutcome(
            payment_id=int(payment["id"]),
            status="success",
            processing_event_id=int(processing["id"]),
            email_event_id=int(email_evt["id"]),
            details={"reason": "Flow completed successfully"},
        )
        store.upsert_correlation(outcome, now)


def safe_path(base_root: str, day_str: str, confirmation: str) -> Path:
    """Build evidence path, falling back to local directory if share is not writable."""
    preferred = Path(base_root) / day_str / confirmation
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        return preferred
    except Exception:  # pylint: disable=broad-except
        fallback = Path.cwd() / "ONLINE_PURCHASING_FAILURES" / day_str / confirmation
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def write_evidence_bundle(row: sqlite3.Row, output_root: str, store: SQLiteStore) -> Path:
    """Write evidence snippets for a failure to a stable per-confirmation folder."""
    purchase_ts = dt.datetime.fromisoformat(row["purchase_time"])
    folder = safe_path(output_root, purchase_ts.strftime("%Y-%m-%d"), row["confirmation_number"])

    payment = store.conn.execute("SELECT * FROM payments WHERE id = ?", (row["payment_id"],)).fetchone()
    processing = None
    if row["processing_event_id"]:
        processing = store.conn.execute(
            "SELECT * FROM processing_events WHERE id = ?",
            (row["processing_event_id"],),
        ).fetchone()

    summary_path = folder / "summary.json"
    summary = {
        "status": row["status"],
        "confirmation_number": row["confirmation_number"],
        "email": row["email"],
        "purchase_time": row["purchase_time"],
        "session_id": row["session_id"],
        "policy_number": row["policy_number"],
        "risk_number": row["risk_number"],
        "processing_time": row["processing_time"],
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if payment:
        (folder / "purchasing_excerpt.log").write_text(payment["source_excerpt"] or "", encoding="utf-8")
    if processing:
        (folder / "processing_excerpt.log").write_text(processing["source_excerpt"] or "", encoding="utf-8")

    return folder


def build_alert_body(rows: Sequence[sqlite3.Row], evidence_map: Dict[int, Path]) -> str:
    """Build multi-failure alert email body."""
    lines: List[str] = []
    lines.append("Online purchasing flow alerts were detected.")
    lines.append("")
    for idx, row in enumerate(rows, start=1):
        lines.append(f"Failure {idx}")
        lines.append(f"Type: {row['status']}")
        lines.append(f"Confirmation Number: {row['confirmation_number']}")
        lines.append(f"Email Address: {row['email']}")
        lines.append(f"Time of Purchase: {row['purchase_time']}")
        lines.append(f"Session ID: {row['session_id']}")
        if row["policy_number"]:
            lines.append(f"Policy Number: {row['policy_number']}")
        if row["processing_time"]:
            lines.append(f"Time of Processing: {row['processing_time']}")
        if row["risk_number"]:
            lines.append(f"Risk Number: {row['risk_number']}")
        elif row["status"] == "missing_email":
            lines.append("Risk Number: not available")
        lines.append(f"Evidence Location: {evidence_map[int(row['payment_id'])]}")
        lines.append("")
    return "\n".join(lines)


def send_alert_email(
    smtp_cfg: Dict[str, Any],
    recipients: Sequence[str],
    body: str,
    failure_count: int,
    dry_run: bool,
) -> None:
    """Send failure email via SMTP relay."""
    subject_prefix = smtp_cfg.get("subject_prefix", "[Online Purchasing Monitor]")
    msg = EmailMessage()
    msg["From"] = smtp_cfg["from_email"]
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = f"{subject_prefix} {failure_count} flow alert(s)"
    msg.set_content(body)

    if dry_run:
        LOGGER.info("Dry run enabled; alert email not sent")
        LOGGER.info("Would send to: %s", ", ".join(recipients))
        LOGGER.info("Body:\n%s", body)
        return

    host = smtp_cfg["host"]
    port = int(smtp_cfg.get("port", 25))
    username = smtp_cfg.get("username", "")
    password = os.getenv(smtp_cfg.get("password_env", ""), "")

    with smtplib.SMTP(host, port, timeout=30) as server:
        if smtp_cfg.get("use_tls", False):
            server.starttls()
        if username:
            server.login(username, password)
        server.send_message(msg)


def determine_start_at(
    store: SQLiteStore,
    now: dt.datetime,
    cli_lookback_hours: Optional[int],
    first_run_lookback_hours: int,
) -> dt.datetime:
    """Determine start timestamp for source parsing window."""
    if cli_lookback_hours is not None:
        return now - dt.timedelta(hours=cli_lookback_hours)

    last = store.get_state("last_successful_run_at")
    if last:
        return dt.datetime.fromisoformat(last)

    return now - dt.timedelta(hours=first_run_lookback_hours)


def run_monitor(args: argparse.Namespace) -> int:  # pylint: disable=too-many-locals
    """Main orchestration entrypoint."""
    recipients = normalize_email_recipients(args.emails)
    if not recipients:
        raise ValueError("At least one valid recipient email is required")

    config = load_config(args.config)
    monitor_cfg = config["monitor"]
    smtp_cfg = config["smtp"]

    db_path = args.state_db or monitor_cfg["db_path"]
    output_root = args.output_root or monitor_cfg["output_root"]

    require_config_fields(
        config,
        [
            ("purchasing", "host"),
            ("purchasing", "username"),
            ("purchasing", "log_dir"),
            ("processing", "base_path"),
            ("emailing", "host"),
            ("emailing", "username"),
            ("emailing", "log_dir"),
            ("smtp", "host"),
            ("smtp", "from_email"),
        ],
    )

    now = parse_now(args.now)
    store = SQLiteStore(db_path)
    try:
        start_at = determine_start_at(
            store,
            now,
            args.lookback_hours,
            int(monitor_cfg.get("first_run_lookback_hours", 24)),
        )
        LOGGER.info("Monitoring window start: %s", start_at.isoformat(sep=" "))

        with tempfile.TemporaryDirectory(prefix="purchasing-monitor-") as temp_raw:
            temp_dir = Path(temp_raw)

            purchasing_paths = fetch_purchasing_logs(config["purchasing"], temp_dir)
            processing_paths = fetch_processing_logs(config["processing"], now)
            emailing_paths = fetch_email_logs(config["emailing"], now, temp_dir)

            payment_records = parse_payment_success_logs(purchasing_paths, start_at, now)
            processing_records = parse_processing_logs(processing_paths, start_at, now)
            email_records = parse_email_logs(emailing_paths, start_at, now)

            LOGGER.info("Parsed payments=%d processing=%d emailing=%d", len(payment_records), len(processing_records), len(email_records))

            for record in payment_records:
                store.upsert_payment(record, now)
            for record in processing_records:
                store.upsert_processing(record, now)
            for record in email_records:
                store.upsert_email(record, now)

        evaluate_correlations(store, now, int(monitor_cfg.get("grace_hours", 2)))
        failures = store.get_unalerted_failures()
        LOGGER.info("New alertable failures found: %d", len(failures))

        if failures:
            evidence_map: Dict[int, Path] = {}
            for row in failures:
                payment_id = int(row["payment_id"])
                evidence_map[payment_id] = write_evidence_bundle(row, output_root, store)

            body = build_alert_body(failures, evidence_map)
            send_alert_email(
                smtp_cfg=smtp_cfg,
                recipients=recipients,
                body=body,
                failure_count=len(failures),
                dry_run=args.dry_run,
            )
            sent_at = dt.datetime.now()
            for row in failures:
                payment_id = int(row["payment_id"])
                fingerprint = f"{row['status']}|{row['confirmation_number']}"
                store.mark_alert_sent(payment_id, sent_at, fingerprint)
        else:
            LOGGER.info("No alerts triggered; no email sent")

        store.set_state("last_successful_run_at", now.isoformat(sep=" "))
        return 0
    finally:
        store.close()


def main() -> int:
    """CLI wrapper with top-level exception handling."""
    args = parse_args()
    setup_logging(args.verbose)
    try:
        return run_monitor(args)
    except Exception as exc:  # pylint: disable=broad-except
        LOGGER.exception("Monitor run failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
