"""Emit counts and groupings for unmatched type voucher review (UTF-8 report)."""

from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path

UNMATCHED = Path(__file__).resolve().parents[1] / "data/review/museum_vouchers_unmatched.csv"
OUT = Path(__file__).resolve().parents[1] / "data/review/museum_unmatched_bucket_counts.txt"


def main() -> None:
    rows = list(csv.DictReader(UNMATCHED.open(encoding="utf-8")))
    lines: list[str] = [f"Total unmatched species rows: {len(rows)}", ""]

    def bucket(voucher: str) -> str:
        v = (voucher or "").strip()
        u = v.upper()
        if u.startswith("UNTRACED"):
            return "untraced"
        if u.startswith("LOST"):
            return "lost"
        if u.startswith("SPECIMEN ") or "specimen collected" in v.lower():
            return "specimen_narrative"
        if "photographed specimen" in v.lower() or u.startswith("PHOTOGRAPHED"):
            return "photographed"
        if u.startswith("FIGURED ") or "figured specimen" in v.lower():
            return "figured"
        if "buffon" in u.lower():
            return "historic_buffon"
        if "seba" in u.lower() and "pl" in v.lower():
            return "historic_seba"
        if "marcgrave" in v.lower():
            return "historic_marcgrave"
        if u.startswith("BOHMANN"):
            return "collector_bohmann"
        if u.startswith("LINNMUS"):
            return "historic_linnmus"
        if re.match(r"^\d{3}y\d{2}[a-z]+", v.lower()):
            return "cheirogaleid_tag"
        if re.match(r"^XZ\d+", v):
            return "xz_field_code"
        return "other_alphanumeric"

    bc = Counter(bucket(r["type_voucher"]) for r in rows)
    lines.append("Primary buckets:")
    for k, n in bc.most_common():
        lines.append(f"  {n:4}  {k}")

    # Within "other", first-token prefix (rough)
    other = [r for r in rows if bucket(r["type_voucher"]) == "other_alphanumeric"]

    def first_token_pref(v: str) -> str:
        v = v.strip().strip('"')
        m = re.match(r"^([A-Za-z][A-Za-z0-9./\-]{0,24}?)(?:\s|[:(]|$)", v)
        if m:
            return m.group(1).upper().rstrip("./-")
        return (v.split()[0] if v.split() else v)[:40].upper()

    oc = Counter(first_token_pref(r["type_voucher"]) for r in other)
    lines.append("")
    lines.append(
        f"Distinct rough prefixes in 'other_alphanumeric' ({len(other)} rows): {len(oc)}"
    )
    lines.append("All (alphabetical by prefix):")
    for pref, n in sorted(oc.items(), key=lambda x: x[0]):
        lines.append(f"  {n:3}  {pref}")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(Path.cwd())}")


if __name__ == "__main__":
    main()
