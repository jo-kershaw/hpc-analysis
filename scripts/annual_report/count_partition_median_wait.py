#!/usr/bin/env python3
import csv
import gzip
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from report_config import DATA_DIR, HISTORICAL_AIRE

DATA = DATA_DIR
HIST = HISTORICAL_AIRE

YEAR = datetime(2026, 1, 1)
OCT = datetime(2026, 10, 1)
LAUNCH = datetime(2026, 10, 12)
END = datetime(2026, 11, 4)

waits = defaultdict(list)
seen = defaultdict(set)

def parse_time(value):
    try:
        return datetime.fromisoformat(value.strip())
    except (AttributeError, ValueError, TypeError):
        return None

def valid_jobid(value):
    jobid = (value or "").strip()
    if not jobid or "." in jobid or "_[" in jobid:
        return None
    return jobid

def record(group, jobid, partition, submitted, started):
    if not (submitted and started and YEAR <= submitted < END):
        return
    if not (submitted <= started < END):
        return
    if jobid in seen[group]:
        return

    seen[group].add(jobid)
    seconds = (started - submitted).total_seconds()
    waits[(group, partition or "UNKNOWN")].append(seconds)

# Historical Aire data, submitted January-September
print("Reading historical Aire jobs...", flush=True)

with gzip.open(HIST, "rt") as f:
    for row in csv.DictReader(f):
        jobid = valid_jobid(row.get("JobID"))
        if not jobid:
            continue
        if (row.get("IsStep") or "").strip().lower() in {"true", "1"}:
            continue

        submitted = parse_time(row.get("Submit"))
        if submitted and YEAR <= submitted < OCT:
            record(
                "Aire", jobid,
                (row.get("Partition") or "").strip(),
                submitted, parse_time(row.get("Start"))
            )

# Join submission and start information from newer extracts
def submission_lookup(filenames, earliest):
    lookup = {}
    for filename in filenames:
        with (DATA / filename).open() as f:
            for row in csv.DictReader(f, delimiter="|"):
                jobid = valid_jobid(row.get("JobID"))
                if not jobid:
                    continue
                submitted = parse_time(row.get("Submit"))
                if submitted and earliest <= submitted < END:
                    lookup[jobid] = (
                        submitted,
                        (row.get("Partition") or "").strip()
                    )
    return lookup

def read_starts(filename, lookup, system):
    with (DATA / filename).open() as f:
        for row in csv.DictReader(f, delimiter="|"):
            jobid = valid_jobid(row.get("JobID"))
            if not jobid or jobid not in lookup:
                continue

            submitted, submitted_partition = lookup[jobid]
            started = parse_time(row.get("Start"))
            if not started:
                continue

            partition = (
                (row.get("Partition") or "").strip()
                or submitted_partition
            )

            if system == "aire":
                record("Aire", jobid, partition, submitted, started)
            else:
                record("Calder YTD", jobid, partition, submitted, started)
                if submitted >= LAUNCH:
                    record("Calder since launch", jobid, partition,
                           submitted, started)

print("Processing Aire October-November...", flush=True)
aire_submits = submission_lookup(["aire_jobs.txt"], OCT)
read_starts("aire_cpu_hours.txt", aire_submits, "aire")
del aire_submits

print("Processing Calder...", flush=True)
calder_submits = submission_lookup(
    ["calder_pre_oct.txt", "calder_jobs.txt"], YEAR
)
read_starts("calder_cpu_hours.txt", calder_submits, "calder")
del calder_submits

print("\nMEDIAN QUEUE WAIT BY PARTITION")
print("1 January - 3 November 2026")

for group in ("Aire", "Calder YTD", "Calder since launch"):
    print(f"\n{group}")
    print(f"{'Partition':<25} {'Jobs':>12} {'Median min':>12} {'Median h':>12}")

    for (system_name, partition), values in sorted(waits.items()):
        if system_name != group:
            continue

        values.sort()
        n = len(values)
        middle = (values[(n-1)//2] + values[n//2]) / 2

        print(
            f"{partition:<25} {n:>12,} "
            f"{middle/60:>12,.1f} {middle/3600:>12,.2f}"
        )

print("\nDefinition: Start minus Submit.")
print("Jobs must have been submitted and started by 3 November.")
print("Pending jobs, job steps and grouped array records excluded.")
print("All job outcomes and teaching partitions included.")

# Overall median across all partitions, without averaging medians.
# The partition lists were sorted in the reporting loop above.
from heapq import merge


from bisect import bisect_right

print("\nOVERALL MEDIAN QUEUE WAIT BY SYSTEM")
print(f"{'System':<25} {'Jobs':>12} {'Median (s)':>14}  {'Readable time':<23} {'Zero wait %':>12}")

for group in ("Aire", "Calder since launch", "Calder YTD"):
    groups = [
        values for (system, partition), values in waits.items()
        if system == group
    ]

    n = sum(len(values) for values in groups)
    if n == 0:
        continue

    left_index = (n - 1) // 2
    right_index = n // 2
    left = right = None

    for i, value in enumerate(merge(*groups)):
        if i == left_index:
            left = value
        if i == right_index:
            right = value
            break

    median_seconds = (left + right) / 2

    hours = int(median_seconds // 3600)
    minutes = int((median_seconds % 3600) // 60)
    seconds = median_seconds % 60

    if hours:
        readable = f"{hours} h {minutes} min {seconds:.3f} s"
    elif minutes:
        readable = f"{minutes} min {seconds:.3f} s"
    else:
        readable = f"{seconds:.3f} s"

    zero_count = sum(bisect_right(v, 0) for v in groups)
    zero_pct = 100 * zero_count / n

    print(
        f"{group:<25} {n:>12,} "
        f"{median_seconds:>14.3f}  "
        f"{readable:<23} {zero_pct:>11.1f}%"
    )
