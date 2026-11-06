#!/usr/bin/env python3
"""Count unique job submitters, including teaching, across Aire and Calder."""
import csv
import gzip
from pathlib import Path
from report_config import DATA_DIR, HISTORICAL_AIRE, load_exclusions

HOME = Path.home()
DATA = DATA_DIR
HISTORICAL = HISTORICAL_AIRE
START = "2026-01-01"
END = "2026-11-04"  # Exclusive: includes 3 November

SOURCES = [
    ("Aire", HISTORICAL, ","),
    ("Aire", DATA / "aire_jobs.txt", "|"),
    ("Calder", DATA / "calder_pre_oct.txt", "|"),
    ("Calder", DATA / "calder_jobs.txt", "|"),
]

# Working adjustment agreed for Finance: probable early test/system accounts.
# Not independently verified as duplicate people; review before other reporting.
PROVISIONAL_EXCLUSIONS = load_exclusions()

users = {"Aire": set(), "Calder": set()}

for system, path, delimiter in SOURCES:
    if not path.is_file():
        raise FileNotFoundError(f"Missing input file: {path}")
    opener = gzip.open if path.suffix == ".gz" else open
    file_users = set()
    with opener(path, "rt", encoding="utf-8") as handle:
        for row in csv.DictReader(handle, delimiter=delimiter):
            jobid = (row.get("JobID") or "").strip()
            if not jobid or "." in jobid:
                continue
            if (row.get("IsStep") or "").strip().lower() in {"true", "1"}:
                continue
            submitted = (row.get("Submit") or "").strip()
            username = (row.get("User") or "").strip().lower()
            if START <= submitted < END and username and username != "unknown":
                file_users.add(username)
    users[system].update(file_users)
    print(f"{system}: {path.name}: {len(file_users):,} unique submitters")

aire, calder = users["Aire"], users["Calder"]
combined = aire | calder
excluded_present = combined & PROVISIONAL_EXCLUSIONS

print(f"\nACTIVE USERS: {START} to 2026-11-03 (inclusive)")
print(f"Aire:                  {len(aire):,}")
print(f"Calder:                {len(calder):,}")
print(f"On both:               {len(aire & calder):,}")
print(f"Combined raw:          {len(combined):,}")
print(f"Provisional exclusions: {len(excluded_present):,}")
print(f"Adjusted working total: {len(combined - excluded_present):,}")
print("Note: this counts usernames; administrative exclusions are provisional.")
