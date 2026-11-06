import csv
from datetime import datetime, timedelta
from pathlib import Path
from report_config import DATA_DIR

folder = DATA_DIR

def date(s):
    return datetime.fromisoformat(s)

windows = {
    "Before 12 October": (date("2026-01-01"), date("2026-10-12")),
    "First launch week": (date("2026-10-12"), date("2026-10-19")),
    "Since 12 October": (date("2026-10-12"), date("2026-11-04")),
    "Whole reporting period": (date("2026-01-01"), date("2026-11-04")),
}

def parse_date(value):
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None

def gpu_count(tres):
    resources = {}

    for item in (tres or "").split(","):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        try:
            resources[key.strip()] = int(value)
        except ValueError:
            pass

    if "gres/gpu" in resources:
        return resources["gres/gpu"]

    return sum(
        value for key, value in resources.items()
        if key.startswith("gres/gpu:")
    )

def overlap_hours(row, window_start, window_end):
    start = parse_date(row.get("Start"))
    end = parse_date(row.get("End"))

    if start is None:
        return 0.0

    if end is None:
        try:
            elapsed = float(row.get("ElapsedRaw") or 0)
            end = start + timedelta(seconds=elapsed)
        except ValueError:
            return 0.0

    seconds = max(
        0,
        (min(end, window_end) -
         max(start, window_start)).total_seconds()
    )

    return seconds / 3600

def calculate(filename, resource):
    totals = {name: 0.0 for name in windows}

    with (folder / filename).open() as f:
        for row in csv.DictReader(f, delimiter="|"):
            jobid = (row.get("JobID") or "").strip()

            if not jobid or "." in jobid:
                continue

            if resource == "cpu":
                try:
                    allocated = int(row.get("AllocCPUS") or 0)
                except ValueError:
                    continue
            else:
                allocated = gpu_count(row.get("AllocTRES"))

            if allocated <= 0:
                continue

            for name, (start, end) in windows.items():
                totals[name] += allocated * overlap_hours(
                    row, start, end
                )

    return totals

cpu = calculate("calder_cpu_hours.txt", "cpu")
gpu = calculate("calder_gpu_hours.txt", "gpu")

print("\nCALDER ALLOCATED RESOURCE-HOURS")
print(f"{'Period':<25} {'CPU core-hours':>18} {'GPU device-hours':>18}")

for name in windows:
    print(f"{name:<25} {cpu[name]:>18,.1f} {gpu[name]:>18,.1f}")

# Published hardware capacity, including CPUs on GPU nodes.
CPU_CORES = 96 * 128 + 7 * 128
GPU_DEVICES = 56

start, end = windows["Since 12 October"]
hours = (end - start).total_seconds() / 3600

cpu_pct = 100 * cpu["Since 12 October"] / (CPU_CORES * hours)
gpu_pct = 100 * gpu["Since 12 October"] / (GPU_DEVICES * hours)

print("\nPROVISIONAL MEAN CAPACITY ALLOCATED")
print("12 October - 3 November 2026")
print(f"CPU: {cpu_pct:.1f}%")
print(f"GPU: {gpu_pct:.1f}%")

if cpu_pct > 100 or gpu_pct > 100:
    print("\nWARNING: Allocation exceeds theoretical capacity.")
    print("Investigate accounting records before reporting percentages.")
