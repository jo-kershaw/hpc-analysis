#!/usr/bin/env python3
"""Count unique Slurm job accounting records submitted in 2026 YTD."""
import csv
import gzip
from collections import Counter
from pathlib import Path
from report_config import DATA_DIR, HISTORICAL_AIRE

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

jobs = {"Aire": set(), "Calder": set()}
monthly = Counter()
duplicates = Counter()
grouped_arrays = Counter()

for system, path, delimiter in SOURCES:
    if not path.is_file():
        raise FileNotFoundError(f"Missing input file: {path}")
    opener = gzip.open if path.suffix == ".gz" else open
    added = 0
    with opener(path, "rt", encoding="utf-8") as handle:
        for row in csv.DictReader(handle, delimiter=delimiter):
            jobid = (row.get("JobID") or "").strip()
            if not jobid or "." in jobid:
                continue  # Exclude .batch, .extern and other steps
            if (row.get("IsStep") or "").strip().lower() in {"true", "1"}:
                continue
            submitted = (row.get("Submit") or "").strip()
            if not (START <= submitted < END):
                continue
            if jobid in jobs[system]:
                duplicates[system] += 1
                continue
            jobs[system].add(jobid)
            monthly[system, submitted[:7]] += 1
            added += 1
            if "_[" in jobid:
                grouped_arrays[system] += 1
    print(f"{system}: {path.name}: {added:,} distinct job records")

print(f"\nJOB SUBMISSIONS: {START} to 2026-11-03 (inclusive)")
print(f"Aire:       {len(jobs['Aire']):,}")
print(f"Calder:     {len(jobs['Calder']):,}")
print(f"Combined:   {len(jobs['Aire']) + len(jobs['Calder']):,}")

print("\nMonthly counts:")
for (system, month), n in sorted(monthly.items()):
    print(f"  {system:7} {month}: {n:,}")
print("\nDuplicate records excluded:", dict(duplicates))
print("Grouped array records (not expanded):", dict(grouped_arrays))
print("Note: a compressed array range is counted as one record, not one per task.")
