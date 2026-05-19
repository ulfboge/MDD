import csv
import duckdb
from pathlib import Path

DB = Path("mdd_project/data/processed/mdd.duckdb")
REVIEW = Path("mdd_project/data/review")

c = duckdb.connect(str(DB), read_only=True)
inst = [r[0].upper() for r in c.execute("SELECT abbreviation FROM type_specimen_institutions").fetchall()]

rows = c.execute(
    """
    SELECT sci_name, type_voucher
    FROM species
    WHERE type_voucher IS NOT NULL AND TRIM(type_voucher) <> ''
    """
).fetchall()

completely_excluded = []
for sci_name, voucher in rows:
    v = voucher.strip().upper()
    if any(v.startswith(a) for a in inst):
        continue
    completely_excluded.append((sci_name, voucher))

# group by first token
from collections import Counter
import re

prefix_counts = Counter()
for sci_name, voucher in completely_excluded:
    m = re.match(r"^([A-Za-z][A-Za-z0-9./\-]{0,15}?)(?:\s|\(|$)", voucher.strip())
    prefix = (m.group(1) if m else voucher.split()[0]).upper()
    prefix_counts[prefix] += 1

out = REVIEW / "museum_completely_excluded_from_app.csv"
with out.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["sci_name", "type_voucher"])
    w.writerows(completely_excluded)

summary = REVIEW / "museum_completely_excluded_prefix_counts.csv"
with summary.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["voucher_prefix", "species_count"])
    for prefix, count in prefix_counts.most_common():
        w.writerow([prefix, count])

print(f"Species with vouchers matching no institution prefix: {len(completely_excluded)}")
print(f"Distinct voucher prefixes (excluded): {len(prefix_counts)}")
print("Top excluded prefixes:")
for prefix, count in prefix_counts.most_common(20):
    print(f"  {prefix:20} {count}")
