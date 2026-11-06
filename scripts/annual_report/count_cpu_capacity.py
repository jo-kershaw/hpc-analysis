import csv
import gzip
from datetime import datetime, timedelta
from pathlib import Path
from report_config import DATA_DIR, HISTORICAL_AIRE

folder = DATA_DIR

def dt(s):
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None

YEAR = dt("2026-01-01")
OCT = dt("2026-10-01")
LAUNCH = dt("2026-10-12")
WEEK_END = dt("2026-10-19")
END = dt("2026-11-04")

sources = [
    ("Aire Jan-Sep",
     HISTORICAL_AIRE,
     YEAR, OCT),
    ("Aire Oct-Nov",
     folder / "aire_cpu_hours.txt",
     OCT, END),
    ("Calder",
     folder / "calder_cpu_hours.txt",
     YEAR, END),
]

totals = {}
calder_first_week = 0.0

for label, path, window_start, window_end in sources:
    opener = gzip.open if path.suffix == ".gz" else open
    delimiter = "," if path.suffix == ".gz" else "|"

    cpu_hours = 0.0
    counted = 0

    with opener(path, "rt") as f:
        for row in csv.DictReader(f, delimiter=delimiter):
            jobid = (row.get("JobID") or "").strip()
            partition = (row.get("Partition") or "").lower()

            if not jobid or "." in jobid:
                continue

            if str(row.get("IsStep", "")).lower() in ("true", "1"):
                continue

            # Exclude CPU allocations on GPU partitions.
            if "gpu" in partition:
                continue

            try:
                cpus = int(float(row.get("AllocCPUS") or 0))
            except ValueError:
                continue

            if cpus <= 0:
                continue

            start = dt(row.get("Start"))
            finish = dt(row.get("End"))

            if start is None:
                continue

            if finish is None:
                try:
                    finish = start + timedelta(
                        seconds=float(row.get("ElapsedRaw") or 0)
                    )
                except ValueError:
                    continue

            seconds = max(
                0,
                (min(finish, window_end)
                 - max(start, window_start)).total_seconds()
            )

            if seconds > 0:
                cpu_hours += cpus * seconds / 3600
                counted += 1

            if label == "Calder":
                first_week_seconds = max(
                    0,
                    (min(finish, WEEK_END)
                     - max(start, LAUNCH)).total_seconds()
                )
                calder_first_week += cpus * first_week_seconds / 3600

    totals[label] = cpu_hours
    print(f"{label}: {cpu_hours:,.1f} CPU-only core-hours")
    print(f"  Jobs counted: {counted:,}")

# Aire: entire reporting period
aire_hours = totals["Aire Jan-Sep"] + totals["Aire Oct-Nov"]
aire_cores = 9072
aire_period_hours = (END - YEAR).total_seconds() / 3600

# Calder: operational period from 12 October
calder_cores = 98 * 128
calder_period_hours = (END - LAUNCH).total_seconds() / 3600

# Calder's pre-launch allocations must not be in the numerator.
# Recalculate post-launch from the whole-period Calder total
# using the first-week and subsequent interval separately.
# The Calder source was processed above, so compute the
# post-launch total in a second pass.
calder_post_launch = 0.0

with (folder / "calder_cpu_hours.txt").open() as f:
    for row in csv.DictReader(f, delimiter="|"):
        jobid = (row.get("JobID") or "").strip()
        partition = (row.get("Partition") or "").lower()

        if not jobid or "." in jobid or "gpu" in partition:
            continue

        try:
            cpus = int(float(row.get("AllocCPUS") or 0))
        except ValueError:
            continue

        start = dt(row.get("Start"))
        finish = dt(row.get("End"))
        if start is None:
            continue
        if finish is None:
            try:
                finish = start + timedelta(
                    seconds=float(row.get("ElapsedRaw") or 0)
                )
            except ValueError:
                continue

        seconds = max(
            0,
            (min(finish, END) - max(start, LAUNCH)).total_seconds()
        )
        calder_post_launch += cpus * seconds / 3600

print("\nCALDER FIRST-WEEK CHECK")
print(f"CPU-only core-hours: {calder_first_week:,.1f}")
print("Previous calculation: 628,135.6")

print("\nMEAN CPU-ONLY CAPACITY ALLOCATED")
print("Aire:   1 Jan - 3 Nov 2026")
print(f"  Allocated: {aire_hours:,.1f} core-hours")
print(f"  Capacity:  {aire_cores:,} CPU cores")
print(f"  Mean:      {100 * aire_hours / (aire_cores * aire_period_hours):.1f}%")

print("Calder: 12 Oct - 3 Nov 2026")
print(f"  Allocated: {calder_post_launch:,.1f} core-hours")
print(f"  Capacity:  {calder_cores:,} CPU cores")
print(f"  Mean:      {100 * calder_post_launch / (calder_cores * calder_period_hours):.1f}%")
