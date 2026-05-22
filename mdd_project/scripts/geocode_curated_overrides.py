#!/usr/bin/env python3
"""Curated geocode overrides for type-locality estimation (review-only)."""

from __future__ import annotations

from typing import Callable

from geocode_type_localities import GeocodeResult, geocode_with_nominatim, manual


def build_nhrm_geocodes() -> dict[str, GeocodeResult]:
    """Curated geocode plan per species for NHRM missing-coordinate exports."""
    return {
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
        "Euphractus_sexcinctus": manual(
            "Pará, Brazil (type restriction)",
            -3.79,
            -52.48,
            350000,
            "low",
            "Original 'America Meridionali'; restricted to Pará, Brazil. State-centroid proxy.",
        ),
        "Craseomys_rufocanus": manual(
            "Lapland, Sweden (Lappmark)",
            66.50,
            17.50,
            250000,
            "low",
            "Type locality 'Lappmark, Sweden' is a historical region label only.",
        ),
        "Dasypus_beniensis": manual(
            "Confluence Rio Madre de Dios and Rio Beni, Beni, Bolivia",
            -11.01,
            -66.06,
            30000,
            "medium",
            "Near confluence of Rio Madre de Dios with Rio Beni, Victoria, Bolivia. "
            "Coordinates placed at Riberalta-area confluence; specimen said to be ~3 km away.",
        ),
        "Loris_tardigradus": manual(
            "Sri Lanka (type restriction: Ceylon)",
            7.87,
            80.77,
            200000,
            "low",
            "Type locality given only as Ceylon (= Sri Lanka). Country-centroid proxy.",
        ),
        "Ozimops_petersi": manual(
            "South Australia, Australia",
            -30.00,
            136.00,
            400000,
            "low",
            "Type locality given only as 'South Australia.' State-centroid proxy.",
        ),
        "Hylomyscus_vulcanorum": manual(
            "Mount Karisimbi, Virunga volcanoes, DR Congo",
            -1.508,
            29.441,
            5000,
            "high",
            "Type locality: Birunga/Virunga Volcanoes, Mount Karisimbi, 3800 m. Summit-area coordinate.",
        ),
        "Lemniscomys_striatus": manual(
            "Sierra Leone (type restriction)",
            8.46,
            -11.78,
            200000,
            "low",
            "Original 'India'; corrected by Thomas 1911 to Sierra Leone. Country-centroid proxy.",
        ),
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
        "Scotophilus_dinganii": manual(
            "Between Durban, South Africa and Maputo, Mozambique",
            -28.50,
            32.00,
            250000,
            "low",
            "Neotype locality between Natal (Durban) and Delagoa Bay (Maputo). Midpoint corridor proxy.",
        ),
    }


def build_qc_geocodes() -> dict[str, GeocodeResult]:
    """Curated fixes from QC review (parser / homonym failures)."""
    return {
        "Alexandromys_kikuchii": manual(
            "Mount Morrison (= Yushan), Taiwan",
            23.470028,
            120.957383,
            8000,
            "high",
            "Type locality: Mt Morrison, Taiwan. English name for Yushan (Jade Mountain); "
            "Nominatim query was wrongly reduced to 'Mt, Japan'.",
        ),
        "Plecotus_taivanus": manual(
            "Mt An-ma Shan, Ho-ping, Taichung County, Taiwan",
            24.181944,
            120.866389,
            8000,
            "high",
            "Type locality: Mt An-ma Shan, Ho-ping, Tai-chung Hsien, central Taiwan. "
            "Nominatim query was wrongly reduced to 'Mt, Japan'.",
        ),
        "Pseudoryx_nghetinhensis": manual(
            "Annamite Mountains, Vietnam (saola range)",
            17.750,
            105.850,
            50000,
            "medium",
            "Type locality given as Vietnam only. Placed in Annamite Mountains (Vu Quang / saola range).",
        ),
    }


CURATED_REGISTRY: dict[str, Callable[[], dict[str, GeocodeResult]]] = {
    "nhrm": build_nhrm_geocodes,
    "qc": build_qc_geocodes,
}


def get_curated_geocodes(name: str) -> dict[str, GeocodeResult]:
    key = name.strip().lower()
    if key not in CURATED_REGISTRY:
        known = ", ".join(sorted(CURATED_REGISTRY))
        raise ValueError(f"Unknown curated set {name!r}. Known sets: {known}")
    return CURATED_REGISTRY[key]()
