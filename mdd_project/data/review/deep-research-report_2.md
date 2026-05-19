# Metodik och resultat

Vi läste in **mn_vouchers_for_review.csv** och identifierade unika prefix i kolumnen *type_voucher* (här: **MN** och **MN-UFRJ**). Alla rader är brasilianska typtyper från **Museu Nacional, Universidade Federal do Rio de Janeiro**. Vi kontrollerade officiella källor och samlingar: bland annat American Museum Novitates (Pavan 2015) bekräftar att förkortningen *MN* betyder *"Museu Nacional, Universidade Federal do Rio de Janeiro, Rio de Janeiro, Brazil"* ([Pavan et al. 2015, AMNH Novitates 3832](https://digitallibrary.amnh.org/server/api/core/bitstreams/9864b9ec-11a5-4018-819e-59f4053bc3ab/content)). OBIS-databladet för Museu Nacional beskriver likaså *"Museu Nacional, Universidade Federal do Rio de Janeiro"* (kod MNRJ) ([OBIS institute 13167](https://obis.org/institute/13167)).

Följande slutsatser drogs:

- *Prefix "MN" och "MN-UFRJ" avser samma institution (Museu Nacional, UFRJ, Rio de Janeiro, Brasilien)*. Enligt matchningsregeln (longest prefix) täcks "MN-UFRJ" redan av "MN", så ingen separat metadata behövs för *MN-UFRJ*.
- *Institutionskod:* Vi antecknar koden som **MN** (eller **MNRJ** i vissa sammanhang), med hög säkerhet baserat på källorna ovan.

Vi skapade en ny CSV-fil **mn_vouchers_for_review_enriched.csv** (sparad i repot) som har samma rader som originalet plus tillagda kolumner för museets fullständiga namn, stad, land, kod, säkerhetsgrad och källhänvisningar. Nedan visas exempel på filens struktur och ett par rader (resten följer samma mönster):

```csv
sci_name,sci_name_space,main_common_name,order,family,genus,type_voucher,type_kind,type_locality,type_lat,type_lon,museum_full_name,museum_city,museum_country,institution_code,confidence,source_url
Abrawayaomys_ruschii,Abrawayaomys ruschii,Ruschi's Spiny Mouse,Rodentia,Cricetidae,Abrawayaomys,MN-UFRJ 23075,holotype,"Forno Grande...,Brasil",-20.50000,-41.6000,"Museu Nacional, Universidade Federal do Rio de Janeiro","Rio de Janeiro","Brazil","MN (MNRJ)","Hög","https://digitallibrary.amnh.org/...; https://obis.org/institute/13167"
Akodon_mystax,Akodon mystax,Caparao Grass Mouse,Rodentia,Cricetidae,Akodon,MN 31910,holotype,"Arrozal...,Brasil",,,"Museu Nacional, Universidade Federal do Rio de Janeiro","Rio de Janeiro","Brazil","MN (MNRJ)","Hög","https://digitallibrary.amnh.org/...; https://obis.org/institute/13167"
...
```

## Slutsatser och rekommendationer

- **Datakvalitet:** Alla förkortningar i filen kunde entydigt kopplas till **Museu Nacional (UFRJ)** i Rio de Janeiro. Det finns inga återstående oidentifierade eller tvetydiga prefix. Genom att använda prefix-matchning (t.ex. `LIKE 'MN%'`) undviker vi felaktiga matchningar mot andra institutioner med kod "MN" (som Madrid eller MNHN, eftersom dessa har längre koder i databasen).
- **Referenser:** Källhänvisningar pekar på [Pavan et al. (2015)](https://digitallibrary.amnh.org/server/api/core/bitstreams/9864b9ec-11a5-4018-819e-59f4053bc3ab/content) och [OBIS/MNRJ](https://obis.org/institute/13167).
- **Implementerat:** `MN`-rad tillagd i `TypeSpecimenMetadata_v2.4.csv`; enriched CSV och audit-rapporter regenererade efter databasbygge.
- **Slutsats:** All typinformation i MN-filen är korrekt länkad till Museu Nacional, och källor är dokumenterade.

**Källor:** [Pavan et al. 2015, American Museum Novitates 3832](https://digitallibrary.amnh.org/server/api/core/bitstreams/9864b9ec-11a5-4018-819e-59f4053bc3ab/content); [OBIS — Museu Nacional UFRJ (MNRJ)](https://obis.org/institute/13167).
