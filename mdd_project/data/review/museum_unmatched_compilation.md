# Sammanställning: omatchade type vouchers (MDD)

**Datum:** 2026-05-20  
**Underlag:** `museum_vouchers_unmatched.csv` (genererad av `audit_museum_matching.py`), räkningar från `summarize_unmatched_vouchers.py`, samt projektets `TypeSpecimenMetadata_v2.4.csv`.

---

## 1. Nuläge i siffror

| Mått | Värde |
|------|------:|
| Rader i omatchade-listan | **435** arter |
| Arter med museiprefix som matchar metadata (i app-logiken) | 238 distinkta institutionskoder med träff |
| Helt omatchade vouchers (samma källa som ovan) | **435** |

Ungefär **85 %** av de omatchade raderna är **två texttaggar** som aldrig kommer att få museiprefix:

| Kategori (automatisk bucket) | Antal | Kommentar |
|------------------------------|------:|-----------|
| `untraced` | 234 | Ingen säker fysisk koppling |
| `lost` | 136 | Angiven som förstörd/saknad |
| **Summa** | **370** | Kräver *inte* fler rader i metadata för “match”, utan annan spårbarhet i källan |

---

## 2. Vad som redan gjorts i detta repo (metadata för prefix-matchning)

Matchningsregeln är i huvudsak: voucher börjar med institutionsförkortning (`LIKE abbreviation || '%'`). Därför “löser” man omatchade poster genom att lägga till **korrekt förkortning + institution** i `TypeSpecimenMetadata_v2.4.csv`, om vouchern verkligen är ett museikatalognummer.

### 2.1 Senaste omgångarna (konversation / commits på `main`)

- **Sju nya prefix:** GHENT, NMZ, UIS (kortform vid sidan av UIS-MHN-M), MMNH (Skopje), TAU, WHT, MUFAL — plus korrigerat visningsnamn för UIS-MHN-M (“La Colección…”).
- **IBE:** *Institute of Biodiversity and Ecology*, Zhengzhou University — verifierat mot primärkälla (Jiang et al. 2025, PMC11814535, holotyp IBE00300).

**Effekt:** “Completely unmatched vouchers” sjönk i auditen från **443 → 435** (åtta färre helt omatchade efter dessa rader; nettot kan skilja något om andrapartslistor räknats om mellan körningar).

### 2.2 Tidigare vågor i samma fil (ur `git log`)

Projektet har iterativt lagt till många prefix (urval): FCV, ZMVNU, MZUCV, Kuroda/YIO, NAMRU, NHRC, NMU, MN m.fl., samt flera “singleton”- och aliasfixar (se commits på `TypeSpecimenMetadata_v2.4.csv`). Detta är det som gör att **238** institutionskoder nu har minst en voucherträff i datan.

---

## 3. Varför listan *inte* kan “tömmas” med bara metadata

1. **`UNTRACED` / `LOST` (370 rader)**  
   Dessa strängar är **inte** museiförkortningar. Att lägga in “UNTRACED” som en institution skulle vara meningslöst i en musei-metadatafil.

2. **Narrativa / historiska vouchrar** (exempelvis “Buffon’s specimen”, “Seba pl. …”, “specimen illustrated by Sonnerat”, “Pennant's specimen”, samlarnamn, platshänvisning utan katalogkod).  
   De saknar ett **stabilt bokstavsprefix** som kan mappas 1:1 till ett arkiv.

3. **Interna fältkoder / okända format**  
   - Cheirogaleid-liknande taggar (`001y07hely` m.fl.)  
   - `XZ2023…` / `XZ2024…` (ser ut som projektinterna koder, inte publika museiprefix)  
   - `TAFO6.1`, `VG-Q1`, `K-EE-12-31` m.fl.

4. **Rening av matchningslogik**  
   Vissa poster **matchar fel** kortare prefix om man inte lägger in längre alias (se nedan). Det är ett *annat* problem än “saknad metadata”.

---

## 4. Kvarvarande “prefix-liknande” rader (~37 st)

Efter att buffertarna `UNTRACED`/`LOST` och övriga narrativa kategorier tagits bort återstår grovt **37** rader med **egenstående bokstavskoder** (en per prefix om inget annat anges). Full lista med prefix finns i `museum_unmatched_bucket_counts.txt`.

**Exempel på gruppering:**

| Typ | Exempel | Varför det ofta fastnar |
|-----|---------|-------------------------|
| Osäker tolkning / behöver primärkälla | CBK, IZEA, LARQ, MLZA, ASRU | Förkortningens institution är inte verifierad i denna genomgång eller är tvetydig (t.ex. kollision med annan MMNH-världen över). |
| Sannolikt institut men ej spårad till rad i CSV | UMRCNRS, UZDZ, PBS, PCM, … | Kräver källgranskning eller längre prefix i metadata. |
| Geografiskt / samlarnamn | TASHKENT, YEREVAN, STILLWATER, NEUHÄUSER, LAÂYOUNE, ĐULIĆ | Inte standardmuseumskoder i MDD-strängarna. |
| RGM / värdmuseum varierar | RGM (Leiden) — behöver ev. egen rad eller bättre strängformat | |
| Katalognummer med specialtecken | `MUHNAC/MB01/006000`, `RGM.444360` | Prefix-extrahering och `LIKE`-matchning gynnar enkla `ABBREV 123`-mönster. |

**OBS:** Efter IBE-posten matchar t.ex. *Uropsilus funiushanensis* (voucher `IBE 00300`) i databasen och ska inte finnas kvar i `museum_vouchers_unmatched.csv` när projektet byggts om från aktuell metadata.

---

## 5. Prefix som “nästan” matchar (alias-problem)

`museum_prefix_mismatch_cases.csv` listar vouchrar där ett **kortare** prefix i metadata träffar först (t.ex. `UF` före `UFRO`, `MN` före `MNHB`, `AM` före `AMA`). Dessa är **inte** samma som “helt omatchade”, men påverkar rätt museitilldelning.

**Åtgärd:** lägg till **längre** institutionsförkortningar där det är vetenskapligt korrekt, eller förbättra extraktionen av prefix — inte bara fler ospecificerade rader.

---

## 6. Verktyg för uppföljning

| Fil / skript | Syfte |
|--------------|--------|
| `mdd_project/scripts/audit_museum_matching.py` | Huvudrapport + `museum_vouchers_unmatched.csv` |
| `mdd_project/scripts/audit_museum_excluded.py` | “Inget prefix alls”-lista |
| `mdd_project/scripts/summarize_unmatched_vouchers.py` | Bucket-räkning → `museum_unmatched_bucket_counts.txt` |
| `museum_voucher_prefixes_missing_from_metadata.csv` | Aggregat per prefix mot metadata |

**Körordning efter ändring i metadata:**  
`setup_database.py --skip-exports` → `audit_museum_matching.py` → vid behov `audit_museum_excluded.py` / `summarize_museum_gaps.py`.

---

## 7. Sammanfattning

| | |
|---|--:|
| **Gjort** | Successiv utökning av `TypeSpecimenMetadata_v2.4.csv` med verifierade prefix (senast bl.a. GHENT, NMZ, UIS, MMNH, TAU, WHT, MUFAL, IBE); rapportfiler uppdateras via audit-skript. |
| **Går inte** att lösa enbart med “fler museirader” | **~370** poster dominerade av `UNTRACED`/`LOST` + narrativa/historiska strängar. |
| **Kvar** | ~**37** “prefix-aktiga” singletons + alias-/matchningsproblem + ev. förbättrad prefix-logik för icke-standard strängar. |

Denna fil är avsedd som **arbetsdokument**; uppdatera datum och kör skripten när listorna ändras.
