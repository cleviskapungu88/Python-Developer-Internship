"""
STEP 4 — notifier.py
Sends a coloured console banner after every run.
If email is enabled in config.json, also sends an HTML email summary.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from datetime             import datetime


# ── ANSI colour helpers (work on any modern terminal) ─────────────────────────
_GREEN  = "\033[92m"
_YELLOW = "\033[93m"
_RED    = "\033[91m"
_CYAN   = "\033[96m"
_BOLD   = "\033[1m"
_RESET  = "\033[0m"


def _banner_line(char: str = "─", width: int = 58) -> str:
    return char * width


class Notifier:
    """Handles console + optional email notifications."""

    def __init__(self, email_config: dict | None = None):
        """
        Args:
            email_config: The 'email' block from config.json,
                          or None / {'enabled': false} to disable email.
        """
        self.email_cfg = email_config or {}

    # ── Console notification ───────────────────────────────────────────────────

    def notify_console(self, result: dict, report_paths: dict | None = None) -> None:
        """Print a colour-formatted run summary to stdout."""
        summary = result["summary"]
        errors  = result["errors"]
        total   = sum(len(v) for v in summary.values())
        status  = (_GREEN + "✓ SUCCESS" if not errors
                   else _YELLOW + f"⚠ DONE WITH {len(errors)} ERROR(S)")

        print(f"\n{_BOLD}{_CYAN}{_banner_line('═')}{_RESET}")
        print(f"{_BOLD}  AUTO-ORGANIZER — RUN COMPLETE  {_RESET}")
        print(f"{_CYAN}{_banner_line('═')}{_RESET}")
        print(f"  Status      : {status}{_RESET}")
        print(f"  Files moved : {_BOLD}{total}{_RESET}")
        print(f"  Errors      : {_RED if errors else ''}{len(errors)}{_RESET}")
        print(f"  Timestamp   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{_CYAN}{_banner_line()}{_RESET}")

        for category, files in summary.items():
            if files:
                bar   = "█" * min(len(files), 20)
                print(f"  {category:<15} {bar}  {len(files)}")

        if errors:
            print(f"\n{_RED}  Errors:{_RESET}")
            for e in errors:
                print(f"    ✗ {e['file']}")

        if report_paths:
            print(f"\n{_CYAN}  Reports saved:{_RESET}")
            for fmt, path in report_paths.items():
                print(f"    [{fmt.upper()}] {path}")

        print(f"{_CYAN}{_banner_line('═')}{_RESET}\n")

    # ── Email notification ─────────────────────────────────────────────────────

    def notify_email(self, result: dict, report_paths: dict | None = None) -> bool:
        """
        Send an HTML email summary if email is enabled in config.

        Returns True on success, False on failure.
        """
        cfg = self.email_cfg
        if not cfg.get("enabled", False):
            return False

        summary = result["summary"]
        errors  = result["errors"]
        total   = sum(len(v) for v in summary.values())

        subject = (
            f"[AutoOrganizer] ✓ {total} files organised"
            if not errors
            else f"[AutoOrganizer] ⚠ Done — {len(errors)} error(s)"
        )

        rows = "".join(
            f"<tr><td>{cat}</td><td>{len(files)}</td></tr>"
            for cat, files in summary.items()
            if files
        )
        body = f"""
        <html><body style="font-family:Arial,sans-serif">
          <h2>AutoOrganizer Run Summary</h2>
          <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
          <p><strong>Files moved:</strong> {total} &nbsp;
             <strong>Errors:</strong> {len(errors)}</p>
          <table border="1" cellpadding="6" cellspacing="0">
            <tr style="background:#2980b9;color:#fff">
              <th>Category</th><th>Files</th>
            </tr>
            {rows}
          </table>
          {"<p style='color:red'>Errors occurred — check the log file.</p>" if errors else ""}
        </body></html>"""

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = cfg["sender"]
        msg["To"]      = cfg["recipient"]
        msg.attach(MIMEText(body, "html"))

        try:
            with smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"]) as server:
                server.starttls()
                server.login(cfg["sender"], cfg["password"])
                server.sendmail(cfg["sender"], cfg["recipient"], msg.as_string())
            return True
        except Exception as exc:
            print(f"{_RED}  Email failed: {exc}{_RESET}")
            return False
