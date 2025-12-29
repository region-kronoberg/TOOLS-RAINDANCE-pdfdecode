ANCHORS = {
    "fakturanummer": ["fakturanummer", "fakturanr", "faktura nr", "invoice no"],
    "fakturadatum": ["fakturadatum", "faktura datum", "invoice date", "datum"],
    "forfallodatum": ["forfallodatum", "forfallodag", "due date", "betalas senast"],
    "ocr": ["ocr ref", "ocr", "ocr nummer", "ocr nr", "referens nr"],
    "totalsumma": ["att betala", "totalsumma", "summa att betala", "belopp att betala"],
    "moms": ["varav moms", "total moms", "momsbelopp"],
    "delsumma": ["summa exkl moms", "delsumma", "nettobelopp"],
    "bankgiro": ["bankgiro", "bg"],
    "plusgiro": ["plusgiro", "pg"],
    "orgnr": ["organisationsnummer", "org nr"],
    "vat": ["vat nr", "momsreg nr", "vat no"],
    "referens": ["er referens", "var referens", "referens"],
    "referenser": ["referenser"],
    "fakturaperiod": ["fakturaperiod", "period"],
    "part_id": ["partid", "part id"],
    "kontakt": ["kontakt", "contact"],
    "email": ["email", "e-mail", "e-post", "epost"],
    "telefon": ["telefon", "tel", "phone", "tfn"]
}

HEADER_KEYWORDS = {
    "artikelnr": ["artikelnr", "art.nr", "artikel"],
    "benamning": ["benamning", "beskrivning", "text", "specifikation"],
    "antal": ["antal", "ant", "kvantitet"],
    "enhet": ["enhet", "enh"],
    "a_pris": ["a pris", "pris", "enhetspris", "a'pris", "á pris", "à pris"],
    "summa": ["summa", "belopp", "totalt"]
}

# Tolerances
LINE_Y_TOLERANCE = 5
