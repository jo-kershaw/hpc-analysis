import csv
import gzip
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from report_config import DATA_DIR, HISTORICAL_AIRE

home = Path.home()
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
        folder / "aire_cpu_hours.txt",
        OCT_START, REPORT_END,
    ),
    (
        "Calder",
        folder / "calder_cpu_hours.txt",
        YEAR_START, REPORT_END,
    ),
]

GPU_PARTITIONS = {
    "gpu",
    "aire-gpu-lovelace",
    "calder-gpu-hopper",
    "gpu_lovelace",
    "gpu_hopper",
}

def parse_time(value):
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None

totals = defaultdict(lambda: defaultdict(float))
partitions_seen = set()

for label, path, window_start, window_end in sources:

    if not path.exists():
        raise FileNotFoundError(path)

    opener = gzip.open if path.suffix == ".gz" else open
    separator = "," if path.suffix == ".gz" else "|"

    cpu_only_hours = 0.0
    gpu_job_cpu_hours = 0.0
    counted = 0

    with opener(path, "rt") as f:
        for job in csv.DictReader(f, delimiter=separator):

            jobid = str(job.get("JobID", "")).strip()

            # Exclude Slurm job steps
            if not jobid or "." in jobid:
                continue

            if str(job.get("IsStep", "")).strip().lower() in ("true", "1"):
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

            try:
                cpus = int(float(job.get("AllocCPUS") or 0))
            except (ValueError, TypeError):
                continue

            if cpus <= 0:
                continue

            seconds = max(
                0,
                (min(finish, window_end) -
                 max(start, window_start)).total_seconds()
            )

            if seconds <= 0:
                continue

            hours = cpus * seconds / 3600
            partition = str(job.get("Partition", "")).strip()
            partitions_seen.add(partition)

            if partition in GPU_PARTITIONS:
                gpu_job_cpu_hours += hours
            else:
                cpu_only_hours += hours

            counted += 1

    totals[label]["cpu_only"] = cpu_only_hours
    totals[label]["gpu_support"] = gpu_job_cpu_hours

    print(f"\n{label}")
    print(f"  Jobs counted:          {counted:,}")
    print(f"  CPU-only core-hours:   {cpu_only_hours:,.1f}")
    print(f"  GPU-job CPU core-hours:{gpu_job_cpu_hours:,.1f}")
    print(f"  Total CPU core-hours:  {cpu_only_hours + gpu_job_cpu_hours:,.1f}")

aire_cpu = (
    totals["Aire Jan-Sep"]["cpu_only"]
    + totals["Aire Oct-Nov"]["cpu_only"]
)
aire_gpu_support = (
    totals["Aire Jan-Sep"]["gpu_support"]
    + totals["Aire Oct-Nov"]["gpu_support"]
)

calder_cpu = totals["Calder"]["cpu_only"]
calder_gpu_support = totals["Calder"]["gpu_support"]

print("\n2026 CPU CORE-HOURS: 1 JANUARY TO 3 NOVEMBER")
print(f"{'':28} {'Aire':>15} {'Calder':>15} {'Combined':>15}")
print(
    f"{'CPU-only partitions':28}"
    f" {aire_cpu:15,.1f} {calder_cpu:15,.1f}"
    f" {aire_cpu + calder_cpu:15,.1f}"
)
print(
    f"{'CPUs supporting GPU jobs':28}"
    f" {aire_gpu_support:15,.1f} {calder_gpu_support:15,.1f}"
    f" {aire_gpu_support + calder_gpu_support:15,.1f}"
)

grand_total = (
    aire_cpu + calder_cpu
    + aire_gpu_support + calder_gpu_support
)

print(f"\nTOTAL CPU CORE-HOURS: {grand_total:,.1f}")
print("Expected previous total: 65,341,498.5")

print("\nPartitions found:")
for partition in sorted(partitions_seen):
    print(" ", partition)
