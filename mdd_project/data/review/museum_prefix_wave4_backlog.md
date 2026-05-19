# Museum prefix wave 4 — investigation backlog

Generated after P3 alias fixes (BMNH, NMPR, MACN-MA, NSMT-M, NMNZ, OUM, CNM, …).
Use this file to research and resolve remaining prefix gaps before updating `TypeSpecimenMetadata_v2.4.csv`.

## Current snapshot

- **Completely unmatched vouchers:** 581 species
- **Prefix gaps in this backlog:** 36 rows
- **Not fixable via metadata:** `UNTRACED` (234) + `LOST` (136) = 370 species

## Priority legend

| Priority | Meaning |
|----------|---------|
| **P4-risky** | Wrong alias would mis-assign museum |
| **P4b-easy-alias** | Likely alias to existing institution; verify then add row |
| **P4b-variant** | Odd BMNH catalog strings; may need parser or extra alias |
| **P4c-orphan-high/medium** | No related metadata code; needs institution research (≥3 sp.) |
| **P4d-orphan-low** | Same, 2 species |

## P4-risky — resolve first

No current P4-risky prefixes after the latest metadata fixes.


## P4b — likely aliases (verify institution, then add metadata row)

### `KURODA` (5 sp.)

- **Priority:** P4b-easy-alias
- **Issue:** alias
- **On map via shorter code:** 5
- **Completely unmatched:** 0
- **Related metadata:** KU
- **Examples:** Alexandromys_kikuchii; Crocidura_tanakae; Mogera_tokudae
- **Suggested action:** Research Kuroda collection repository; do not map to KU (Kansas) based only on prefix similarity.
- **Notes:** Do not alias to KU (Kansas) without evidence. Kuroda is a Japanese collector/collection label; repository needs confirmation.

### `MNHN-ZM-MO-1867-146` (2 sp.)

- **Priority:** P4b-easy-alias
- **Issue:** alias
- **On map via shorter code:** 2
- **Completely unmatched:** 0
- **Related metadata:** MN; MNHN
- **Examples:** Cricetulus_longicaudatus; Lasiopodomys_mandarinus
- **Suggested action:** Treat as an MNHN catalog-number variant; prefer parser/normalization over a long institution alias.
- **Notes:** Long Paris MNHN catalog string; treat as MNHN variant or parser issue, not as MN.

### `NU` (2 sp.)

- **Priority:** P4b-easy-alias
- **Issue:** alias
- **On map via shorter code:** 0
- **Completely unmatched:** 2
- **Related metadata:** NUPECCE
- **Examples:** Nannospalax_karyominor; Nannospalax_colaki
- **Suggested action:** Confirm NU repository from the 2025 Zoologischer Anzeiger paper before adding a new metadata row.
- **Notes:** Not NUPECCE. Turkish Nannospalax types (NU 45 / NU 675); likely Niğde Ömer Halisdemir University, but repository needs confirmation from the 2025 Zoologischer Anzeiger paper.

### `BMNH:PV:M` (4 sp.)

- **Priority:** P4b-variant
- **Issue:** alias
- **On map via shorter code:** 4
- **Completely unmatched:** 0
- **Related metadata:** BM; BMNH
- **Examples:** Crocidura_katinka; Myomimus_roachi; Pennatomys_nivalis
- **Suggested action:** BMNH alias exists; these colon-suffix variants may still match BM/BMNH — low priority.
- **Notes:** Voucher prefix absent from metadata; shorter/longer related code exists (NRM-style mismatch).

### `BMNH:MAMM:1855.12.24.185` (2 sp.)

- **Priority:** P4b-variant
- **Issue:** alias
- **On map via shorter code:** 2
- **Completely unmatched:** 0
- **Related metadata:** BM; BMNH
- **Examples:** Leopardus_pardinoides; Phyllotis_xanthopygus
- **Suggested action:** BMNH alias exists; these colon-suffix variants may still match BM/BMNH — low priority.
- **Notes:** Voucher prefix absent from metadata; shorter/longer related code exists (NRM-style mismatch).

### `BMNH:MAMM:1907.1.1.339` (2 sp.)

- **Priority:** P4b-variant
- **Issue:** alias
- **On map via shorter code:** 2
- **Completely unmatched:** 0
- **Related metadata:** BM; BMNH
- **Examples:** Nyctophilus_gouldi; Lyroderma_sinense
- **Suggested action:** BMNH alias exists; these colon-suffix variants may still match BM/BMNH — low priority.
- **Notes:** Voucher prefix absent from metadata; shorter/longer related code exists (NRM-style mismatch).

### `BMNH:MAMM:22A` (2 sp.)

- **Priority:** P4b-variant
- **Issue:** alias
- **On map via shorter code:** 2
- **Completely unmatched:** 0
- **Related metadata:** BM; BMNH
- **Examples:** Hipposideros_fulvus; Sekeetamys_calurus
- **Suggested action:** BMNH alias exists; these colon-suffix variants may still match BM/BMNH — low priority.
- **Notes:** Voucher prefix absent from metadata; shorter/longer related code exists (NRM-style mismatch).

### `BMNH:PV:OR` (2 sp.)

- **Priority:** P4b-variant
- **Issue:** alias
- **On map via shorter code:** 2
- **Completely unmatched:** 0
- **Related metadata:** BM; BMNH
- **Examples:** Alticola_roylei; Lasiorhinus_krefftii
- **Suggested action:** BMNH alias exists; these colon-suffix variants may still match BM/BMNH — low priority.
- **Notes:** Voucher prefix absent from metadata; shorter/longer related code exists (NRM-style mismatch).


## P4c — orphan prefixes (≥3 species, needs new institution row)

### `CNP` (3 sp.)

- **Priority:** P4c-orphan-medium
- **Issue:** orphan
- **On map via shorter code:** 0
- **Completely unmatched:** 3
- **Related metadata:** —
- **Examples:** Tympanoctomys_kirchnerorum; Oecomys_franciscorum; Akodon_philipmyersi
- **Suggested action:** Research institution for CNP; add new metadata row if confirmed.
- **Notes:** Voucher prefix not in metadata; no related abbreviation detected.

### `EPN` (3 sp.)

- **Priority:** P4c-orphan-medium
- **Issue:** orphan
- **On map via shorter code:** 0
- **Completely unmatched:** 3
- **Related metadata:** —
- **Examples:** Lonchophylla_orcesi; Anoura_fistulata; Sturnira_koopmanhilli
- **Suggested action:** Research institution for EPN; add new metadata row if confirmed.
- **Notes:** Voucher prefix not in metadata; no related abbreviation detected.

### `ISAM` (3 sp.)

- **Priority:** P4c-orphan-medium
- **Issue:** orphan
- **On map via shorter code:** 0
- **Completely unmatched:** 3
- **Related metadata:** —
- **Examples:** Eremitalpa_granti; Cryptochloris_wintoni; Chlorotalpa_sclateri
- **Suggested action:** Research institution for ISAM; add new metadata row if confirmed.
- **Notes:** Voucher prefix not in metadata; no related abbreviation detected.

### `IZH` (3 sp.)

- **Priority:** P4c-orphan-medium
- **Issue:** orphan
- **On map via shorter code:** 0
- **Completely unmatched:** 3
- **Related metadata:** —
- **Examples:** Sigmodon_hirsutus; Gracilinanus_agilis; Molossops_temminckii
- **Suggested action:** Research institution for IZH; add new metadata row if confirmed.
- **Notes:** Voucher prefix not in metadata; no related abbreviation detected.

### `LHB` (3 sp.)

- **Priority:** P4c-orphan-medium
- **Issue:** orphan
- **On map via shorter code:** 0
- **Completely unmatched:** 3
- **Related metadata:** —
- **Examples:** Nannospalax_hungaricus; Mesocricetus_newtoni; Spalax_giganteus
- **Suggested action:** Research institution for LHB; add new metadata row if confirmed.
- **Notes:** Voucher prefix not in metadata; no related abbreviation detected.

### `OMUS` (3 sp.)

- **Priority:** P4c-orphan-medium
- **Issue:** orphan
- **On map via shorter code:** 0
- **Completely unmatched:** 3
- **Related metadata:** —
- **Examples:** Spermophilus_taurensis; Microtus_dogramacii; Talpa_hakkariensis
- **Suggested action:** Research institution for OMUS; add new metadata row if confirmed.
- **Notes:** Voucher prefix not in metadata; no related abbreviation detected.

### `SZM` (3 sp.)

- **Priority:** P4c-orphan-medium
- **Issue:** orphan
- **On map via shorter code:** 0
- **Completely unmatched:** 3
- **Related metadata:** —
- **Examples:** Spermophilus_vorontsovi; Sorex_camtschaticus; Marmota_kastschenkoi
- **Suggested action:** Research institution for SZM; add new metadata row if confirmed.
- **Notes:** Voucher prefix not in metadata; no related abbreviation detected.


## P4d — orphan prefixes (2 species)

See `museum_prefix_wave4_backlog.csv` for the full list.

## Workflow

1. Pick a prefix from **P4-risky** or **P4c-orphan-high**.
2. Confirm institution from original publication / collection database.
3. Add row to `TypeSpecimenMetadata_v2.4.csv` (or alias if same institution).
4. Rebuild: `python mdd_project/scripts/setup_database.py --skip-exports`
5. Regenerate audits: `python mdd_project/scripts/audit_museum_matching.py`

## Regenerate this file

```bash
python mdd_project/scripts/build_museum_prefix_wave4_backlog.py
```
