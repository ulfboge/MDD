#!/usr/bin/env python3
"""Geocode NHRM type specimens missing coordinates from an MDD coverage export."""

from __future__ import annotations

import csv
import json
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

INPUT_CSV = Path(r"c:\Users\galag\Downloads\mdd_type_specimens_missing_coords_NHRM.csv")
OUTPUT_CSV = Path(r"c:\Users\galag\Downloads\mdd_type_specimens_missing_coords_NHRM_geocoded.csv")

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "MDD-geocoder/1.0 (research; contact: ulfboge@github)"


@dataclass
class GeocodeResult:
    query: str
    latitude: float | None
    longitude: float | None
    uncertainty_m: int | None
    method: str
    confidence: str
    notes: str


def nominatim_search(query: str) -> dict | None:
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


def geocode_with_nominatim(query: str, base_uncertainty_m: int, notes: str = "") -> GeocodeResult:
    try:
        hit = nominatim_search(query)
        time.sleep(1.1)
    except Exception as exc:  # noqa: BLE001
        return GeocodeResult(query, None, None, None, "nominatim_error", "none", f"{notes}; error={exc}")

    if not hit:
        return GeocodeResult(query, None, None, None, "nominatim_no_match", "none", notes)

    uncertainty = pick_uncertainty(hit.get("category"), hit.get("type"), base_uncertainty_m)
    confidence = "high" if uncertainty <= 25000 else "medium" if uncertainty <= 100000 else "low"
    detail = hit.get("display_name", "")
    return GeocodeResult(
        query=query,
        latitude=hit["lat"],
        longitude=hit["lon"],
        uncertainty_m=uncertainty,
        method="nominatim",
        confidence=confidence,
        notes=f"{notes}; match={detail}".strip("; "),
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
    )


def build_geocodes() -> dict[str, GeocodeResult]:
    """Curated geocode plan per species (sci_name)."""
    return {
        # Amazon: Santo Antônio on Rio Eiru/Eirú near Juruá — use Eiru River mouth area (MDD text).
        "Saguinus_subgrisescens": manual(
            "Eiru River, Juruá basin, Amazonas, Brazil",
            -6.6917,
            -69.8394,
            80000,
            "low",
            "Type locality: Santo Antônio, left bank Rio Eirú near Rio Juruá. "
            "Placed on Rio Eiru (Wikipedia: 6°41′30″S 69°50′22″W); exact settlement not verified.",
        ),
        "Cacajao_novaesi": manual(
            "Eiru River, Juruá basin, Amazonas, Brazil",
            -6.6917,
            -69.8394,
            80000,
            "low",
            "Type locality: Santo Antônio, Rio Eiru, Amazonas. Same river-basin anchor as S. subgrisescens.",
        ),
        # Restricted by Thomas 1907 to Pará state.
        "Euphractus_sexcinctus": manual(
            "Pará, Brazil (type restriction)",
            -3.79,
            -52.48,
            350000,
            "low",
            "Original 'America Meridionali'; restricted to Pará, Brazil. State-centroid proxy.",
        ),
        # Swedish Lapland — very vague historical label.
        "Craseomys_rufocanus": manual(
            "Lapland, Sweden (Lappmark)",
            66.50,
            17.50,
            250000,
            "low",
            "Type locality 'Lappmark, Sweden' is a historical region label only.",
        ),
        # Holotype 3 km from Madre de Dios–Beni confluence (Lönnberg 1942; zootaxa revision).
        "Dasypus_beniensis": manual(
            "Confluence Rio Madre de Dios and Rio Beni, Beni, Bolivia",
            -11.01,
            -66.06,
            30000,
            "medium",
            "Near confluence of Rio Madre de Dios with Rio Beni, Victoria, Bolivia. "
            "Coordinates placed at Riberalta-area confluence; specimen said to be ~3 km away.",
        ),
        # Country-level type locality.
        "Loris_tardigradus": manual(
            "Sri Lanka (type restriction: Ceylon)",
            7.87,
            80.77,
            200000,
            "low",
            "Type locality given only as Ceylon (= Sri Lanka). Country-centroid proxy.",
        ),
        # State-level type locality.
        "Ozimops_petersi": manual(
            "South Australia, Australia",
            -30.00,
            136.00,
            400000,
            "low",
            "Type locality given only as 'South Australia.' State-centroid proxy.",
        ),
        # Specific volcano and elevation in type string.
        "Hylomyscus_vulcanorum": manual(
            "Mount Karisimbi, Virunga volcanoes, DR Congo",
            -1.508,
            29.441,
            5000,
            "high",
            "Type locality: Birunga/Virunga Volcanoes, Mount Karisimbi, 3800 m. Summit-area coordinate.",
        ),
        # Thomas 1911 restriction to Sierra Leone.
        "Lemniscomys_striatus": manual(
            "Sierra Leone (type restriction)",
            8.46,
            -11.78,
            200000,
            "low",
            "Original 'India'; corrected by Thomas 1911 to Sierra Leone. Country-centroid proxy.",
        ),
        # Lower Congo — downstream Congo River / estuary region.
        "Lutra_congica": manual(
            "Lower Congo River, DRC",
            -5.82,
            13.45,
            150000,
            "low",
            "Type locality 'Lower Congo' — placed near lower Congo River / Matadi–Boma region.",
        ),
        "Cricetomys_kivuensis": manual(
            "Masisi, North Kivu, Democratic Republic of the Congo",
            -1.398,
            29.335,
            25000,
            "high",
            "Type locality: Masisi, DR Congo. Coordinates for Masisi, Nord-Kivu (not homonyms elsewhere).",
        ),
        "Anoura_aequatoris": geocode_with_nominatim(
            "Gualea, Pichincha, Ecuador",
            40000,
            "Type locality: Ilambo near Gualea, Pichincha, Ecuador.",
        ),
        "Pithecia_napensis": manual(
            "Napo River, Napo Province, Ecuador (~610 m)",
            -0.72,
            -77.69,
            100000,
            "medium",
            "Type locality: Napo river, 2000 ft (~610 m), Ecuador. "
            "Placed on mid–upper Napo River in Napo Province.",
        ),
        # Hershkovitz 1963 restriction to Lago do Baptista, Amazonas.
        "Plecturocebus_baptista": manual(
            "Lago do Baptista area, Amazonas, Brazil",
            -3.58,
            -59.13,
            60000,
            "low",
            "Original type locality unknown; restricted to Lago do Baptista, Amazonas. "
            "Approximate location in central Amazonas (Autazes / lower Madeira basin).",
        ),
        "Plecturocebus_modestus": manual(
            "Upper Río Beni basin near Rurrenabaque, Beni, Bolivia",
            -14.441,
            -67.528,
            60000,
            "medium",
            "Type locality: El Consuelo, Río Beni, Bolivia. Named locality not found in gazetteers; "
            "placed in upper Río Beni basin (P. modestus range) near Rurrenabaque.",
        ),
        "Plecturocebus_olallae": manual(
            "La Laguna near Santa Rosa de Yacuma, Beni, Bolivia",
            -14.0778,
            -66.7936,
            20000,
            "medium",
            "Type locality: La Laguna (5 km from Santa Rosa), Rio Beni. "
            "Anchored at Santa Rosa de Yacuma; lagoon ~5 km uncertainty added.",
        ),
        "Epomophorus_wahlbergi": geocode_with_nominatim(
            "Durban, KwaZulu-Natal, South Africa",
            15000,
            "Type locality: near Port Natal (= Durban), KwaZulu-Natal.",
        ),
        # Neotype locality between Durban and Maputo.
        "Scotophilus_dinganii": manual(
            "Between Durban, South Africa and Maputo, Mozambique",
            -28.50,
            32.00,
            250000,
            "low",
            "Neotype locality between Natal (Durban) and Delagoa Bay (Maputo). Midpoint corridor proxy.",
        ),
    }


def main() -> None:
    geocodes = build_geocodes()

    with INPUT_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    out_fields = list(rows[0].keys()) + [
        "geocode_query",
        "type_lat_suggested",
        "type_lon_suggested",
        "coordinate_uncertainty_m",
        "geocode_method",
        "geocode_confidence",
        "geocode_notes",
    ]

    out_rows: list[dict[str, str]] = []
    for row in rows:
        sci_name = row["sci_name"]
        result = geocodes.get(sci_name)
        if result is None:
            result = GeocodeResult("", None, None, None, "missing_plan", "none", "No geocode rule defined.")

        out_rows.append(
            {
                **row,
                "geocode_query": result.query,
                "type_lat_suggested": "" if result.latitude is None else f"{result.latitude:.6f}",
                "type_lon_suggested": "" if result.longitude is None else f"{result.longitude:.6f}",
                "coordinate_uncertainty_m": "" if result.uncertainty_m is None else str(result.uncertainty_m),
                "geocode_method": result.method,
                "geocode_confidence": result.confidence,
                "geocode_notes": result.notes,
            }
        )

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(out_rows)

    geocoded = sum(1 for r in out_rows if r["type_lat_suggested"])
    print(f"Wrote {OUTPUT_CSV}")
    print(f"Geocoded {geocoded}/{len(out_rows)} rows")


if __name__ == "__main__":
    main()
