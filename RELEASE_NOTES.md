# Release Notes

## v1.1.7 (2026-05-11)

### Felrättningar
*   **Spökbelopp i artikelrader med långa serialnummersträngar**: När `pdfplumber` extraherade en lång kommaseparerad serialnummersträng (t.ex. `2603N2635,2603N2636,...`) som ett enda ord svämmar texten utanför sidan (`x1 > 980 pt`). Det geometriska centret hamnade då i summa-kolumnen, och `parse_swedish_amount` hittade ett falskt belopp inuti strängen (t.ex. `2635,26`). Resultatet var en felaktig spökrad med ett bråktalsvärde i `summa` och att artikelns fortsättningsrader inte slogs ihop korrekt. Ord bredare än 700 pt tilldelas nu kolumn baserat på vänsterkant (`x0`) istället för centret.

## v1.1.6 (2026-05-04)

### Felrättningar
*   **Justeringar med flerrads-beskrivning**: Avgifter/rabatter vars namn bryts över flera rader (t.ex. `"Drivmedelstillägg**, Paket (momssats 25%)"`) slås nu ihop till en enda post med korrekt beskrivning och belopp. Tidigare skapades felaktiga delposter där t.ex. `"Paket (momssats"` tolkades som en separat justering med beloppet 25,00.
*   **Striktare beloppstolkning i justeringssektionen**: Tokens som innehåller bokstäver, `%`, `)` eller andra icke-numeriska tecken avvisas nu direkt som beloppskandidater, innan `parse_swedish_amount` anropas. Tidigare kunde `25%` tolkas som beloppet 25,00.

### Förbättringar
*   **Förbättrad CLI-felhantering**: Nytt flagga `-v`/`-vv` för att styra loggnivå (INFO/DEBUG) med fullständiga stack traces vid fel. Felmeddelanden skrivs nu till stderr. Utdatakatalogen skapas rekursivt (`mkdir -p`). Filer sorteras för deterministisk körningsordning. Avslutar med exitkod 1 om någon fil misslyckades.
*   **Monetära värden som `Decimal`**: Alla belopps­fält (`a_pris`, `summa`, `moms_belopp`, `totalsumma` m.fl.) lagras nu internt som `Decimal` istället för `float` för att undvika binär flyttalsavrundning. JSON-utdata är oförändrad (numeriska värden).
*   **Developer Guide**: Lade till `DEVELOPER_GUIDE.md` med arkitekturöversikt, konventioner och vägledning för att lägga till stöd för nya fakturaformat.

## v1.1.5 (2026-04-28)

### Felrättningar
*   **Felaktig tilldelning av siffror till `artikelnr`**: Siffror och `/` som förekommer *inuti* en artikelbeskrivning (t.ex. `"FS LIBRE 2 PLUS …"`) tilldelades felaktigt `artikelnr` i stället för att stanna i `benamning`. Gränsen för omplacering gäller nu bara när `benamning` ännu inte påbörjats på raden.

## v1.1.4 (2026-04-23)

### Felrättningar
*   **Justeringar i nytt fakturaformat**: Avgifter/Rabatter som i det nya formatet placerats i mittenkolumnen (t.ex. `Summa Legeringstillägg 26,06` och `RÅVARUTILLÄGG 14,07`) extraheras nu korrekt. Tidigare sattes sökområdets nedre gräns precis under rubriken "Avgifter" eftersom ordet "Summa" i raden `Summa Legeringstillägg` matchade mot tabellens kolumnrubrik. Tabellhuvudet detekteras nu som en rad som innehåller minst tre distinkta kolumnrubriker (t.ex. Rad + Artikelnr + Benämning), istället för att stoppa vid ett enskilt tvetydigt ord.

## v1.1.3 (2026-04-21)

### Felrättningar
*   **Negativa belopp i tabellrader**: Rader med negativa värden (t.ex. kreditrader/introduktionsavdrag som `-4,00 HUR` och `-2 860,00`) tolkas nu korrekt. Tidigare placerades minustecknet i fel kolumn – `antal` blev `null`, minustecknet hamnade i `benamning` och `summa` fick fel tecken. `_is_numeric_text` i `table.py` accepterar nu ledande och eftersläpande minustecken, så snap-logiken för numeriska kolumner fungerar även för negativa tal.

## v1.1.2 (2026-04-10)

### Felrättningar
*   **Filtrering av info-rader med enbart a_pris**: Rader som enbart innehåller ett `a_pris`-värde (utan summa, antal eller text) tolkas nu som informationsrader (t.ex. rabattinfo på OK-Q8-fakturor) och filtreras bort istället för att generera tomma fakturarader.
*   **Sidfotsdetektering**: Sidnummer på formatet "1/6" hanteras nu korrekt som sidfot, utan att felaktigt matcha batchnummer som "286/2511192".
*   **Justeringar begränsas av sektionsgränser**: Sökområdet för justeringar (t.ex. "Frakt", "Öresavrundning") stoppas nu även vid sektioner som "Notering" och "Betalningsvillkor" för att undvika felaktiga träffar.

### Förbättringar
*   **Förbättrad radgruppering**: `group_words_by_line` använder nu närmaste matchning istället för första träff, vilket ger korrekta rader när textlinjer ligger nära varandra.
*   **Robustare ankarmatchning**: Refaktorerad `find_all_anchors` med tvåstegs-strategi – rå substrängsökning för formatspecifika etiketter (t.ex. "Bankgiro:") och normaliserad ordgränssökning för generiska nycklar (t.ex. "referens"). Förhindrar felaktiga delträffar.
*   **Leverantörsextrahering**: `extract_supplier_info` använder nu `find_anchor` för konsekvent fras-matchning av ankarord som "Godkänd för F-skatt" och "Org.nr:".
*   **Refaktorering av tabellparsning**: Extraherat hjälpfunktioner (`_snap_numeric_to_column`, `_resolve_article_description_boundary`, `_fix_interleaved_chars`, `_parse_row_numerics`, `_is_table_footer`) och ersatt magiska tal med namngivna konstanter.

### Övrigt
*   Lade till regressionstester som jämför parserns utdata mot referens-JSON.
*   Ersatte `print`-debug med `logging`.

## v1.1.1 (2026-03-15)

### Felrättningar
*   **Förbättrad parsning av justeringar**: Åtgärdat flera problem i `extract_adjustments`-funktionen som ledde till felaktig eller utebliven extrahering av justeringsrader.
    *   Beloppsparser hanterar nu korrekt belopp med mellanslag som tusentalsseparator (t.ex. "198 727,50"), genom att kombinera på varandra följande numeriska tokens.
    *   Sökområdets högra gräns beräknas nu dynamiskt utifrån nästa kolumnhuvud på samma rad, vilket minskar risken att text från angränsande kolumner plockas in.
    *   Sökområdets nedre gräns begränsas nu korrekt av tabellens rubrikrad och nästkommande justeringshuvud, så att rader inte "läcker" in i fel sektion.
*   **Schema**: Fältet `belopp` i `Adjustment`-modellen är nu valfritt (`Optional[float]`), vilket förhindrar valideringsfel för justeringsrader där beloppet inte kan tolkas.

## v1.1.0 (2026-03-05)

### Förbättringar
*   **Stöd för ny fakturalayout**: Uppdaterat tolkningslogiken för att hantera fakturor där huvudinformationen (header) är placerad högre upp på sidan.
    *   Detta åtgärdar specifikt problem med extrahering av fält för leverantörer som **OneMed** och **Linde Gas**.
    *   Generella justeringar i `parser.py` för att hitta ankartexter och värden mer robust.
*   **CI/CD**: Uppdaterat GitHub pipelines för build och release-hantering.


## v1.0.6 (2026-02-03)

### Nya funktioner
*   **Detektering av fakturatyp**: Lade till logik för att avgöra om dokumentet är en debetfaktura eller kreditfaktura.
    *   Nytt fält `fakturatyp` i JSON-utdatan (värden: "Faktura" eller "Kreditfaktura").
    *   Systemet skannar nu första sidan efter texten "Kreditfaktura" och sätter fältet därefter.

### Övrigt
*   Lade till förbättrade typannoteringar för `parse_header`-funktionen för ökad kodtydlighet och underhållbarhet.
