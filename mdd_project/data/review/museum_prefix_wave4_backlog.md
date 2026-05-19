# Museum prefix wave 4 — investigation backlog

Generated after P3 alias fixes (BMNH, NMPR, MACN-MA, NSMT-M, NMNZ, OUM, CNM, …).
Use this file to research and resolve remaining prefix gaps before updating `TypeSpecimenMetadata_v2.4.csv`.

## Current snapshot

- **Completely unmatched vouchers:** 611 species
- **Prefix gaps in this backlog:** 51 rows
- **Not fixable via metadata:** `UNTRACED` (234) + `LOST` (136) = 370 species

## Priority legend

| Priority | Meaning |
|----------|---------|
| **P4-risky** | Wrong alias would mis-assign museum (CMI/CMN→CM, MNK→MN) |
| **P4b-easy-alias** | Likely alias to existing institution; verify then add row |
| **P4b-variant** | Odd BMNH catalog strings; may need parser or extra alias |
| **P4c-orphan-high/medium** | No related metadata code; needs institution research (≥3 sp.) |
| **P4d-orphan-low** | Same, 2 species |

## P4-risky — resolve first

### `CMI` (5 sp.)

- **Priority:** P4-risky
- **Issue:** alias
- **On map via shorter code:** 5
- **Completely unmatched:** 0
- **Related metadata:** CM
- **Examples:** Salinomys_delicatus; Akodon_oenos; Phyllotis_pehuenche
- **Suggested action:** Identify institution per voucher; add CMN (Canadian Museum of Nature) or fix CM row — do NOT alias to Carnegie CM.
- **Notes:** BLOCKER: CM in metadata = Carnegie Museum (Pittsburgh). Vouchers look South American — likely Canadian Museum of Nature (CMN) or other. Do not alias to CM without verifying institution.

### `MNK` (4 sp.)

- **Priority:** P4-risky
- **Issue:** alias
- **On map via shorter code:** 4
- **Completely unmatched:** 0
- **Related metadata:** MN
- **Examples:** Juscelinomys_huanchacae; Oecomys_sydandersoni; Hylaeamys_acritus
- **Suggested action:** Add MNK row for correct museum; prevents false match to Museu Nacional (MN).
- **Notes:** BLOCKER: MN now matches Museu Nacional (Rio). MNK vouchers currently mis-match to MN. Add dedicated MNK row after identifying holding museum.

### `CMN` (2 sp.)

- **Priority:** P4-risky
- **Issue:** alias
- **On map via shorter code:** 2
- **Completely unmatched:** 0
- **Related metadata:** CM
- **Examples:** Phenacomys_intermedius; Dicrostonyx_nunatakensis
- **Suggested action:** Identify institution per voucher; add CMN (Canadian Museum of Nature) or fix CM row — do NOT alias to Carnegie CM.
- **Notes:** BLOCKER: same as CMI — CM is Carnegie in metadata, but CMN usually = Canadian Museum of Nature (Ottawa). May need new CMN row, not CM alias.


## P4b — likely aliases (verify institution, then add metadata row)

### `KURODA` (5 sp.)

- **Priority:** P4b-easy-alias
- **Issue:** alias
- **On map via shorter code:** 5
- **Completely unmatched:** 0
- **Related metadata:** KU
- **Examples:** Alexandromys_kikuchii; Crocidura_tanakae; Mogera_tokudae
- **Suggested action:** Add KURODA alias row pointing to same institution as KU.
- **Notes:** Likely alias for KU (University of Kansas). Japanese/E Asian types collected by Kuroda.

### `UFMG` (3 sp.)

- **Priority:** P4b-easy-alias
- **Issue:** alias
- **On map via shorter code:** 3
- **Completely unmatched:** 0
- **Related metadata:** UF
- **Examples:** Rhipidomys_tribei; Cyclopes_xinguensis; Cyclopes_rufus
- **Suggested action:** Add UFMG alias row pointing to same institution as UF.
- **Notes:** Likely Universidade Federal de Minas Gerais — do not alias to UF (Florida). Needs new UFMG row.

### `MNHN-ZM-MO-1867-146` (2 sp.)

- **Priority:** P4b-easy-alias
- **Issue:** alias
- **On map via shorter code:** 2
- **Completely unmatched:** 0
- **Related metadata:** MN; MNHN
- **Examples:** Cricetulus_longicaudatus; Lasiopodomys_mandarinus
- **Suggested action:** Add MNHN-ZM-MO-1867-146 alias row pointing to same institution as MN.
- **Notes:** Long Paris MNHN catalog string — add alias or normalize matching.

### `NU` (2 sp.)

- **Priority:** P4b-easy-alias
- **Issue:** alias
- **On map via shorter code:** 0
- **Completely unmatched:** 2
- **Related metadata:** NUPECCE
- **Examples:** Nannospalax_karyominor; Nannospalax_colaki
- **Suggested action:** Add NU alias row pointing to same institution as NUPECCE.
- **Notes:** Likely alias for NUPECCE (Jaboticabal, Brazil). 2 Nannospalax species; vouchers NU 45 / NU 675.

### `TTU-M` (2 sp.)

- **Priority:** P4b-easy-alias
- **Issue:** alias
- **On map via shorter code:** 2
- **Completely unmatched:** 0
- **Related metadata:** TTU
- **Examples:** Lepilemur_hollandorum; Cheirogaleus_grovesi
- **Suggested action:** Add TTU-M alias row pointing to same institution as TTU.
- **Notes:** Likely alias for TTU (Texas Tech) mammal sub-collection.

### `UFRGS` (2 sp.)

- **Priority:** P4b-easy-alias
- **Issue:** alias
- **On map via shorter code:** 2
- **Completely unmatched:** 0
- **Related metadata:** UF
- **Examples:** Ctenomys_lami; Ctenomys_flamarioni
- **Suggested action:** Add UFRGS alias row pointing to same institution as UF.
- **Notes:** Likely Universidade Federal do Rio Grande do Sul — do not alias to UF (Florida). Needs new UFRGS row.

### `ZSIS` (2 sp.)

- **Priority:** P4b-easy-alias
- **Issue:** alias
- **On map via shorter code:** 2
- **Completely unmatched:** 0
- **Related metadata:** ZSI
- **Examples:** Myotis_himalaicus; Glischropus_meghalayanus
- **Suggested action:** Add ZSIS alias row pointing to same institution as ZSI.
- **Notes:** Likely alias for ZSI (Zoological Survey of India).

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

### `GNMT` (4 sp.)

- **Priority:** P4c-orphan-high
- **Issue:** orphan
- **On map via shorter code:** 0
- **Completely unmatched:** 4
- **Related metadata:** —
- **Examples:** Microtus_transcaspicus; Nannospalax_nehringi; Microtus_schelkovnikovi
- **Suggested action:** Research institution for GNMT; add new metadata row if confirmed.
- **Notes:** Possibly Georgian National Museum (Tbilisi)? Metadata has SGMT (State Georgian Museum).

### `KM` (4 sp.)

- **Priority:** P4c-orphan-high
- **Issue:** orphan
- **On map via shorter code:** 0
- **Completely unmatched:** 4
- **Related metadata:** —
- **Examples:** Petromyscus_barbouri; Cryptochloris_zyli; Chrysochloris_visagiei
- **Suggested action:** Research institution for KM; add new metadata row if confirmed.
- **Notes:** Voucher prefix not in metadata; no related abbreviation detected.

### `MMUS` (4 sp.)

- **Priority:** P4c-orphan-high
- **Issue:** orphan
- **On map via shorter code:** 0
- **Completely unmatched:** 4
- **Related metadata:** —
- **Examples:** Dendrolagus_dorianus; Petrogale_assimilis; Dorcopsulus_macleayi
- **Suggested action:** Research institution for MMUS; add new metadata row if confirmed.
- **Notes:** Metadata lists MMUS as synonym on MAMU (Macleay Museum, Sydney). Vouchers still unmatched — verify prefix.

### `UANT` (4 sp.)

- **Priority:** P4c-orphan-high
- **Issue:** orphan
- **On map via shorter code:** 0
- **Completely unmatched:** 4
- **Related metadata:** —
- **Examples:** Laephotis_robertsi; Voalavo_antsahabensis; Scotophilus_tandrefana
- **Suggested action:** Research institution for UANT; add new metadata row if confirmed.
- **Notes:** Voucher prefix not in metadata; no related abbreviation detected.

### `ULPS` (4 sp.)

- **Priority:** P4c-orphan-high
- **Issue:** orphan
- **On map via shorter code:** 0
- **Completely unmatched:** 4
- **Related metadata:** —
- **Examples:** Avahi_meridionalis; Avahi_peyrierasi; Avahi_ramanantsoavani
- **Suggested action:** Research institution for ULPS; add new metadata row if confirmed.
- **Notes:** Voucher prefix not in metadata; no related abbreviation detected.

### `ZMNTU` (4 sp.)

- **Priority:** P4c-orphan-high
- **Issue:** orphan
- **On map via shorter code:** 0
- **Completely unmatched:** 4
- **Related metadata:** —
- **Examples:** Murina_gracilis; Harpiola_isodon; Murina_bicolor
- **Suggested action:** Research institution for ZMNTU; add new metadata row if confirmed.
- **Notes:** Voucher prefix not in metadata; no related abbreviation detected.

### `AHNU` (3 sp.)

- **Priority:** P4c-orphan-medium
- **Issue:** orphan
- **On map via shorter code:** 0
- **Completely unmatched:** 3
- **Related metadata:** —
- **Examples:** Parablarinella_latimaxillata; Uropsilus_huanggangensis; Mesechinus_orientalis
- **Suggested action:** Research institution for AHNU; add new metadata row if confirmed.
- **Notes:** Anhui Normal University (China). Related AHUB already in metadata with zero matches.

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

### `SCNU` (3 sp.)

- **Priority:** P4c-orphan-medium
- **Issue:** orphan
- **On map via shorter code:** 0
- **Completely unmatched:** 3
- **Related metadata:** —
- **Examples:** Crocidura_zhadaensis; Crocidura_medogensis; Typhlomys_fengjiensis
- **Suggested action:** Research institution for SCNU; add new metadata row if confirmed.
- **Notes:** South China Normal University (China).

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
