"""
STEP 7 — setup_test.py
Automated test suite.  Runs four scenarios and prints a PASS / FAIL table.

Run with:
    python setup_test.py
"""

import json
import os
import shutil
import sys
from pathlib import Path

# ── Make sure project root is on sys.path ─────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

from organizer    import FileOrganizer
from reporter     import Reporter
from notifier     import Notifier
from logger_setup import get_logger

# ── ANSI colours ──────────────────────────────────────────────────────────────
GRN  = "\033[92m"; RED = "\033[91m"; YEL = "\033[93m"
CYN  = "\033[96m"; BLD = "\033[1m";  RST = "\033[0m"

LOG_FILE    = "./logs/test_run.log"
CONFIG_FILE = "config.json"


# ── Fixture helpers ───────────────────────────────────────────────────────────

def make_files(folder: Path, specs: dict[str, bytes]) -> None:
    """Write dummy files into *folder*."""
    folder.mkdir(parents=True, exist_ok=True)
    for name, content in specs.items():
        (folder / name).write_bytes(content)


def cleanup(folder: Path) -> None:
    if folder.exists():
        shutil.rmtree(folder)


# ── Individual tests ──────────────────────────────────────────────────────────

def test_normal_run() -> tuple[bool, str]:
    """SCENARIO 1 — Normal run: various file types are organised correctly."""
    src  = Path("./test_tmp/scenario1_src")
    dest = Path("./test_tmp/scenario1_dest")
    cleanup(src); cleanup(dest)

    make_files(src, {
        "photo.jpg":    b"\xff\xd8",
        "notes.txt":    b"hello",
        "budget.xlsx":  b"PK",
        "movie.mp4":    b"\x00ftyp",
        "script.py":    b"print(1)",
        "archive.zip":  b"PK",
        "unknown.xyz":  b"???",
    })

    # Temporarily patch config
    with open(CONFIG_FILE) as f:
        cfg = json.load(f)
    cfg["source_folder"] = str(src)
    cfg["output_folder"] = str(dest)
    patched_cfg = "./test_tmp/cfg1.json"
    Path("./test_tmp").mkdir(exist_ok=True)
    with open(patched_cfg, "w") as f:
        json.dump(cfg, f)

    org    = FileOrganizer(patched_cfg)
    result = org.run()

    moved   = sum(len(v) for v in result["summary"].values())
    ok      = moved == 7 and len(result["errors"]) == 0
    msg     = f"Moved {moved}/7 files, errors: {len(result['errors'])}"
    cleanup(src); cleanup(dest)
    return ok, msg


def test_dry_run() -> tuple[bool, str]:
    """SCENARIO 2 — Dry-run: files must NOT be moved."""
    src  = Path("./test_tmp/scenario2_src")
    dest = Path("./test_tmp/scenario2_dest")
    cleanup(src); cleanup(dest)
    make_files(src, {"doc.pdf": b"%PDF", "img.png": b"\x89PNG"})

    with open(CONFIG_FILE) as f:
        cfg = json.load(f)
    cfg["source_folder"] = str(src)
    cfg["output_folder"] = str(dest)
    patched_cfg = "./test_tmp/cfg2.json"
    with open(patched_cfg, "w") as f:
        json.dump(cfg, f)

    org = FileOrganizer(patched_cfg)
    org.run(dry_run=True)

    # Files must still be in source
    remaining = list(src.iterdir())
    ok  = len(remaining) == 2
    msg = f"Source still has {len(remaining)}/2 files after dry-run"
    cleanup(src); cleanup(dest)
    return ok, msg


def test_empty_folder() -> tuple[bool, str]:
    """SCENARIO 3 — Empty source folder: must not crash."""
    src  = Path("./test_tmp/scenario3_src")
    dest = Path("./test_tmp/scenario3_dest")
    cleanup(src); cleanup(dest)
    src.mkdir(parents=True)

    with open(CONFIG_FILE) as f:
        cfg = json.load(f)
    cfg["source_folder"] = str(src)
    cfg["output_folder"] = str(dest)
    patched_cfg = "./test_tmp/cfg3.json"
    with open(patched_cfg, "w") as f:
        json.dump(cfg, f)

    try:
        org    = FileOrganizer(patched_cfg)
        result = org.run()
        ok  = len(result["errors"]) == 0
        msg = "Handled empty folder without errors"
    except Exception as exc:
        ok  = False
        msg = f"Raised exception: {exc}"

    cleanup(src); cleanup(dest)
    return ok, msg


def test_report_generation() -> tuple[bool, str]:
    """SCENARIO 4 — Reporter creates both HTML and TXT files."""
    rpt_folder = Path("./test_tmp/reports")
    cleanup(rpt_folder)

    fake_result = {
        "summary":     {"Images": [{"extension": ".jpg", "size_bytes": 100,
                                    "original": "x.jpg", "destination": "d/x.jpg",
                                    "moved_at": "2024-01-01T00:00:00"}],
                         "Documents": [], "Videos": [], "Audio": [],
                         "Archives": [], "Code": [], "Others": []},
        "errors":      [],
        "start_time":  "2024-01-01T00:00:00",
        "end_time":    "2024-01-01T00:00:01",
        "source":      "./src",
        "destination": "./dest",
    }

    rep   = Reporter(str(rpt_folder))
    paths = rep.generate(fake_result)

    html_ok = Path(paths["html"]).exists()
    txt_ok  = Path(paths["txt"]).exists()
    ok  = html_ok and txt_ok
    msg = f"HTML={'✓' if html_ok else '✗'}  TXT={'✓' if txt_ok else '✗'}"
    return ok, msg


def test_duplicate_handling() -> tuple[bool, str]:
    """SCENARIO 5 — Conflict resolution: duplicate filenames get renamed."""
    src  = Path("./test_tmp/scenario5_src")
    dest = Path("./test_tmp/scenario5_dest")
    cleanup(src); cleanup(dest)

    # Pre-place a file at the destination to force a conflict
    (dest / "Images").mkdir(parents=True, exist_ok=True)
    (dest / "Images" / "photo.jpg").write_bytes(b"original")
    make_files(src, {"photo.jpg": b"\xff\xd8"})

    with open(CONFIG_FILE) as f:
        cfg = json.load(f)
    cfg["source_folder"] = str(src)
    cfg["output_folder"] = str(dest)
    patched_cfg = "./test_tmp/cfg5.json"
    with open(patched_cfg, "w") as f:
        json.dump(cfg, f)

    org    = FileOrganizer(patched_cfg)
    result = org.run()

    # Both original and renamed file should now be in Images/
    images = list((dest / "Images").iterdir())
    ok  = len(images) == 2 and len(result["errors"]) == 0
    msg = f"Images/ has {len(images)} file(s) — no overwrite, no errors"
    cleanup(src); cleanup(dest)
    return ok, msg


# ── Test runner ────────────────────────────────────────────────────────────────

TESTS = [
    ("Normal run (7 files)",           test_normal_run),
    ("Dry-run (files stay in place)",  test_dry_run),
    ("Empty source folder",            test_empty_folder),
    ("Report generation (HTML + TXT)", test_report_generation),
    ("Duplicate file conflict",        test_duplicate_handling),
]


def run_all() -> None:
    print(f"\n{BLD}{CYN}{'═'*60}{RST}")
    print(f"{BLD}  AUTO-ORGANIZER — TEST SUITE{RST}")
    print(f"{CYN}{'═'*60}{RST}\n")

    results = []
    for name, fn in TESTS:
        try:
            ok, msg = fn()
        except Exception as exc:
            ok, msg = False, str(exc)

        tag = f"{GRN}PASS{RST}" if ok else f"{RED}FAIL{RST}"
        print(f"  [{tag}]  {name}")
        print(f"          {YEL}{msg}{RST}\n")
        results.append(ok)

    passed = sum(results)
    total  = len(results)
    colour = GRN if passed == total else (YEL if passed > 0 else RED)

    print(f"{CYN}{'─'*60}{RST}")
    print(f"  Result: {colour}{BLD}{passed}/{total} tests passed{RST}\n")

    # Cleanup temp folder
    shutil.rmtree("./test_tmp", ignore_errors=True)

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    run_all()
