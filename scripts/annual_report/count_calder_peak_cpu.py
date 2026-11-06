import csv
import subprocess
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from report_config import DATA_DIR

DATA = DATA_DIR / 'calder_cpu_hours.txt'

START = datetime(2026, 10, 12)
END = datetime(2026, 11, 4)  # Exclusive
FIRST_WEEK_END = datetime(2026, 10, 19)

PARTITION = "calder-cpu-turin"

def parse_time(value):
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None

# Get current installed CPU capacity from Slurm.
result = subprocess.run(
    ["sinfo", "-N", "-h", "-p", PARTITION, "-o", "%N|%c"],
    capture_output=True,
    text=True,
    check=True
)

nodes = {}

for line in result.stdout.splitlines():
    name, cpus = line.split("|")
    nodes[name] = int(cpus)

capacity = sum(nodes.values())

if capacity == 0:
    raise SystemExit("No CPU nodes found in Slurm")

# Build a timeline of CPU allocations.
# Positive events = allocation begins.
# Negative events = allocation ends.
events = defaultdict(int)
jobs = 0

with DATA.open() as f:
    for row in csv.DictReader(f, delimiter="|"):

        jobid = (row.get("JobID") or "").strip()
        partition = (row.get("Partition") or "").strip()

        if not jobid or "." in jobid:
            continue

        if partition != PARTITION:
            continue

        try:
            cpus = int(float(row.get("AllocCPUS") or 0))
        except ValueError:
            continue

        if cpus <= 0:
            continue

        start = parse_time(row.get("Start"))
        end = parse_time(row.get("End"))

        if start is None:
            continue

        if end is None:
            try:
                end = start + timedelta(
                    seconds=float(row.get("ElapsedRaw") or 0)
                )
            except ValueError:
                continue

        # Clip to the monitoring window.
        start = max(start, START)
        end = min(end, END)

        if end <= start:
            continue

        t0 = int((start - START).total_seconds())
        t1 = int((end - START).total_seconds())

        events[t0] += cpus
        events[t1] -= cpus
        jobs += 1

# Sweep through all allocation changes.
# Combining changes at the same second avoids false peaks.
current = 0
peak = 0
peak_time = None

first_week_peak = 0
first_week_time = None

first_week_seconds = int(
    (FIRST_WEEK_END - START).total_seconds()
)

for second in sorted(events):
    current += events[second]

    if current > peak:
        peak = current
        peak_time = START + timedelta(seconds=second)

    if second < first_week_seconds and current > first_week_peak:
        first_week_peak = current
        first_week_time = START + timedelta(seconds=second)

print("\nCALDER PEAK CPU ALLOCATION")
print("Monitoring window: 12 October - 3 November 2026")
print(f"Start: {START}")
print(f"End (exclusive): {END}")

print(f"\nPartition: {PARTITION}")
print(f"Configured CPU nodes: {len(nodes):,}")
print(f"Configured CPU cores: {capacity:,}")
print(f"Jobs analysed: {jobs:,}")

print(f"\nPeak allocated CPU cores: {peak:,}")
print(f"Peak timestamp: {peak_time}")
print(f"PEAK CPU ALLOCATION: {100 * peak / capacity:.2f}%")

print("\nFIRST-WEEK CROSS-CHECK")
print(f"Peak allocated cores: {first_week_peak:,}")
print(f"Peak timestamp: {first_week_time}")
print(f"Peak allocation: {100 * first_week_peak / capacity:.2f}%")

if peak > capacity:
    print("\nWARNING: Peak exceeds configured capacity.")
    print("Check historical node counts and accounting records.")

if current != 0:
    print("\nWARNING: Allocation timeline did not return to zero.")
