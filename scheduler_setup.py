"""
STEP 5 — scheduler_setup.py
Uses the lightweight `schedule` library to run the organizer on a loop.
Also prints the Windows Task Scheduler / Linux cron equivalent commands.

Usage:
    python scheduler_setup.py --interval 30           # every 30 minutes
    python scheduler_setup.py --interval 60 --unit h  # every 1 hour
    python scheduler_setup.py --daily 08:00           # once a day at 08:00
    python scheduler_setup.py --show-cron             # print OS scheduler commands
"""

import argparse
import sys
import time
import os
import schedule
from datetime    import datetime
from organizer   import FileOrganizer
from reporter    import Reporter
from notifier    import Notifier
from logger_setup import get_logger


CONFIG_PATH = "config.json"
LOG_PATH    = "./logs/organizer.log"


def run_once() -> None:
    """Single organizer pass — called by schedule or directly."""
    logger = get_logger(LOG_PATH)
    logger.info("⏰ Scheduled run triggered at %s", datetime.now().isoformat())

    import json
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)

    org     = FileOrganizer(CONFIG_PATH)
    result  = org.run()

    rep     = Reporter(cfg.get("report_folder", "./reports"))
    paths   = rep.generate(result)

    notif   = Notifier(cfg.get("email"))
    notif.notify_console(result, paths)
    notif.notify_email(result, paths)


def show_os_commands(interval_min: int) -> None:
    """Print ready-to-use scheduler commands for Windows & Linux."""
    script = os.path.abspath("main.py")
    python = sys.executable

    print("\n" + "═" * 60)
    print("  OS-LEVEL SCHEDULER COMMANDS")
    print("═" * 60)

    # ── Windows Task Scheduler ─────────────────────────────────────────────
    print("\n[Windows — Task Scheduler]")
    print(f"  schtasks /Create /SC MINUTE /MO {interval_min} \\")
    print(f'    /TN "AutoOrganizer" \\')
    print(f'    /TR "{python} {script}" \\')
    print( '    /F')
    print("\n  Or open Task Scheduler GUI → Create Basic Task → set trigger.")

    # ── Linux / macOS cron ─────────────────────────────────────────────────
    print("\n[Linux / macOS — crontab]")
    print("  Open with:  crontab -e")
    print(f"  Add line:   */{interval_min} * * * * {python} {script} >> ~/cron.log 2>&1")

    print("\n" + "═" * 60 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Schedule the File Organizer to run automatically."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--interval", type=int, metavar="MINUTES",
        help="Run every N minutes (e.g. --interval 30)"
    )
    group.add_argument(
        "--daily", metavar="HH:MM",
        help="Run once per day at the given time (e.g. --daily 08:00)"
    )
    group.add_argument(
        "--show-cron", action="store_true",
        help="Print OS scheduler commands and exit"
    )
    parser.add_argument(
        "--run-now", action="store_true",
        help="Execute one immediate run before entering the schedule loop"
    )
    args = parser.parse_args()

    # ── Just print cron commands ───────────────────────────────────────────
    if args.show_cron:
        show_os_commands(interval_min=30)
        return

    logger = get_logger(LOG_PATH)

    # ── Optional immediate run ─────────────────────────────────────────────
    if args.run_now:
        logger.info("--run-now flag set — running immediately.")
        run_once()

    # ── Register schedule ──────────────────────────────────────────────────
    if args.interval:
        schedule.every(args.interval).minutes.do(run_once)
        logger.info("Scheduler started — running every %d minute(s).", args.interval)
        print(f"\n  ⏰ Scheduler active — runs every {args.interval} minute(s).")
        show_os_commands(args.interval)
    elif args.daily:
        schedule.every().day.at(args.daily).do(run_once)
        logger.info("Scheduler started — daily at %s.", args.daily)
        print(f"\n  ⏰ Scheduler active — runs daily at {args.daily}.")
        show_os_commands(interval_min=0)

    print("  Press Ctrl+C to stop.\n")
    try:
        while True:
            schedule.run_pending()
            time.sleep(30)          # check every 30 s
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user.")
        print("\n  Scheduler stopped.")


if __name__ == "__main__":
    main()
