#!/bin/bash
set -euo pipefail
DATA_DIR="${HPC_DATA_DIR:-$HOME/hpc-meeting-nov2026}"

SYSTEM="${1:?Usage: bash fetch_completed_jobs.sh aire|calder}"
OUT="$DATA_DIR/${SYSTEM}_completed.txt"
TEMP="${OUT}.tmp"

START="2026-01-01"
END="2026-11-04"   # Exclusive: includes 3 November
CHUNK_DAYS=7

echo "JobID|Submit|End" > "$TEMP"

while [[ "$START" < "$END" ]]; do
    NEXT=$(date -d "$START + $CHUNK_DAYS days" +%F)

    if [[ "$NEXT" > "$END" ]]; then
        NEXT="$END"
    fi

    echo "Fetching $SYSTEM: $START to $NEXT"

    sacct -a -X -nP \
        -S "${START}T00:00:00" \
        -E "${NEXT}T00:00:00" \
        --state=COMPLETED \
        --format=JobID,Submit,End \
        >> "$TEMP"

    START="$NEXT"
done

mv "$TEMP" "$OUT"
echo "Saved to $OUT"
wc -l "$OUT"
