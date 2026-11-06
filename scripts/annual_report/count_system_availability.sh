#!/bin/bash
set -euo pipefail
DATA_DIR="${HPC_DATA_DIR:-$HOME/hpc-meeting-nov2026}"

SYSTEM="${1:?Usage: bash count_system_availability.sh aire|calder}"
DIR="$DATA_DIR"

case "$SYSTEM" in
  aire)
    START="2026-01-01"
    ;;
  calder)
    START="2026-10-12"
    ;;
  *)
    echo "Choose aire or calder"
    exit 1
    ;;
esac

END="2026-11-04"
OUT="$DIR/${SYSTEM}_availability_raw.txt"

sreport -nP -t Seconds -T cpu \
  cluster Utilization \
  Start="$START" End="$END" \
  Format=Cluster,Allocated,Down,PlannedDown,Idle,Planned,Reported \
  > "$OUT"

python3 - "$OUT" "$START" "$END" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])

rows = [
    line.strip().split("|")
    for line in path.read_text().splitlines()
    if "|" in line
]

if len(rows) != 1 or len(rows[0]) != 7:
    raise SystemExit(
        f"Unexpected report output. Inspect {path}"
    )

cluster, allocated, down, planned_down, idle, planned, reported = rows[0]

down = float(down)
planned_down = float(planned_down)
reported = float(reported)

if reported <= 0:
    raise SystemExit("No reported capacity for this period")

availability = 100 * (1 - (down + planned_down) / reported)

print(f"\nSystem: {cluster}")
print(f"Period: {sys.argv[2]} to {sys.argv[3]} (exclusive)")
print(f"Down:         {down:,.0f} CPU-seconds")
print(f"Planned down: {planned_down:,.0f} CPU-seconds")
print(f"Reported:     {reported:,.0f} CPU-seconds")
print(f"\nSYSTEM AVAILABILITY: {availability:.2f}%")
PY
