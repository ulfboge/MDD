# Metodik och resultat

Vi lade först upp och granskade CSV-filen med typmaterial. Filen innehåller 54 rader, nästan alla med brasilianiska typlokaliteter och samlingar från **Museu Nacional, Universidade Federal do Rio de Janeiro** (Rio de Janeiro, Brasilien). Den enda avvikande raden använder prefixet **“MN-UFRJ”**, vilket också hänvisar till samma museum. Detta bekräftas av auktoritativa källor: såväl Zoologiska Institutet (American Museum Novitates) som samlingsdatabaser anger att *“MN”* betyder *“Museu Nacional, Universidade Federal do Rio de Janeiro, Rio de Janeiro, Brazil”*【31†L246-L248】, och portugiskspråkig information om museets samlingar stöder detta【23†L36-L43】. 

Vi identifierade således följande unika museiförkortningar i filen:

- **MN** – fullständig namn “Museu Nacional, Universidade Federal do Rio de Janeiro”, beläget i **Rio de Janeiro, Brasilien**. Institutionens standardkod anges ibland som *MNRJ* eller helt enkelt *MN*. Källor: publicerad typmateriallista【31†L246-L248】, OBIS-datablad【23†L36-L43】 m.fl. *Säkerhet: hög*. (Observera att Monodelphis pinocchio *(MN 78680)* i ursprungsartikeln anges med “MN”【31†L246-L248】; enstaka felaktiga referenser till AMNH är felaktiga.)
- **MN-UFRJ** – samma institution (“Museu Nacional, Universidade Federal do Rio de Janeiro, Rio de Janeiro, Brasilien”), där ”UFRJ” förtydligar universitetstilknytningen. Givet att källor anger *MN* för Museu Nacional, tolkas ”MN-UFRJ” som ett äldre alias för samma museum. *Säkerhet: hög*.

Det finns inga andra förkortningar i filen, och alla prefix kunde entydigt kopplas till Museu Nacional (UFRJ). Ingen förkortning förblev oidentifierad eller flertydig efter denna genomgång.

Vi uppdaterade sedan CSV-filen genom att lägga till kolumnerna **museum_full_name**, **museum_city**, **museum_country**, **institution_code**, **confidence** och **source_url**. För varje rad är värdena (för båda prefix “MN” och “MN-UFRJ”) satta till exempelvis *“Museu Nacional, Universidade Federal do Rio de Janeiro”*, *“Rio de Janeiro”*, *“Brazil”*, kod “MN (alternativt MNRJ)”, *“Hög”*, och källhänvisningarna ovan.

Nedan ges en tabell med varje identifierad förkortning och dess matchning:

| Förkortning | Fullständigt namn                                        | Stad         | Land     | Institutionkod         | Säkerhet  | Källor                     |
|-------------|----------------------------------------------------------|--------------|----------|------------------------|-----------|----------------------------|
| MN          | Museu Nacional, Universidade Federal do Rio de Janeiro    | Rio de Janeiro | Brasilien | MN (alternativt MNRJ) | Hög       | 【31†L246-L248】【23†L36-L43】 |
| MN-UFRJ     | Museu Nacional, Universidade Federal do Rio de Janeiro    | Rio de Janeiro | Brasilien | MN (alternativt MNRJ) | Hög       | 【31†L246-L248】【23†L36-L43】 |

## Sammanfattning och rekommendationer

Vi har därmed kunnat lösa *alla* förkortningar i tabellen. Både *MN* och *MN-UFRJ* hänvisar entydigt till **Museu Nacional (UFRJ)** i Rio de Janeiro, med hög säkerhet baserat på flertalet primära källor【31†L246-L248】【23†L36-L43】. Inga resterande tvetydigheter återstår. I analysen bekräftades även att arten *Monodelphis pinocchio* (typholotyp **MN 78680**) faktiskt hör till Museet (ej AMNH) enligt Pavan et al. 2015【31†L246-L248】. 

**Rekommendationer:** För fullständighetens skull bör nya datauppsättningar standardisera ”MN” som kod för Museu Nacional – eventuellt notera alternativa kodnamn som *MNRJ*. Inga ytterligare ambiguiteter observerades här. 

## Uppdaterad CSV (exempel)

Nedan visas struktur på den uppdaterade CSV-filen (samma rader som ursprungsfilen, med extra kolumner längst till höger). Exempel på några rader (övriga följer samma mönster):

```csv
sci_name,sci_name_space,main_common_name,order,family,genus,type_voucher,type_kind,type_locality,type_lat,type_lon,museum_full_name,museum_city,museum_country,institution_code,confidence,source_url
Abrawayaomys_ruschii,Abrawayaomys ruschii,Ruschi's Spiny Mouse,Rodentia,Cricetidae,Abrawayaomys,MN-UFRJ 23075,holotype,"Forno Grande ..., Brasil", -20.50000,-41.6000,"Museu Nacional, Universidade Federal do Rio de Janeiro","Rio de Janeiro","Brazil","MN (alternativt MNRJ)","Hög","【31†L246-L248】【23†L36-L43】"
Akodon_mystax,Akodon mystax,Caparao Grass Mouse,Rodentia,Cricetidae,Akodon,MN 31910,holotype,"Arrozal ..., Brasil",,, "Museu Nacional, Universidade Federal do Rio de Janeiro","Rio de Janeiro","Brazil","MN (alternativt MNRJ)","Hög","【31†L246-L248】【23†L36-L43】"
...
```

*Källor:* Oficiella samlingsdatabaser och originalpublikationer, t.ex. Pavan et al. 2015 (AMNH Novitates)【31†L246-L248】 och OBIS (Museu Nacional)【23†L36-L43】. Dessa anger klart att *MN* hänvisar till Museu Nacional, UFRJ, Rio, Brasilien. All text är översatt/sammanställd på svenska där så behövdes.