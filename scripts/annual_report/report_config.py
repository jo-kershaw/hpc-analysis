"""Local paths for the annual HPC reporting scripts.

Set environment variables before running scripts on a different system.
No private datasets or account names are stored in this repository.
"""
import os
import sys
from pathlib import Path


def configured_path(variable, default):
    return Path(os.environ.get(variable, str(default))).expanduser()


DATA_DIR = configured_path("HPC_DATA_DIR", Path.home() / "hpc-meeting-nov2026")
HISTORICAL_AIRE = configured_path(
    "HPC_AIRE_HISTORICAL", DATA_DIR / "df_all_2025_2026.csv.gz"
)
FACULTY_CSV = configured_path(
    "HPC_FACULTY_CSV", DATA_DIR / "users_dep_fac_2026.csv"
)
EXCLUSIONS_FILE = configured_path(
    "HPC_EXCLUSIONS_FILE", DATA_DIR / "provisional_exclusions.txt"
)


def load_exclusions():
    """Return the optional, locally supplied list of accounts to exclude."""
    if not EXCLUSIONS_FILE.is_file():
        print(
            f"Note: no exclusion file at {EXCLUSIONS_FILE}; no accounts excluded",
            file=sys.stderr,
        )
        return set()
    return {
        line.strip().lower()
        for line in EXCLUSIONS_FILE.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
