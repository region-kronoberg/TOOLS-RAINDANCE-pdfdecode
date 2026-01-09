ANCHORS = {
    "fakturanummer": ["Fakturanummer:"],
    "fakturadatum": ["Fakturadatum:"],
    "forfallodatum": ["Förfallodatum:"],
    "ocr": ["OCR Ref:", "ocr", "ocr nummer", "ocr nr", "referens nr"],
    "totalsumma": ["att betala", "totalsumma", "summa att betala", "belopp att betala"],
    "moms": ["varav moms", "total moms", "momsbelopp"],
    "delsumma": ["summa exkl moms", "delsumma", "nettobelopp"],
    "bankgiro": ["Bankgiro:"],
    "plusgiro": ["plusgiro", "pg"],
    "orgnr": ["Org.nr:"],
    "vat": ["Momsreg.nr:"],
    "referens": ["Er referens:", "var referens", "referens"],
    "referenser": ["referenser"],
    "fakturaperiod": ["fakturaperiod", "period"],
    "part_id": ["PartID:"],
    "kontakt": ["Kontakt:"],
    "email": ["Email:", "e-mail", "e-post", "epost"],
    "telefon": ["Telefon:"],
    "iban": ["IBAN:"],
    "bic": ["BIC:"],
    "peppol_id": ["Peppol-ID:"]
}

HEADER_KEYWORDS = {
    "artikelnr": ["Artikelnr"],
    "benamning": ["Benämning"],
    "antal": ["Antal"],
    "enhet": ["enhet", "enh"], # Keep these as no header column found in example, might need adjustment
    "a_pris": ["A'pris"],
    "summa": ["Summa"]
}

# Tolerances
LINE_Y_TOLERANCE = 5
