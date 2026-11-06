#!/usr/bin/env python3
"""2026 active HPC job submitters by Leeds faculty (legacy 7 and current 5).

Run on Aire: python3 count_active_users_by_faculty.py [path/to/users_dep_fac_2026.csv]
Only usernames with at least one Slurm job submitted in the reporting window count.
"""
import csv
import gzip
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from report_config import DATA_DIR, FACULTY_CSV, HISTORICAL_AIRE, load_exclusions

HOME = Path.home()
OUT = DATA_DIR
USER_MAP = (Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else
            FACULTY_CSV)
START = "2026-01-01"
END = "2026-11-04"          # Exclusive: through 3 November
HIST = HISTORICAL_AIRE

SOURCES = [
    ("Aire", HIST, ","),
    ("Aire", OUT / "aire_jobs.txt", "|"),
    ("Calder", OUT / "calder_pre_oct.txt", "|"),
    ("Calder", OUT / "calder_jobs.txt", "|"),
]

# Same provisional administrative/test exclusions as count_active_users.py.
EXCLUDE = load_exclusions()

OLD = [
    "Engineering and Physical Sciences", "Environment", "Medicine and Health",
    "Biological Sciences", "Arts, Humanities and Cultures", "Business",
    "Social Sciences",
]
NEW = [
    "Engineering and Physical Sciences", "Environment and Social Sciences",
    "Health and Life Sciences", "Arts, Humanities and Cultures", "Business",
]

# Associate a legacy faculty with the corresponding 2026 merged faculty.
TO_NEW = {
    "Engineering and Physical Sciences": "Engineering and Physical Sciences",
    "Environment": "Environment and Social Sciences",
    "Social Sciences": "Environment and Social Sciences",
    "Medicine and Health": "Health and Life Sciences",
    "Biological Sciences": "Health and Life Sciences",
    "Arts, Humanities and Cultures": "Arts, Humanities and Cultures",
    "Business": "Business",
}


def norm(text):
    text = (text or "").casefold().replace("&", "and")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"^faculty (of )?", "", text).strip()
    return " ".join(text.split())

ALIASES = {norm(name): name for name in OLD + NEW}
ALIASES.update({
    "engineering physical sciences": "Engineering and Physical Sciences",
    "arts humanities cultures": "Arts, Humanities and Cultures",
    "medicine health": "Medicine and Health",
    "leeds university business school": "Business",
    "university business school": "Business",
    "lubs": "Business",
    "business school": "Business",
    "education soc sciences and law": "Social Sciences",
})


def faculty_name(raw):
    return ALIASES.get(norm(raw))

def active_submitters():
    systems = {"Aire": set(), "Calder": set()}
    for system, path, delimiter in SOURCES:
        if not path.exists():
            raise SystemExit(f"Missing job data: {path}")
        open_file = gzip.open if path.suffix == ".gz" else open
        with open_file(path, "rt", encoding="utf-8") as handle:
            reader = csv.DictReader(handle, delimiter=delimiter)
            for row in reader:
                jobid = (row.get("JobID") or "").strip()
                if not jobid or "." in jobid:
                    continue
                if (row.get("IsStep") or "").strip().lower() in {"true", "1"}:
                    continue
                submit = (row.get("Submit") or "").strip()
                user = (row.get("User") or "").strip().lower()
                if START <= submit < END and user and user != "unknown":
                    systems[system].add(user)
        print(f"Read {system}: {path.name}", flush=True)
    return systems


def read_faculty_map(path):
    if not path.exists():
        raise SystemExit(f"Metadata file not found: {path}\n"
                         "Pass its actual path as an argument if different.")
    records = defaultdict(list)
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        columns = {c.strip().lower(): c for c in (reader.fieldnames or [])}
        username_col = columns.get("u_ad_sam_account")
        faculty_col = columns.get("u_faculty") or columns.get("faculty")
        dept_col = columns.get("department")
        if not username_col or not faculty_col:
            raise SystemExit(f"Expected u_ad_sam_account and u_faculty columns; got {reader.fieldnames}")
        for row in reader:
            username = (row.get(username_col) or "").strip().lower()
            if username:
                records[username].append(((row.get(faculty_col) or "").strip(),
                                          (row.get(dept_col) or "").strip() if dept_col else ""))
    return records

def write_csv(path, header, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    systems = active_submitters()
    all_active = systems["Aire"] | systems["Calder"]
    excluded = all_active & EXCLUDE
    included = all_active - excluded
    metadata = read_faculty_map(USER_MAP)
    old_count, new_count = Counter(), Counter()
    problems = []
    raw_faculties = Counter()
    old_unresolved, new_unresolved = 0, 0

    for user in sorted(included):
        rows = metadata.get(user, [])
        raw = sorted({faculty for faculty, _ in rows if faculty})
        departments = sorted({dept for _, dept in rows if dept})
        for value in raw:
            raw_faculties[value] += 1
        canonical = {faculty_name(value) for value in raw}
        canonical.discard(None)
        legacy = {name for name in canonical if name in OLD}
        current = {TO_NEW[name] for name in legacy}
        current.update(name for name in canonical if name in NEW)
        # A user must map to exactly one current faculty.
        new_fac = next(iter(current)) if len(current) == 1 else None
        # A user must map to a unique legacy faculty; never split a new merged label.
        old_fac = next(iter(legacy)) if len(legacy) == 1 and new_fac else None
        if len(legacy) > 1 or len(current) > 1:
            old_fac = new_fac = None
        if old_fac:
            old_count[old_fac] += 1
        else:
            old_unresolved += 1
        if new_fac:
            new_count[new_fac] += 1
        else:
            new_unresolved += 1
        if not old_fac or not new_fac:
            if not rows:
                reason = "User absent from 2026 metadata"
            elif len(current) > 1 or len(legacy) > 1:
                reason = "Conflicting faculty assignments"
            elif new_fac and not old_fac:
                reason = "Only merged/new faculty; legacy category unknown"
            else:
                reason = "Faculty label missing or unrecognised"
            problems.append([user, "; ".join(raw), "; ".join(departments),
                             reason, "yes" if user in systems["Aire"] else "no",
                             "yes" if user in systems["Calder"] else "no"])

    print("\nACTIVE HPC USERS BY FACULTY, 1 Jan - 3 Nov 2026")
    print(f"Metadata source: {USER_MAP}")
    print(f"Aire: {len(systems['Aire']):,}; Calder: {len(systems['Calder']):,}; "
          f"both: {len(systems['Aire'] & systems['Calder']):,}")
    print(f"Combined raw unique users: {len(all_active):,}")
    print(f"Excluded provisional admin/test accounts: {len(excluded):,}")
    print(f"Active usernames in scope: {len(included):,}\n")

    print("SEVEN LEGACY FACULTIES (as requested)")
    for name in OLD:
        print(f"  {name:<38} {old_count[name]:>5,}")
    print(f"  {'Total assigned to a legacy faculty':<38} {sum(old_count.values()):>5,}")
    print(f"  {'Unresolved / not in seven faculties':<38} {old_unresolved:>5,}")
    print(f"  {'TOTAL ACTIVE (including unresolved)':<38} {len(included):>5,}")

    print("\nFIVE CURRENT FACULTIES (September 2026 structure)")
    for name in NEW:
        print(f"  {name:<38} {new_count[name]:>5,}")
    print(f"  {'Total assigned to a current faculty':<38} {sum(new_count.values()):>5,}")
    print(f"  {'Unresolved / not in five faculties':<38} {new_unresolved:>5,}")
    print(f"  {'TOTAL ACTIVE (including unresolved)':<38} {len(included):>5,}")

    write_csv(OUT / "active_users_faculty_legacy7.csv",
              ["Faculty", "Active users"],
              [[n, old_count[n]] for n in OLD] +
              [["Total assigned", sum(old_count.values())],
               ["Unresolved / other", old_unresolved], ["Total active", len(included)]])
    write_csv(OUT / "active_users_faculty_current5.csv",
              ["Faculty", "Active users"],
              [[n, new_count[n]] for n in NEW] +
              [["Total assigned", sum(new_count.values())],
               ["Unresolved / other", new_unresolved], ["Total active", len(included)]])
    write_csv(OUT / "active_users_faculty_review.csv",
              ["Username", "Metadata faculty", "Department", "Issue", "Aire", "Calder"],
              problems)
    print(f"\nReview file (possibly identifiable): {OUT / 'active_users_faculty_review.csv'}")
    print("Distinct faculty labels found in metadata for active users:")
    for name, count in sorted(raw_faculties.items()):
        print(f"  {name}: {count}")
    print("\nDo not silently distribute users labelled only with a new merged faculty "
          "between the two predecessor faculties.")


if __name__ == "__main__":
    main()
