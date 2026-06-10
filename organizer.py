"""
STEP 2 — organizer.py
Core engine: scans the source folder, sorts files into category sub-folders,
and returns a summary dict that other modules can use for reporting / notifications.
"""

import os
import shutil
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from logger_setup import get_logger


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_config(config_path: str = "config.json") -> dict:
    """Load and validate the JSON config file."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_category(extension: str, categories: dict) -> str:
    """
    Map a file extension (e.g. '.jpg') to a category name.
    Falls back to 'Others' when the extension is not listed anywhere.
    """
    ext = extension.lower()
    for category, extensions in categories.items():
        if ext in extensions:
            return category
    return "Others"


# ── Main organizer ─────────────────────────────────────────────────────────────

class FileOrganizer:
    """
    Scans *source_folder*, moves every file into a matching category sub-folder
    inside *output_folder*, and records every action in a structured summary.
    """

    def __init__(self, config_path: str = "config.json"):
        self.config      = load_config(config_path)
        self.logger      = get_logger(
            self.config["log_file"], name="AutoOrganizer"
        )
        self.source      = Path(self.config["source_folder"])
        self.destination = Path(self.config["output_folder"])
        self.categories  = self.config["categories"]

        # ── Summary populated during run() ────────────────────────────────────
        self.summary: Dict[str, List[dict]] = {cat: [] for cat in self.categories}
        self.summary["Others"] = []
        self.errors: List[dict] = []
        self.start_time: datetime | None = None
        self.end_time:   datetime | None = None

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _ensure_dirs(self) -> None:
        """Make sure source and output directories exist."""
        if not self.source.exists():
            self.logger.warning(
                "Source folder does not exist — creating it: %s", self.source
            )
            self.source.mkdir(parents=True)
        self.destination.mkdir(parents=True, exist_ok=True)

    def _resolve_conflict(self, dest_path: Path) -> Path:
        """
        If *dest_path* already exists, append _(1), _(2), … until the name is
        unique.  This prevents accidental overwriting.
        """
        if not dest_path.exists():
            return dest_path
        stem, suffix, parent = dest_path.stem, dest_path.suffix, dest_path.parent
        counter = 1
        while True:
            candidate = parent / f"{stem}_({counter}){suffix}"
            if not candidate.exists():
                return candidate
            counter += 1

    # ── Public API ─────────────────────────────────────────────────────────────

    def run(self, dry_run: bool = False) -> dict:
        """
        Organise files from source_folder → output_folder.

        Args:
            dry_run: When True, log what *would* happen but don't move anything.

        Returns:
            A summary dict with keys per category plus 'errors'.
        """
        self.start_time = datetime.now()
        mode_tag = "[DRY-RUN] " if dry_run else ""
        self.logger.info("=" * 60)
        self.logger.info("%sOrganizer started — source: %s", mode_tag, self.source)
        self._ensure_dirs()

        # Collect all files (non-recursive; skip hidden files)
        files = [
            f for f in self.source.iterdir()
            if f.is_file() and not f.name.startswith(".")
        ]

        if not files:
            self.logger.warning("No files found in source folder.")
            self.end_time = datetime.now()
            return self._build_result()

        self.logger.info("Found %d file(s) to process.", len(files))

        for file_path in files:
            try:
                ext      = file_path.suffix
                category = get_category(ext, self.categories)
                cat_dir  = self.destination / category
                cat_dir.mkdir(parents=True, exist_ok=True)

                dest = self._resolve_conflict(cat_dir / file_path.name)

                # Capture size BEFORE moving (file won't exist at original path after)
                size_bytes = file_path.stat().st_size

                if dry_run:
                    self.logger.info(
                        "[DRY-RUN] Would move '%s' → %s/", file_path.name, category
                    )
                else:
                    shutil.move(str(file_path), str(dest))
                    self.logger.info(
                        "Moved '%s' → %s/", file_path.name, category
                    )

                self.summary[category].append({
                    "original":    str(file_path),
                    "destination": str(dest),
                    "extension":   ext,
                    "size_bytes":  size_bytes,
                    "moved_at":    datetime.now().isoformat(),
                })

            except Exception as exc:
                self.logger.error("ERROR processing '%s': %s", file_path.name, exc)
                self.errors.append({"file": str(file_path), "error": str(exc)})

        self.end_time = datetime.now()
        elapsed = (self.end_time - self.start_time).total_seconds()
        total_moved = sum(len(v) for v in self.summary.values())
        self.logger.info(
            "%sFinished — %d moved, %d errors, %.2fs elapsed.",
            mode_tag, total_moved, len(self.errors), elapsed,
        )
        self.logger.info("=" * 60)
        return self._build_result()

    def _build_result(self) -> dict:
        """Assemble the final summary dict."""
        return {
            "summary":    self.summary,
            "errors":     self.errors,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time":   self.end_time.isoformat()   if self.end_time   else None,
            "source":     str(self.source),
            "destination":str(self.destination),
        }
