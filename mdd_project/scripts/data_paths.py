"""Canonical paths for MDD v2.4 raw CSV inputs."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
PROJECT = SCRIPTS.parent
REPO_ROOT = PROJECT.parent
RAW_MDD = PROJECT / "data" / "raw" / "MDD"

CSV_FILES = {
    "species_csv": "MDD_v2.4_6871species.csv",
    "synonyms_csv": "Species_Syn_v2.4.csv",
    "type_specimen_csv": "TypeSpecimenMetadata_v2.4.csv",
    "meta_csv": "META_v2.4.csv",
    "diff_csv": "Diff_v2.3-v2.4.csv",
}

TYPE_SPECIMEN_METADATA_CSV = RAW_MDD / CSV_FILES["type_specimen_csv"]
RELEASE_TOML = RAW_MDD / "release.toml"
DIFF_ALL_CHANGES_CSV = RAW_MDD / "Diff-AllChanges_v2.3-2.4.csv"


def find_raw_dir(hint: Path | None = None) -> Path:
    """Return the directory containing all required MDD CSV files."""
    candidates: list[Path] = []
    if hint:
        candidates.append(Path(hint))
    candidates += [
        RAW_MDD,
        REPO_ROOT,  # legacy layout
    ]
    for directory in candidates:
        if all((directory / name).exists() for name in CSV_FILES.values()):
            return directory.resolve()
    missing = [
        name
        for name in CSV_FILES.values()
        if not any((directory / name).exists() for directory in candidates)
    ]
    print(
        "\n[ERROR] Could not find all MDD CSV files.\n"
        f"  Missing: {missing}\n"
        "  Looked in:\n"
        + "\n".join(f"    {directory}" for directory in candidates)
        + "\n\n  Download MDD v2.4 from:\n"
        "    https://www.mammaldiversity.org/\n"
        "  or Zenodo: https://doi.org/10.5281/zenodo.18135819\n"
        f"  Place all CSV files in `{RAW_MDD}` (preferred) or the repo root.",
        file=sys.stderr,
    )
    sys.exit(1)
