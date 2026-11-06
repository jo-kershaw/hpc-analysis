# Annual HPC analysis scripts

Reproducible reporting of Slurm jobs, users, allocated resource-hours,
queue wait, compute-node availability, and user faculties for Aire and Calder.
This folder contains **code only**, with no datasets or identifiable outputs.

## Inputs and local configuration

These scripts expect locally exported Slurm accounting files and, for faculty
reports, a local university user-to-faculty mapping. Data is **not included**.
All paths are configured by environment variables; see `report_config.py`.

| Variable | Purpose | Default |
| --- | --- | --- |
| `HPC_DATA_DIR` | Accounting extract and output directory | `~/hpc-meeting-nov2026` |
| `HPC_AIRE_HISTORICAL` | Compressed historical Aire CSV | `$HPC_DATA_DIR/df_all_2025_2026.csv.gz` |
| `HPC_FACULTY_CSV` | User/faculty mapping CSV | `$HPC_DATA_DIR/users_dep_fac_2026.csv` |
| `HPC_EXCLUSIONS_FILE` | Optional private list of excluded Slurm accounts, one per line | `$HPC_DATA_DIR/provisional_exclusions.txt` |

Example on a system where the data is stored elsewhere:

```bash
export HPC_DATA_DIR="$HOME/my-private-hpc-data"
export HPC_AIRE_HISTORICAL="/path/to/df_all_2025_2026.csv.gz"
export HPC_FACULTY_CSV="/path/to/users_dep_fac_2026.csv"
python3 scripts/annual_report/count_active_users.py
```

A missing exclusion file produces a warning and **no exclusions**, so totals
may differ from an internal adjusted report. The exclusion list should never
be committed or published. An optional filename argument to
`count_active_users_by_faculty.py` overrides `HPC_FACULTY_CSV`.

The two shell extraction/report scripts respect `HPC_DATA_DIR` as well.
Some scripts call `sacct`, `sreport` or `sinfo` and must run on the
corresponding Slurm cluster. Others read previously exported files.

## 2026 reporting snapshot and definitions

- Reporting window: **1 January through 3 November 2026**, inclusive;
  the end timestamp is 4 November 2026 00:00:00 (exclusive).
- Operational Calder capacity and wait summaries use **12 October through
  3 November 2026**. Other Calder totals may include earlier testing.
- Submitted jobs are distinct Slurm accounting records; compressed array
  ranges are not expanded. Job steps are excluded where applicable.
- Active users submitted at least one job. Users of both systems are counted
  once in the combined total. Staff/test account exclusions are provisional.
- CPU core-hours include CPU cores supporting GPU jobs; CPU-only capacity
  percentages exclude GPU-partition allocations.
- GPU device-hours are allocated devices multiplied by time, not measured
  GPU processing activity.
- Queue wait is Start minus Submit for jobs which started within the window.
  Jobs still pending are excluded from the median.
- Availability is derived from Slurm Down, PlannedDown and Reported CPU-time;
  it does not independently measure storage, login or network services.
- Faculty data uses the available user metadata; users not mapped to a faculty
  are retained in an unclassified group.
- Percentages based on installed hardware do not adjust for maintenance or
  reduced availability unless a particular script explicitly says so.

**Before another annual report:** review script-specific periods, partition
names and hardware assumptions; not all reporting dates are configurable yet.

## Privacy and reproducibility

Never add raw Slurm exports, account lists, identifiable data, notebook
outputs, or local configuration with sensitive information to this repository.
`.gitignore` provides a precaution, but review `git diff --cached` before push.
