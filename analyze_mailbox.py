import csv
from collections import Counter

rows = list(csv.DictReader(open("mailbox_export.csv", encoding="utf-8")))
print(f"Total emails: {len(rows)}\n")

# Gmail's own classification
cats = Counter()
for r in rows:
    for label in r["labels"].split("|"):
        if label.startswith("CATEGORY_"):
            cats[label] += 1
print("Gmail's own categories:")
for k, v in cats.most_common():
    print(f"  {k}: {v}")

# Top sending domains
domains = Counter(r["domain"] for r in rows)
unsub = Counter(r["domain"] for r in rows if r["has_unsubscribe"] == "True")
print("\nTop 30 sender domains (count, % with unsubscribe header):")
for d, n in domains.most_common(30):
    print(f"  {d}: {n}  ({round(100 * unsub[d] / n)}%)")

# Likely real people: no unsubscribe header, no automated-looking address,
# and no Gmail category label.
auto_words = ("noreply", "no-reply", "donotreply", "notification", "alert", "mailer")


def likely_human(r):
    return (
        r["has_unsubscribe"] != "True"
        and not any(w in r["address"] for w in auto_words)
        and "CATEGORY_" not in r["labels"]
    )


human = [r for r in rows if likely_human(r)]
print(f"\nLikely person-to-person emails: {len(human)} of {len(rows)}")
print("Top domains among them:")
for d, n in Counter(r["domain"] for r in human).most_common(15):
    print(f"  {d}: {n}")