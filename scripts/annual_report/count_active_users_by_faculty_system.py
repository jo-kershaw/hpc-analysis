#!/usr/bin/env python3
"""2026 active users by legacy faculty, split by Aire and Calder.

Run alongside count_active_users_by_faculty.py on Aire.
Combined column counts each person once, even if active on both clusters.
"""
import csv
from collections import Counter
from pathlib import Path
import count_active_users_by_faculty as base

# Preserve the correction made during the 2026 Finance analysis.
base.ALIASES["education soc sciences and law"] = "Social Sciences"

systems = base.active_submitters()
# Match the provisional, adjusted active-user population used by Finance.
systems = {name: names - base.EXCLUDE for name, names in systems.items()}
all_users = systems["Aire"] | systems["Calder"]
metadata = base.read_faculty_map(base.USER_MAP)
counts = {name: Counter() for name in ("Aire", "Calder", "Combined")}
overlap = Counter()

for user in all_users:
    raw_labels = {faculty for faculty, _ in metadata.get(user, []) if faculty}
    recognised = {base.faculty_name(label) for label in raw_labels}
    recognised.discard(None)
    legacy = {name for name in recognised if name in base.OLD}
    current = {base.TO_NEW[name] for name in legacy}
    current.update(name for name in recognised if name in base.NEW)
    faculty = (next(iter(legacy)) if len(legacy) == 1 and len(current) == 1
               else "Unresolved / other")

    on_aire = user in systems["Aire"]
    on_calder = user in systems["Calder"]
    if on_aire:
        counts["Aire"][faculty] += 1
    if on_calder:
        counts["Calder"][faculty] += 1
    if on_aire and on_calder:
        overlap[faculty] += 1
    counts["Combined"][faculty] += 1

faculties = base.OLD + ["Unresolved / other"]
print("\nACTIVE HPC USERS BY FACULTY AND SYSTEM")
print("1 January - 3 November 2026; 13 provisional admin/test accounts excluded")
print(f"{'Faculty':<39} {'Aire':>7} {'Calder':>8} {'Unique total':>13}")
rows = []
for faculty in faculties:
    a, c, u = (counts[k][faculty] for k in ("Aire", "Calder", "Combined"))
    assert u == a + c - overlap[faculty]
    rows.append([faculty, a, c, u])
    print(f"{faculty:<39} {a:>7,} {c:>8,} {u:>13,}")

totals = [len(systems["Aire"]), len(systems["Calder"]), len(all_users)]
rows.append(["TOTAL", *totals])
print(f"{'TOTAL':<39} {totals[0]:>7,} {totals[1]:>8,} {totals[2]:>13,}")
print(f"Users active on both systems: {len(systems['Aire'] & systems['Calder']):,}")
print("Combined total = Aire + Calder - users active on both (per faculty).")

output = base.OUT / "active_users_faculty_by_system.csv"
with output.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Faculty", "Aire", "Calder", "Combined unique"])
    writer.writerows(rows)
print(f"CSV saved: {output}")
