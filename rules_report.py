import csv
from collections import Counter

from rules import classify_by_rules

with open("mailbox_export.csv", newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

counts = Counter()
needs_ai = []

for r in rows:
    labels = r["labels"].split("|")
    cat = classify_by_rules(r["domain"], labels, r["has_unsubscribe"] == "True")
    counts[cat or "NEEDS_AI"] += 1
    if cat is None:
        needs_ai.append(r)

print(f"Total emails: {len(rows)}\n")
for category, n in counts.most_common():
    print(f"  {category}: {n} ({round(100 * n / len(rows))}%)")

print("\nTop domains that still need the AI:")
for domain, n in Counter(r["domain"] for r in needs_ai).most_common(20):
    print(f"  {domain}: {n}")