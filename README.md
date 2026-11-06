# HPC Analysis

Python and shell scripts for analysing Slurm HPC usage,
resource allocation, queueing, system availability and
user activity.

Developed using the Aire and Calder HPC systems at the
University of Leeds.

## Contents

- `scripts/annual_report/` — Scripts for annual HPC
  statistics and reporting.

See the README in each subdirectory for usage instructions,
data requirements and methodological assumptions.

## Data and privacy

This repository contains analysis code, not HPC accounting
datasets or identifiable user information.

Raw Slurm records, user-to-faculty mappings and administrative
account exclusion lists are deliberately excluded.

Users must supply their own data and configure local paths.

## Reproducibility

The reporting scripts were developed using a 2026 reporting
snapshot. Reporting dates, partitions and hardware assumptions
should be reviewed before reuse.

## Dependencies

Most Python scripts use the Python standard library.
Slurm extraction scripts require access to the relevant
Slurm commands and accounting database.
