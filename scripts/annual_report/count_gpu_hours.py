import csv
import gzip
from datetime import datetime, timedelta
from pathlib import Path
from report_config import DATA_DIR, HISTORICAL_AIRE

folder = DATA_DIR

YEAR_START = datetime(2026, 1, 1)
OCT_START = datetime(2026, 10, 1)
REPORT_END = datetime(2026, 11, 4)

sources = [
    (
        "Aire Jan-Sep",
        HISTORICAL_AIRE,
        YEAR_START, OCT_START,
    ),
    (
        "Aire Oct-Nov",
        folder / "aire_gpu_hours.txt",
        OCT_START, REPORT_END,
    ),
    (
        "Calder",
        folder / "calder_gpu_hours.txt",
        YEAR_START, REPORT_END,
    ),
]

def parse_time(value):
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None

def count_gpus(tres):
    resources = {}

    for item in str(tres or "").split(","):
        if "=" not in item:
            continue

        key, value = item.split("=", 1)
        try:
            resources[key.strip()] = int(value)
        except ValueError:
            continue

    # Prefer the generic total, avoiding double-counting
    # when Slurm also reports GPUs by type.
    if "gres/gpu" in resources:
        return resources["gres/gpu"]

    return sum(
        value for key, value in resources.items()
        if key.startswith("gres/gpu:")
    )

totals = {}

for label, path, window_start, window_end in sources:

    if not path.exists():
        raise FileNotFoundError(path)

    opener = gzip.open if path.suffix == ".gz" else open
    separator = "," if path.suffix == ".gz" else "|"

    gpu_hours = 0.0
    jobs_counted = 0
    grouped_arrays = 0

    with opener(path, "rt") as f:
        for job in csv.DictReader(f, delimiter=separator):

            jobid = str(job.get("JobID", "")).strip()

            if not jobid or "." in jobid:
                continue

            if str(job.get("IsStep", "")).strip().lower() in ("true", "1"):
                continue

            gpus = count_gpus(job.get("AllocTRES", ""))

            if gpus <= 0:
                continue

            start = parse_time(job.get("Start"))
            finish = parse_time(job.get("End"))

            if start is None:
                continue

            if finish is None:
                try:
                    finish = start + timedelta(
                        seconds=int(float(job.get("ElapsedRaw") or 0))
                    )
                except (ValueError, TypeError):
                    continue

            seconds = max(
                0,
                (min(finish, window_end)
                 - max(start, window_start)).total_seconds()
            )

            if seconds <= 0:
                continue

            gpu_hours += gpus * seconds / 3600
            jobs_counted += 1

            if "_[" in jobid:
                grouped_arrays += 1

    totals[label] = gpu_hours

    print(f"\n{label}")
    print(f"  Jobs with GPU allocations: {jobs_counted:,}")
    print(f"  Allocated GPU-hours:       {gpu_hours:,.1f}")
    print(f"  Grouped array records:     {grouped_arrays:,}")

aire = totals["Aire Jan-Sep"] + totals["Aire Oct-Nov"]
calder = totals["Calder"]

print("\n2026 ALLOCATED GPU-HOURS")
print("1 January – 3 November 2026")
print(f"Aire:      {aire:,.1f}")
print(f"Calder:    {calder:,.1f}")
print(f"COMBINED:  {aire + calder:,.1f}")
print(f"Thousands: {(aire + calder) / 1000:,.1f} thousand")
