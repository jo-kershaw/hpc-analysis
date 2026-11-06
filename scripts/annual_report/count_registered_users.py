import csv
from collections import defaultdict
from pathlib import Path
from report_config import DATA_DIR

path = DATA_DIR / 'registered_associations.txt'

users = defaultdict(set)

with path.open() as f:
    for cluster, user, account in csv.reader(f, delimiter="|"):
        user = user.strip().lower()
        if user and user != "root":
            users[cluster].add(user)

for cluster, names in sorted(users.items()):
    print(f"{cluster}: {len(names):,} distinct registered usernames")

print("Combined distinct usernames:",
      len(set().union(*users.values())))
