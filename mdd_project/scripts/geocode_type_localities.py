#!/usr/bin/env python3
"""
Estimate type-locality coordinates for MDD species missing official geocodes.

Outputs review-only suggested coordinates (type_lat_suggested / type_lon_suggested).
Never writes to species.type_lat / type_lon in DuckDB.

Phases (run in order; first successful phase wins):
  curated   — hand-maintained per-species rules (e.g. NHRM batch)
  explicit  — parse coordinates embedded in type_locality text
  nominatim — OpenStreetMap Nominatim lookup from cleaned locality text

Examples:
  python mdd_project/scripts/geocode_type_localities.py --museum NHRM --curated nhrm
  python mdd_project/scripts/geocode_type_localities.py --all-missing --phases explicit
  python mdd_project/scripts/geocode_type_localities.py --input-csv export.csv --phases curated,explicit
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

import duckdb

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "mdd_project" / "data" / "processed" / "mdd.duckdb"
REVIEW_DIR = ROOT / "mdd_project" / "data" / "review"
DEFAULT_OUTPUT = REVIEW_DIR / "estimated_type_localities.csv"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "MDD-geocoder/1.0 (research; contact: ulfboge@github)"
NOMINATIM_CACHE_PATH = REVIEW_DIR / "nominatim_geocode_cache.json"

MUSEUM_MATCH = """
    s.type_voucher IS NOT NULL
    AND TRIM(s.type_voucher) <> ''
    AND UPPER(TRIM(s.type_voucher)) LIKE UPPER(tsi.abbreviation) || '%'
"""

SPECIES_WITH_MUSEUM_CTE = f"""
species_with_museum AS (
    SELECT
        s.species_id,
        s.sci_name,
        REPLACE(s.sci_name, '_', ' ') AS sci_name_space,
        s.main_common_name,
        s."order",
        s.family,
        s.genus,
        s.type_voucher,
        s.type_kind,
        s.type_locality,
        s.type_lat,
        s.type_lon,
        (
            SELECT tsi.abbreviation
            FROM type_specimen_institutions tsi
            WHERE {MUSEUM_MATCH}
            ORDER BY LENGTH(tsi.abbreviation) DESC
            LIMIT 1
        ) AS museum_abbreviation,
        (
            SELECT tsi.full_name
            FROM type_specimen_institutions tsi
            WHERE {MUSEUM_MATCH}
            ORDER BY LENGTH(tsi.abbreviation) DESC
            LIMIT 1
        ) AS museum_name,
        (
            SELECT tsi.city_and_country
            FROM type_specimen_institutions tsi
            WHERE {MUSEUM_MATCH}
            ORDER BY LENGTH(tsi.abbreviation) DESC
            LIMIT 1
        ) AS museum_location,
        (
            SELECT TRIM(regexp_extract(tsi.city_and_country, '[^,]+$', 0))
            FROM type_specimen_institutions tsi
            WHERE {MUSEUM_MATCH}
              AND tsi.city_and_country IS NOT NULL
              AND TRIM(tsi.city_and_country) <> ''
            ORDER BY LENGTH(tsi.abbreviation) DESC
            LIMIT 1
        ) AS museum_country
    FROM species s
    WHERE s.type_voucher IS NOT NULL AND TRIM(s.type_voucher) <> ''
)
"""

SKIP_VOUCHER_PREFIXES = {
    "LOST",
    "UNTRACED",
    "NONEXISTENT",
    "SPECIMEN",
    "PHOTOGRAPHED",
    "FIGURED",
    "BOHMANN",
    "BUFFON'S",
    "MARCGRAVE'S",
    "MALE",
    "SEBA",
}

GEOCODE_OUTPUT_FIELDS = [
    "geocode_phase",
    "geocode_query",
    "type_lat_suggested",
    "type_lon_suggested",
    "coordinate_uncertainty_m",
    "geocode_method",
    "geocode_confidence",
    "geocode_notes",
    "review_status",
]


@dataclass
class GeocodeResult:
    query: str
    latitude: float | None
    longitude: float | None
    uncertainty_m: int | None
    method: str
    confidence: str
    notes: str
    phase: str = "none"


def load_nominatim_cache() -> dict[str, dict[str, object]]:
    if not NOMINATIM_CACHE_PATH.exists():
        return {}
    try:
        return json.loads(NOMINATIM_CACHE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_nominatim_cache(cache: dict[str, dict[str, object]]) -> None:
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    NOMINATIM_CACHE_PATH.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def _nominatim_search_remote(query: str) -> dict | None:
    params = urllib.parse.urlencode(
        {
            "q": query,
            "format": "jsonv2",
            "limit": 1,
            "addressdetails": 0,
        }
    )
    req = urllib.request.Request(
        f"{NOMINATIM_URL}?{params}",
        headers={"User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    if not data:
        return None
    hit = data[0]
    return {
        "lat": float(hit["lat"]),
        "lon": float(hit["lon"]),
        "category": hit.get("category"),
        "type": hit.get("type"),
        "importance": float(hit.get("importance", 0)),
        "display_name": hit.get("display_name", ""),
    }


def resolve_nominatim_hit(
    query: str,
    *,
    cache: dict[str, dict[str, object]] | None = None,
    write_cache: bool = False,
    sleep_s: float = 1.1,
) -> dict | None:
    if cache is not None and query in cache:
        cached = cache[query]
        return None if cached.get("error") else cached  # type: ignore[return-value]

    hit = _nominatim_search_remote(query)
    if cache is not None:
        cache[query] = hit if hit else {"error": "no_match"}
        if write_cache:
            save_nominatim_cache(cache)
    time.sleep(sleep_s)
    return hit


def pick_uncertainty(category: str | None, type_: str | None, base: int) -> int:
    if type_ in {"peak", "volcano", "mountain"}:
        return min(base, 5000)
    if type_ in {"city", "town", "village", "hamlet"}:
        return max(base, 15000)
    if type_ in {"state", "region", "county"}:
        return max(base, 150000)
    if type_ in {"country"}:
        return max(base, 300000)
    if category == "place" and type_ in {"locality", "isolated_dwelling"}:
        return max(base, 25000)
    return base


def geocode_with_nominatim(
    query: str,
    base_uncertainty_m: int,
    notes: str = "",
    *,
    sleep_s: float = 1.1,
    cache: dict[str, dict[str, object]] | None = None,
    write_cache: bool = False,
) -> GeocodeResult:
    try:
        hit = resolve_nominatim_hit(
            query,
            cache=cache,
            write_cache=write_cache,
            sleep_s=sleep_s,
        )
    except Exception as exc:  # noqa: BLE001
        return GeocodeResult(
            query,
            None,
            None,
            None,
            "nominatim_error",
            "none",
            f"{notes}; error={exc}".strip("; "),
            phase="nominatim",
        )

    if not hit:
        return GeocodeResult(
            query,
            None,
            None,
            None,
            "nominatim_no_match",
            "none",
            notes,
            phase="nominatim",
        )

    uncertainty = pick_uncertainty(hit.get("category"), hit.get("type"), base_uncertainty_m)
    confidence = "high" if uncertainty <= 25000 else "medium" if uncertainty <= 100000 else "low"
    detail = hit.get("display_name", "")
    return GeocodeResult(
        query=query,
        latitude=float(hit["lat"]),
        longitude=float(hit["lon"]),
        uncertainty_m=uncertainty,
        method="nominatim",
        confidence=confidence,
        notes=f"{notes}; match={detail}".strip("; "),
        phase="nominatim",
    )


def manual(
    query: str,
    lat: float,
    lon: float,
    uncertainty_m: int,
    confidence: str,
    notes: str,
) -> GeocodeResult:
    return GeocodeResult(
        query=query,
        latitude=lat,
        longitude=lon,
        uncertainty_m=uncertainty_m,
        method="manual_literature",
        confidence=confidence,
        notes=notes,
        phase="curated",
    )


def _hemisphere_sign(value: float, hemisphere: str) -> float:
    if hemisphere.upper() in {"S", "W"}:
        return -abs(value)
    return abs(value)


def _dms_to_decimal(deg: float, minute: float, second: float, hemisphere: str) -> float:
    value = deg + minute / 60.0 + second / 3600.0
    return _hemisphere_sign(value, hemisphere)


def _valid_wgs84(lat: float, lon: float) -> bool:
    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0


def parse_coordinates_from_locality(text: str) -> GeocodeResult | None:
    """Phase explicit: extract point coordinates already present in locality text."""
    if not text or not text.strip():
        return None

    cleaned = text.replace("″", '"').replace("′", "'").replace("´", "'")
    cleaned = re.sub(r"\s+", " ", cleaned)

    if re.search(r"\blatitudes?\b.*\band\b.*\blatitudes?\b", cleaned, re.I):
        return None

    patterns: list[tuple[str, re.Pattern[str]]] = [
        (
            "dms_quoted_seconds",
            re.compile(
                r"(\d{1,3})\s*°\s*(\d{1,2})\s*['\u2032]?\s*(\d+(?:\.\d+)?)\s*[\"″]?\s*([NSns])"
                r"\s*[,;]?\s*(\d{1,3})\s*°\s*(\d{1,2})\s*['\u2032]?\s*(\d+(?:\.\d+)?)\s*[\"″]?\s*([EWew])"
            ),
        ),
        (
            "dms_minutes",
            re.compile(
                r"(\d{1,3})\s*°\s*(\d{1,2})\s*['\u2032]?\s*([NSns])"
                r"\s*[,;]?\s*(\d{1,3})\s*°\s*(\d{1,2})\s*['\u2032]?\s*([EWew])"
            ),
        ),
        (
            "decimal_degrees",
            re.compile(
                r"(\d{1,2}(?:\.\d+)?)\s*°\s*([NSns])\s*[,;]?\s*(\d{1,3}(?:\.\d+)?)\s*°\s*([EWew])"
            ),
        ),
        (
            "decimal_pair",
            re.compile(r"([-]?\d{1,2}\.\d+)\s*°?\s*([NSns])\s*[,;]\s*([-]?\d{1,3}\.\d+)\s*°?\s*([EWew])"),
        ),
    ]

    for label, pattern in patterns:
        match = pattern.search(cleaned)
        if not match:
            continue
        groups = match.groups()
        try:
            if label == "dms_quoted_seconds":
                lat = _dms_to_decimal(
                    float(groups[0]), float(groups[1]), float(groups[2]), groups[3]
                )
                lon = _dms_to_decimal(
                    float(groups[4]), float(groups[5]), float(groups[6]), groups[7]
                )
            elif label == "dms_minutes":
                lat = _dms_to_decimal(float(groups[0]), float(groups[1]), 0.0, groups[2])
                lon = _dms_to_decimal(float(groups[3]), float(groups[4]), 0.0, groups[5])
            elif label == "decimal_degrees":
                lat = _hemisphere_sign(float(groups[0]), groups[1])
                lon = _hemisphere_sign(float(groups[2]), groups[3])
            else:
                lat = _hemisphere_sign(float(groups[0]), groups[1])
                lon = _hemisphere_sign(float(groups[2]), groups[3])
        except ValueError:
            continue

        if not _valid_wgs84(lat, lon):
            continue

        return GeocodeResult(
            query=match.group(0).strip(),
            latitude=lat,
            longitude=lon,
            uncertainty_m=2000,
            method="parse_locality_text",
            confidence="high",
            notes="Coordinates parsed directly from type_locality text.",
            phase="explicit",
        )

    return None


def skip_reason(voucher: str | None, locality: str | None) -> str | None:
    voucher_upper = (voucher or "").strip().upper()
    if not voucher_upper:
        return "missing_type_voucher"
    token = re.match(r"^([A-ZÄÖÜÅÆØĐ'./-]+)", voucher_upper)
    prefix = token.group(1).rstrip("./-") if token else voucher_upper.split()[0]
    if prefix in SKIP_VOUCHER_PREFIXES:
        return f"non_geocodeable_voucher_prefix:{prefix}"
    if "number not known" in voucher_upper.lower():
        return "voucher_number_unknown"
    if not locality or not locality.strip():
        return "missing_type_locality"
    return None


def build_nominatim_query(locality: str) -> str:
    text = locality.strip().strip('"')
    text = re.sub(r"^Restricted by .*? to ", "", text, flags=re.I)
    text = re.sub(r"^Corrected by .*? to ", "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text)
    if "." in text:
        text = text.split(".")[0]
    return text[:240]


def geocode_row(
    row: dict[str, Any],
    *,
    phases: list[str],
    curated: dict[str, GeocodeResult] | None = None,
    nominatim_sleep_s: float = 1.1,
    nominatim_cache: dict[str, dict[str, object]] | None = None,
    write_nominatim_cache: bool = False,
) -> GeocodeResult:
    sci_name = str(row.get("sci_name", ""))
    voucher = row.get("type_voucher")
    locality = row.get("type_locality")

    if "curated" in phases and curated and sci_name in curated:
        return curated[sci_name]

    reason = skip_reason(
        str(voucher) if voucher is not None else None,
        str(locality) if locality is not None else None,
    )
    if reason:
        return GeocodeResult("", None, None, None, "skipped", "none", reason, phase="skipped")

    if "explicit" in phases:
        parsed = parse_coordinates_from_locality(str(locality))
        if parsed is not None:
            return parsed

    if "nominatim" in phases:
        query = build_nominatim_query(str(locality))
        if len(query) >= 8:
            return geocode_with_nominatim(
                query,
                base_uncertainty_m=50000,
                notes=f"Nominatim query derived from type_locality for {sci_name}.",
                sleep_s=nominatim_sleep_s,
                cache=nominatim_cache,
                write_cache=write_nominatim_cache,
            )

    return GeocodeResult(
        "",
        None,
        None,
        None,
        "no_match",
        "none",
        "No geocode result from configured phases.",
        phase="none",
    )


def load_rows_from_duckdb(
    *,
    museum: str | None = None,
    country: str | None = None,
    all_missing: bool = False,
    missing_geolocation: bool = True,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    if not all_missing and not museum and not country:
        raise ValueError("Provide --museum, --country, or --all-missing.")

    conditions = ["1=1"]
    params: list[Any] = []

    if all_missing:
        sql_from = f"""
            SELECT
                s.species_id,
                s.sci_name,
                REPLACE(s.sci_name, '_', ' ') AS sci_name_space,
                s.main_common_name,
                s."order",
                s.family,
                s.genus,
                s.type_voucher,
                s.type_kind,
                s.type_locality,
                s.type_lat,
                s.type_lon,
                (
                    SELECT tsi.abbreviation
                    FROM type_specimen_institutions tsi
                    WHERE {MUSEUM_MATCH.replace("s.", "s.")}
                    ORDER BY LENGTH(tsi.abbreviation) DESC
                    LIMIT 1
                ) AS museum_abbreviation,
                (
                    SELECT tsi.full_name
                    FROM type_specimen_institutions tsi
                    WHERE {MUSEUM_MATCH.replace("s.", "s.")}
                    ORDER BY LENGTH(tsi.abbreviation) DESC
                    LIMIT 1
                ) AS museum_name,
                (
                    SELECT tsi.city_and_country
                    FROM type_specimen_institutions tsi
                    WHERE {MUSEUM_MATCH.replace("s.", "s.")}
                    ORDER BY LENGTH(tsi.abbreviation) DESC
                    LIMIT 1
                ) AS museum_location,
                (
                    SELECT TRIM(regexp_extract(tsi.city_and_country, '[^,]+$', 0))
                    FROM type_specimen_institutions tsi
                    WHERE {MUSEUM_MATCH.replace("s.", "s.")}
                      AND tsi.city_and_country IS NOT NULL
                      AND TRIM(tsi.city_and_country) <> ''
                    ORDER BY LENGTH(tsi.abbreviation) DESC
                    LIMIT 1
                ) AS museum_country
            FROM species s
        """
        conditions.append("s.type_locality IS NOT NULL AND TRIM(s.type_locality) <> ''")
        if missing_geolocation:
            conditions.append("(s.type_lat IS NULL OR s.type_lon IS NULL)")
    else:
        sql_from = f"""
            WITH {SPECIES_WITH_MUSEUM_CTE}
            SELECT
                species_id,
                sci_name,
                sci_name_space,
                main_common_name,
                "order",
                family,
                genus,
                type_voucher,
                type_kind,
                type_locality,
                type_lat,
                type_lon,
                museum_abbreviation,
                museum_name,
                museum_location,
                museum_country
            FROM species_with_museum
        """
        if missing_geolocation:
            conditions.append("(type_lat IS NULL OR type_lon IS NULL)")

    if museum:
        conditions.append("museum_abbreviation ILIKE ?")
        params.append(museum.strip())
    if country:
        conditions.append("museum_country ILIKE ?")
        params.append(country.strip())

    where = " AND ".join(conditions)
    sql = f"{sql_from} WHERE {where} ORDER BY sci_name"
    if limit is not None:
        sql += f" LIMIT {int(limit)}"

    conn = duckdb.connect(str(DB), read_only=True)
    try:
        df = conn.execute(sql, params).fetchdf()
    finally:
        conn.close()

    return df.to_dict(orient="records")


def load_rows_from_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def result_to_output(result: GeocodeResult) -> dict[str, str]:
    review_status = "proposed" if result.latitude is not None else "no_estimate"
    if result.phase == "skipped":
        review_status = "skipped"
    return {
        "geocode_phase": result.phase,
        "geocode_query": result.query,
        "type_lat_suggested": "" if result.latitude is None else f"{result.latitude:.6f}",
        "type_lon_suggested": "" if result.longitude is None else f"{result.longitude:.6f}",
        "coordinate_uncertainty_m": "" if result.uncertainty_m is None else str(result.uncertainty_m),
        "geocode_method": result.method,
        "geocode_confidence": result.confidence,
        "geocode_notes": result.notes,
        "review_status": review_status,
    }


def write_geocoded_csv(rows: list[dict[str, Any]], output: Path) -> None:
    if not rows:
        raise ValueError("No rows to write.")

    input_fields = [k for k in rows[0].keys() if k not in GEOCODE_OUTPUT_FIELDS]
    fieldnames = input_fields + GEOCODE_OUTPUT_FIELDS
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def run_geocoder(
    rows: Iterable[dict[str, Any]],
    *,
    phases: list[str],
    curated: dict[str, GeocodeResult] | None = None,
    nominatim_sleep_s: float = 1.1,
    nominatim_cache: dict[str, dict[str, object]] | None = None,
    write_nominatim_cache: bool = False,
    output: Path | None = None,
    checkpoint_every: int = 100,
) -> list[dict[str, Any]]:
    out_rows: list[dict[str, Any]] = []
    rows_list = list(rows)
    use_nominatim = "nominatim" in phases
    for index, row in enumerate(rows_list, start=1):
        result = geocode_row(
            row,
            phases=phases,
            curated=curated,
            nominatim_sleep_s=nominatim_sleep_s,
            nominatim_cache=nominatim_cache,
            write_nominatim_cache=write_nominatim_cache,
        )
        out_rows.append({**row, **result_to_output(result)})
        if output and checkpoint_every and index % checkpoint_every == 0:
            write_geocoded_csv(out_rows, output)
        if use_nominatim and index % 100 == 0:
            proposed = sum(1 for r in out_rows if r.get("type_lat_suggested"))
            print(f"  progress {index}/{len(rows_list)} · proposed={proposed}", flush=True)
    if use_nominatim and nominatim_cache is not None and write_nominatim_cache:
        save_nominatim_cache(nominatim_cache)
    return out_rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        status = str(row.get("review_status", "unknown"))
        counts[status] = counts.get(status, 0) + 1
        phase = str(row.get("geocode_phase", "none"))
        if row.get("type_lat_suggested"):
            counts[f"phase:{phase}"] = counts.get(f"phase:{phase}", 0) + 1
    return counts


def parse_phases(raw: str) -> list[str]:
    allowed = {"curated", "explicit", "nominatim"}
    phases = [part.strip().lower() for part in raw.split(",") if part.strip()]
    unknown = [p for p in phases if p not in allowed]
    if unknown:
        raise ValueError(f"Unknown phases: {unknown}. Allowed: {sorted(allowed)}")
    if not phases:
        raise ValueError("At least one phase is required.")
    return phases


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input-csv", type=Path, help="Coverage export CSV or compatible input.")
    source.add_argument("--museum", help="Museum abbreviation filter (e.g. NHRM).")
    source.add_argument("--country", help="Museum country filter.")
    source.add_argument(
        "--all-missing",
        action="store_true",
        help="All species with type locality text but no official coordinates.",
    )
    parser.add_argument(
        "--phases",
        default="curated,explicit",
        help="Comma-separated phases: curated, explicit, nominatim (default: curated,explicit).",
    )
    parser.add_argument(
        "--curated",
        help="Named curated override set (e.g. nhrm) from geocode_curated_overrides.py.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output CSV path (default: {DEFAULT_OUTPUT}).",
    )
    parser.add_argument("--limit", type=int, help="Optional row limit for DuckDB queries.")
    parser.add_argument(
        "--include-geocoded",
        action="store_true",
        help="Include rows that already have official type_lat/type_lon.",
    )
    parser.add_argument(
        "--nominatim-sleep",
        type=float,
        default=1.1,
        help="Seconds to sleep between Nominatim requests (default: 1.1).",
    )
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    phases = parse_phases(args.phases)

    curated: dict[str, GeocodeResult] | None = None
    if args.curated:
        from geocode_curated_overrides import get_curated_geocodes

        curated = get_curated_geocodes(args.curated)
        if "curated" not in phases:
            phases = ["curated", *phases]

    if args.input_csv:
        rows = load_rows_from_csv(args.input_csv)
    else:
        rows = load_rows_from_duckdb(
            museum=args.museum,
            country=args.country,
            all_missing=args.all_missing,
            missing_geolocation=not args.include_geocoded,
            limit=args.limit,
        )

    out_rows = run_geocoder(
        rows,
        phases=phases,
        curated=curated,
        nominatim_sleep_s=args.nominatim_sleep,
        nominatim_cache=load_nominatim_cache() if "nominatim" in phases else None,
        write_nominatim_cache="nominatim" in phases,
        output=args.output,
        checkpoint_every=100,
    )
    write_geocoded_csv(out_rows, args.output)

    stats = summarize(out_rows)
    proposed = stats.get("proposed", 0)
    print(f"Wrote {len(out_rows)} rows to {args.output}")
    print(f"Proposed coordinates: {proposed}/{len(out_rows)}")
    for key in sorted(stats):
        if key.startswith("phase:"):
            print(f"  {key}: {stats[key]}")
    for status in ("skipped", "no_estimate"):
        if status in stats:
            print(f"  {status}: {stats[status]}")


if __name__ == "__main__":
    main()
