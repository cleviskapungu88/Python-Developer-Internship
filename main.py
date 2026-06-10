"""
STEP 6 — main.py  ★ Entry Point ★
Ties every module together and exposes a clean CLI.

Usage examples
──────────────
# Organise files (normal run)
    python main.py

# Dry-run (no files actually moved)
    python main.py --dry-run

# Use a custom config file
    python main.py --config /path/to/my_config.json

# Only show the last report (no organising)
    python main.py --report-only

# Generate test files first, then organise
    python main.py --seed-test-data

# Schedule: run every 15 minutes
    python scheduler_setup.py --interval 15 --run-now
"""

import argparse
import json
import os
import sys
from pathlib import Path

from organizer    import FileOrganizer
from reporter     import Reporter
from notifier     import Notifier
from logger_setup import get_logger


# ── Helpers ───────────────────────────────────────────────────────────────────

def seed_test_data(source_folder: str) -> None:
    """Create dummy files in source_folder for quick testing."""
    import random, string

    samples = {
        "photo_holiday.jpg":   b"\xff\xd8\xff" + b"\x00" * 100,
        "photo_profile.png":   b"\x89PNG\r\n"  + b"\x00" * 100,
        "notes.txt":           b"Hello, World!\nLine 2\n",
        "budget.xlsx":         b"PK\x03\x04" + b"\x00" * 50,
        "report.pdf":          b"%PDF-1.4\n"  + b"\x00" * 50,
        "project.py":          b"print('Automation!')\n",
        "movie_clip.mp4":      b"\x00\x00\x00\x18ftyp" + b"\x00" * 100,
        "song.mp3":            b"ID3\x03\x00" + b"\x00" * 100,
        "archive.zip":         b"PK\x05\x06" + b"\x00" * 22,
        "presentation.pptx":   b"PK\x03\x04" + b"\x00" * 50,
        "unknown_file.xyz":    b"???" + b"\x00" * 20,
        "style.css":           b"body { margin: 0; }\n",
    }

    src = Path(source_folder)
    src.mkdir(parents=True, exist_ok=True)

    for filename, content in samples.items():
        (src / filename).write_bytes(content)

    print(f"  ✔ Created {len(samples)} test file(s) in: {src.resolve()}\n")


def show_latest_report(report_folder: str) -> None:
    """Print the latest TXT report to stdout."""
    folder = Path(report_folder)
    txts   = sorted(folder.glob("report_*.txt"), reverse=True)
    if not txts:
        print("  No reports found yet.")
        return
    latest = txts[0]
    print(f"\n  Showing: {latest}\n")
    print(latest.read_text(encoding="utf-8"))


# ── CLI ────────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog        = "main.py",
        description = "AutoOrganizer — Bulk File Organizer & Report Generator",
        epilog      = "For scheduling: python scheduler_setup.py --help",
    )
    p.add_argument(
        "--config", default="config.json", metavar="PATH",
        help="Path to the JSON config file (default: config.json)"
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="Show what would happen without actually moving files"
    )
    p.add_argument(
        "--report-only", action="store_true",
        help="Display the latest report without running the organizer"
    )
    p.add_argument(
        "--seed-test-data", action="store_true",
        help="Populate source_folder with sample files for testing"
    )
    p.add_argument(
        "--no-report", action="store_true",
        help="Skip report generation"
    )
    p.add_argument(
        "--no-notify", action="store_true",
        help="Skip all notifications"
    )
    return p


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> int:
    args = build_parser().parse_args()

    # Load config early so we can read folder paths
    if not os.path.exists(args.config):
        print(f"  ✗ Config file not found: {args.config}")
        return 1

    with open(args.config, encoding="utf-8") as f:
        cfg = json.load(f)

    logger = get_logger(cfg.get("log_file", "./logs/organizer.log"))

    # ── --report-only ─────────────────────────────────────────────────────────
    if args.report_only:
        show_latest_report(cfg.get("report_folder", "./reports"))
        return 0

    # ── --seed-test-data ──────────────────────────────────────────────────────
    if args.seed_test_data:
        logger.info("Seeding test data into: %s", cfg["source_folder"])
        seed_test_data(cfg["source_folder"])

    # ── Run organizer ─────────────────────────────────────────────────────────
    try:
        org    = FileOrganizer(args.config)
        result = org.run(dry_run=args.dry_run)
    except Exception as exc:
        logger.critical("Fatal error in organizer: %s", exc, exc_info=True)
        return 2

    # ── Generate reports ──────────────────────────────────────────────────────
    report_paths = {}
    if not args.no_report:
        try:
            rep          = Reporter(cfg.get("report_folder", "./reports"))
            report_paths = rep.generate(result)
            logger.info("Reports saved: %s", report_paths)
        except Exception as exc:
            logger.error("Report generation failed: %s", exc)

    # ── Notifications ─────────────────────────────────────────────────────────
    if not args.no_notify:
        notif = Notifier(cfg.get("email"))
        notif.notify_console(result, report_paths)

        if cfg.get("email", {}).get("enabled", False):
            sent = notif.notify_email(result, report_paths)
            logger.info("Email notification: %s", "sent" if sent else "failed")

    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
