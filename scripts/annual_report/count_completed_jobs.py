import csv
from pathlib import Path
from report_config import DATA_DIR

folder = DATA_DIR

START = "2026-01-01"
END = "2026-11-04"  # Exclusive

files = {
    "Aire": folder / "aire_completed.txt",
    "Calder": folder / "calder_completed.txt",
}

for system, path in files.items():
    jobids = set()
    grouped_arrays = 0

    with path.open() as f:
        for row in csv.DictReader(f, delimiter="|"):
            jobid = (row.get("JobID") or "").strip()
            submit = (row.get("Submit") or "").strip()
            end = (row.get("End") or "").strip()

            if not jobid or "." in jobid:
                continue

            # Only jobs submitted AND completed in our period.
            if not (START <= submit < END):
                continue
            if not (START <= end < END):
                continue

            if jobid not in jobids:
                jobids.add(jobid)
                if "_[" in jobid:
                    grouped_arrays += 1

    print(f"{system}: {len(jobids):,} completed jobs")
    print(f"  Grouped array records: {grouped_arrays:,}")
