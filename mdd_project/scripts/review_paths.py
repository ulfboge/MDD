"""Canonical paths for mdd_project/data/review outputs."""

from __future__ import annotations

from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
PROJECT = SCRIPTS.parent
REVIEW = PROJECT / "data" / "review"
ARCHIVE = REVIEW / "archive"
GEOCODING = REVIEW / "geocoding"
MUSEUM = REVIEW / "museum"
QC = REVIEW / "qc"
ARCHIVE_QC = ARCHIVE / "qc"
ARCHIVE_MUSEUM_RESEARCH = ARCHIVE / "museum_research"

ESTIMATED_TYPE_LOCALITIES_CSV = GEOCODING / "estimated_type_localities.csv"
NOMINATIM_CACHE_JSON = GEOCODING / "nominatim_geocode_cache.json"
NHRM_GEOCODED_CSV = GEOCODING / "nhrm_type_specimens_missing_coords_geocoded.csv"
QC_SAMPLE_CSV = QC / "estimated_qc_sample.csv"

# Legacy names kept for script defaults / docs
REVIEW_DIR = REVIEW
DEFAULT_OUTPUT = ESTIMATED_TYPE_LOCALITIES_CSV
NOMINATIM_CACHE_PATH = NOMINATIM_CACHE_JSON
