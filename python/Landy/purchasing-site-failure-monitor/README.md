# Online Policy Purchasing Flow Monitor

This script monitors policy purchases from the online purchasing flow and checks whether each payment reached:

1. Processing logs (confirmation number found)
2. Emailing logs (Full Policy send found)

It stores all outcomes in SQLite and sends alert email **only when new failures are found**.

## What It Detects

- Missing processing transfer:
  - Payment exists in purchasing logs, but no confirmation number found in processing logs
- Missing emailing completion:
  - Payment exists and processing exists, but no matching Full Policy email event
- Success:
  - Payment, processing, and emailing all found

A payment is not considered failed until it is at least 2 hours old (configurable).

## Prerequisites

- Python 3.9+
- Network access to:
  - Purchasing server over SFTP (`/var/www/html/storage/logs`)
  - Processing logs direct path (`\\ix200\\pdf_files\\garf\\Scheduled-Jobs-Logs`)
  - Emailing server over SSH/SFTP (`/home/sendmail/logs`)
  - SMTP relay for alerts

## Installation

From this folder:

```bash
python -m pip install -r requirements.txt
```

Create config and secrets:

```bash
cp config.example.yaml config.yaml
cp .env.example .env
```

Populate:

- `config.yaml` with hostnames, usernames, key paths, and SMTP settings
- environment variables from `.env` in your scheduler/runtime environment

## Command

```bash
python purchasing_site_failure_monitor.py \
  --emails ops1@domain.com ops2@domain.com
```

You can also pass comma-separated recipients:

```bash
python purchasing_site_failure_monitor.py --emails ops1@domain.com,ops2@domain.com
```

## Important Options

- `--config`: Config file path (default `config.yaml`)
- `--state-db`: Override SQLite DB path
- `--output-root`: Override evidence root path
- `--lookback-hours`: Force lookback window for this run
- `--now`: Test-time override (ISO timestamp)
- `--dry-run`: Build failures/evidence but do not send email
- `--verbose`: Debug logging

## Scheduler (Hourly)

Example cron:

```cron
0 * * * * cd /path/to/purchasing-site-failure-monitor && /path/to/python purchasing_site_failure_monitor.py --emails ops@domain.com >> monitor.log 2>&1
```

## Monthly Executive Summary

Use the monthly script to email an executive summary for the previous month,
including success/failure counts by LOB and CSV attachments.

Command:

```bash
python monthly_executive_summary.py --emails ops@domain.com
```

Generated CSV files:

- `summary_by_lob.csv`
- `accounts_success.csv`
- `accounts_failure.csv`

By default, these are written to:

- `./monthly-executive-reports/YYYY-MM/`

Monthly scheduler example (first day at 06:00):

```cron
0 6 1 * * cd /path/to/purchasing-site-failure-monitor && /path/to/python monthly_executive_summary.py --emails ops@domain.com >> monthly-summary.log 2>&1
```

Optional flags:

- `--as-of`: override period calculation (ISO date/datetime)
- `--state-db`: override SQLite path
- `--output-dir`: override CSV output root
- `--dry-run`: generate reports without sending email

## Data and Evidence

### SQLite

Creates SQLite DB automatically if missing. Tracks:

- Payments
- Processing events
- Email events
- Correlation status
- Alert-sent flags
- Last successful run timestamp

### Failure Evidence

Failure artifacts are written to:

- `\\ix200\\pdf_files\\ONLINE_PURCHASING_FAILURES\\{yyyy-mm-dd}\\{confirmation}`

If the network path is unavailable/writable failure occurs, it falls back to:

- `./ONLINE_PURCHASING_FAILURES/{yyyy-mm-dd}/{confirmation}`

Each folder includes:

- `summary.json`
- `purchasing_excerpt.log`
- `processing_excerpt.log` (when available)

## First Run Behavior

If no prior successful run is stored in SQLite, the monitor backfills the previous 24 hours (configurable).

## Alerting Behavior

- Email is sent only when there are new alertable failures.
- No email is sent when:
  - no failures are found
  - entries are still within the grace window
  - the same failure has already been alerted

## Troubleshooting

- `Unable to connect` errors:
  - Verify host/username/key path
  - Confirm password env var exists if fallback auth is needed
- No processing logs found:
  - Verify UNC/mounted path and month-specific files (`ga_apolar_YYYYMM.log`, etc.)
- No emailing logs found:
  - Verify remote path and server access
- No alerts but expected failures:
  - Check grace window (`monitor.grace_hours`)
  - Run once with `--verbose` and `--lookback-hours`

## Suggested Operations

- Rotate keys/passwords quarterly
- Backup SQLite DB periodically
- Retain evidence files for a fixed window (for example 90 days)
- Review alert volume weekly for parser tuning
