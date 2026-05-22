"""
Country hints and Nominatim match validation for estimated type-locality geocoding.

Shared by geocode_type_localities.py and QC suggestion scripts.
"""

from __future__ import annotations

import re
from typing import Iterable

# (locality regex, query country suffix, match tokens in Nominatim display_name)
COUNTRY_RULES: list[tuple[re.Pattern[str], str, tuple[str, ...]]] = [
    (re.compile(r"\bTaiwan\b|Tai-chung|Ho-ping|An-ma Shan", re.I), "Taiwan", ("Taiwan", "臺灣", "台湾")),
    (re.compile(r"\bBrazil\b|\bBrasil\b|Rio de Janeiro|Rio Tocantins|Cametá|Espiritu Santo|Espírito Santo", re.I), "Brazil", ("Brazil", "Brasil")),
    (re.compile(r"\bPanama\b|Chagres", re.I), "Panama", ("Panama", "Panamá")),
    (re.compile(r"\bMexico\b|México|Puebla|Chiapas|Orizaba", re.I), "Mexico", ("Mexico", "México")),
    (re.compile(r"\bArgentina\b|Tucumán|Tucuman|San Juan", re.I), "Argentina", ("Argentina",)),
    (re.compile(r"\bGuyana\b|Demerara|Kanuku", re.I), "Guyana", ("Guyana",)),
    (re.compile(r"\bAustralia\b|Tasmania|Van Diemen|Queensland|New South Wales|Western Australia|New Holland|Derby, N\. W", re.I), "Australia", ("Australia", "Tasmania", "Queensland")),
    (re.compile(r"\bArizona\b|Coconino|San Francisco Mtn|San Francisco Mountain|Charleston Peak|Nevada\b|Clark County", re.I), "United States", ("United States", "Arizona", "Nevada")),
    (re.compile(r"\bRwanda\b|Sabyinyo", re.I), "Rwanda", ("Rwanda",)),
    (re.compile(r"\bMadagascar\b|Madagasikara|Montagne d'Ambre|Bélo", re.I), "Madagascar", ("Madagascar", "Madagasikara")),
    (re.compile(r"\bEthiopia\b|Lake Tsana|Lake Tana|Zegi", re.I), "Ethiopia", ("Ethiopia", "ኢትዮጵያ")),
    (re.compile(r"\bSudan\b|Jebel Mara", re.I), "Sudan", ("Sudan", "السودان")),
    (re.compile(r"\bDR Congo\b|\bCongo\b|Masisi|Kivu|Karisimbi|Virunga|Birunga", re.I), "Democratic Republic of the Congo", ("Congo", "République démocratique", "Democratic Republic", "Kivu", "Virunga")),
    (re.compile(r"\bPapua New Guinea\b|Mt\. Dayman|Maneau Range", re.I), "Papua New Guinea", ("Papua New Guinea", "Papua Niugini")),
    (re.compile(r"\bNew Guinea\b|Arfak|Irian", re.I), "Indonesia", ("Indonesia", "Papua", "New Guinea", "Irian")),
    (re.compile(r"\bMalaysia\b|Sabah|Kinabalu", re.I), "Malaysia", ("Malaysia", "Sabah")),
    (re.compile(r"\bChina\b|Yunnan|Lijiang|Sichuan|Snow Mountain|Ssu-shan", re.I), "China", ("China", "中国", "Yunnan", "Sichuan")),
    (re.compile(r"\bLaos\b|Phong Saly|ລາວ|ປະເທດລາວ", re.I), "Laos", ("Laos", "ລາວ", "ປະເທດລາວ")),
    (re.compile(r"\bJava\b|\bIndonesia\b", re.I), "Indonesia", ("Indonesia", "Java", "Jawa")),
    (re.compile(r"\bNepal\b", re.I), "Nepal", ("Nepal", "नेपाल")),
    (re.compile(r"\bColombia\b|Bogotá|Bogota", re.I), "Colombia", ("Colombia",)),
    (re.compile(r"\bPeru\b|Chanchamayo", re.I), "Peru", ("Peru", "Perú")),
    (re.compile(r"\bParaguay\b", re.I), "Paraguay", ("Paraguay", "Paraguái")),
    (re.compile(r"\bVenezuela\b|Caracas", re.I), "Venezuela", ("Venezuela",)),
    (re.compile(r"\bGuatemala\b|Petén|Uaxactún", re.I), "Guatemala", ("Guatemala",)),
    (re.compile(r"\bEcuador\b|Imbabura|Chinipamba", re.I), "Ecuador", ("Ecuador",)),
    (re.compile(r"\bGabon\b", re.I), "Gabon", ("Gabon",)),
    (re.compile(r"\bGambia\b", re.I), "Gambia", ("Gambia",)),
    (re.compile(r"\bEgypt\b", re.I), "Egypt", ("Egypt", "مصر")),
    (re.compile(r"\bJapan\b|Mt\. Morrison", re.I), "Japan", ("Japan", "日本", "Nippon")),
    (re.compile(r"\bSierra Leone\b", re.I), "Sierra Leone", ("Sierra Leone",)),
    (re.compile(r"\bSouth Africa\b", re.I), "South Africa", ("South Africa",)),
    (re.compile(r"\bNicaragua\b|Lago Nicaragua", re.I), "Nicaragua", ("Nicaragua",)),
    (re.compile(r"\bUnited Kingdom\b|\bScotland\b|\bEngland\b", re.I), "United Kingdom", ("United Kingdom", "Scotland", "England", "Alba")),
]

DIPLOMATIC_REJECT = re.compile(
    r"Embassy|Embassade|Ambassade|Consulate|Consulat|High Commission|قنصلية|"
    r"Embajada|Botschaft|Ambassade de",
    re.I,
)

# Country-only localities (whole string is essentially just a country name)
COUNTRY_ONLY = re.compile(
    r'^[\s"]*(?:'
    r"Paraguay|Egypt|Ethiopia|Gabon|Gambia|Nepal|Japan|Sierra Leone|"
    r"South America|Indonesia, Java"
    r')[\s."]*$',
    re.I,
)


def locality_country_hints(locality: str) -> list[tuple[str, tuple[str, ...]]]:
    """Return (query_country, match_tokens) for each rule matching the locality."""
    hints: list[tuple[str, tuple[str, ...]]] = []
    seen: set[str] = set()
    for pattern, query_country, match_tokens in COUNTRY_RULES:
        if pattern.search(locality) and query_country not in seen:
            hints.append((query_country, match_tokens))
            seen.add(query_country)
    return hints


def infer_query_country(locality: str, museum_country: str | None) -> str | None:
    """
    Prefer country implied by type_locality over museum holding country.

    US museums often hold types from Panama, Mexico, etc. — appending
    'United States of America' causes systematic false positives.
    """
    hints = locality_country_hints(locality)
    if hints:
        return hints[-1][0]

    museum = (museum_country or "").strip()
    if not museum:
        return None

    # Do not append museum country for country-only localities.
    if COUNTRY_ONLY.match(locality.strip()):
        return None

    loc_lower = locality.lower()
    if museum.lower() in loc_lower:
        return None

    return museum


def token_in_display_name(token: str, display_name: str) -> bool:
    text = display_name
    lower = text.lower()
    token_lower = token.lower()

    if token_lower == "mexico":
        if re.search(r"\bnew mexico\b", text, re.I):
            return False
        return bool(re.search(r"\bm[ée]xico\b", text, re.I))

    if token_lower == "congo":
        return "congo" in lower

    if len(token) <= 3:
        return bool(re.search(rf"\b{re.escape(token)}\b", text, re.I))
    return token_lower in lower


def display_name_matches_locality(locality: str, display_name: str) -> tuple[bool, str]:
    """Return (ok, reason). Empty reason when ok."""
    if DIPLOMATIC_REJECT.search(display_name):
        return False, "diplomatic_mission_match"

    hints = locality_country_hints(locality)
    if not hints:
        return True, ""

    for _query_country, match_tokens in hints:
        if any(token_in_display_name(token, display_name) for token in match_tokens):
            return True, ""

    expected = ", ".join(sorted({t for _, tokens in hints for t in tokens[:2]}))
    return False, f"country_mismatch: expected one of [{expected}]"


def suggest_qc_decision(row: dict[str, str]) -> tuple[str, str, bool]:
    """
    Suggest qc_decision, qc_notes, uncertain flag for a proposed coordinate row.

    Returns decision in {accept, reject, review}.
    """
    method = row.get("geocode_method", "")
    notes = row.get("geocode_notes", "")
    locality = row.get("type_locality", "")
    display = notes.split("match=", 1)[1] if "match=" in notes else notes

    if method == "manual_literature":
        return "accept", "curated manual_literature", False

    if method != "nominatim":
        return "review", f"non-nominatim method: {method}", True

    if DIPLOMATIC_REJECT.search(display):
        return "reject", "embassy/consulate false positive", False

    ok, reason = display_name_matches_locality(locality, display)
    if not ok:
        return "reject", reason, False

    hints = locality_country_hints(locality)
    if not hints:
        conf = row.get("geocode_confidence", "")
        if conf == "medium":
            return "review", "medium confidence, no country rule", True
        return "accept", "no country rule; visually verify", True

    # Extra checks for ambiguous cases
    if re.search(r"\bNew Holland\b", locality, re.I) and "Illinois" in display:
        return "reject", "New Holland → US false positive", False
    if re.search(r"South America\b", locality, re.I) and "América" in display:
        return "reject", "continent-only locality too coarse", False
    if re.search(r"Derby, N\. W", locality, re.I) and "Polska" in display:
        return "reject", "Derby WA → Poland false positive", False
    if re.search(r"Cerro San Javier", locality, re.I) and "San Juan" in display:
        if re.search(r"Tucum", locality, re.I) and not re.search(r"Tucum", display, re.I):
            return "reject", "Cerro San Javier: Tucumán vs San Juan province", False
        return "review", "Cerro San Javier: verify province", True

    return "accept", "country hint matches Nominatim result", False
