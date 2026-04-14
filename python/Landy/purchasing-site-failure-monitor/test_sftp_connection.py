#!/usr/bin/env python3
"""
Test SFTP connectivity and diagnose permission issues.

Usage:
    python test_sftp_connection.py --config config.yaml --target purchasing
    python test_sftp_connection.py --config config.yaml --target emailing
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import paramiko
import yaml

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger("sftp_diagnostic")


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


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
            # pylint: disable=consider-using-f-string
            logger.info("Attempting key auth with %s", key_path)
            client.connect(hostname=host, port=port, username=username,
                          key_filename=key_path, timeout=20)
            logger.info("✓ Key authentication successful")
            return client, client.open_sftp()
        except Exception as exc:  # pylint: disable=broad-except
            errors.append("key auth failed: %s" % exc)
            logger.warning("Key auth failed: %s", exc)

    if password:
        try:
            logger.info("Attempting password auth")
            client.connect(hostname=host, port=port, username=username,
                          password=password, timeout=20)
            logger.info("✓ Password authentication successful")
            return client, client.open_sftp()
        except Exception as exc:  # pylint: disable=broad-except
            errors.append("password auth failed: %s" % exc)
            logger.error("Password auth failed: %s", exc)

    raise RuntimeError(  # pylint: disable=consider-using-f-string
        "All auth methods failed: %s" % errors)


def test_sftp_target(config: Dict[str, Any], target: str) -> None:  # pylint: disable=consider-using-f-string
    """Test SFTP connectivity and file access for a target."""
    if target not in config:
        logger.error("Target '%s' not found in config", target)
        sys.exit(1)

    cfg = config[target]
    # pylint: disable=consider-using-f-string
    sep = "=" * 60
    logger.info("\n%s", sep)
    logger.info("Testing %s SFTP target", target.upper())
    logger.info("%s", sep)
    logger.info("Host: %s", cfg["host"])
    logger.info("Port: %s", cfg.get("port", 22))
    logger.info("Username: %s", cfg["username"])
    logger.info("Log dir: %s", cfg.get("log_dir"))

    ssh, sftp = None, None
    try:
        ssh, sftp = open_sftp_client(cfg)

        log_dir = cfg.get("log_dir")
        if not log_dir:
            logger.error("No 'log_dir' configured for this target")
            return

        logger.info("\nListing files in %s...", log_dir)
        try:
            entries = []
            for attr in sftp.listdir_attr(log_dir):
                size_kb = attr.st_size / 1024
                logger.info("  ✓ %s (%.1f KB, mtime=%s)", attr.filename, size_kb, attr.st_mtime)
                entries.append(attr.filename)

            if not entries:
                logger.warning("No files found in %s", log_dir)
                return

            logger.info("\nAttempting to read first file: %s", entries[0])
            remote_path = "%s/%s" % (log_dir.rstrip("/"), entries[0])  # pylint: disable=consider-using-f-string
            logger.info("Full remote path: %s", remote_path)

            # Try to stat the file
            try:
                stat_result = sftp.stat(remote_path)
                logger.info("✓ File stat successful: size=%s, mode=%s",
                           stat_result.st_size, oct(stat_result.st_mode))
            except IOError as e:
                logger.error("✗ File stat failed: %s", e)
                return

            # Try to open the file
            try:
                with sftp.open(remote_path, "r") as f:  # pylint: disable=unspecified-encoding
                    first_line = f.readline()
                    logger.info("✓ File read successful. First line preview:")
                    logger.info("  %s...", first_line[:100])
            except IOError as e:
                logger.error("✗ File read failed: %s", e)
                return

        except IOError as e:
            logger.error("✗ Directory listing failed: %s", e)
            logger.error("  This usually means the directory doesn't exist "
                        "or user lacks read permission")
            return

    finally:
        if sftp:
            sftp.close()
        if ssh:
            ssh.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test SFTP connectivity and diagnose permission issues")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument("--target", choices=["purchasing", "emailing"], required=True,
                        help="Which target to test")
    args = parser.parse_args()

    if not Path(args.config).exists():
        logger.error("Config file not found: %s", args.config)
        sys.exit(1)

    try:
        config = load_config(args.config)
        test_sftp_target(config, args.target)
        sep = "=" * 60
        logger.info("\n%s", sep)
        logger.info("✓ All tests passed!")
        logger.info("%s\n", sep)
    except Exception as e:  # pylint: disable=broad-except
        sep = "=" * 60
        logger.error("\n%s", sep)
        logger.error("✗ Test failed with error:")
        logger.error(str(e))
        logger.error("%s\n", sep)
        sys.exit(1)


if __name__ == "__main__":
    main()
