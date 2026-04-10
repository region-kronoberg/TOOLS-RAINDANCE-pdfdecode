# Release Notes

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
