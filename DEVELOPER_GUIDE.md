# Introduktion för nya utvecklare

## Vad är det här projektet?

`pdf-decode` är ett Python-verktyg som automatiskt läser AXT e-fakturor (PDF-filer producerade av Raindance/CGI) och konverterar dem till strukturerad JSON. Verktyget används av Region Kronoberg för att integrera fakturaflöden.

En PDF kan se ut hur som helst layoutmässigt, och parsern navigerar dokumentet spatialt – den letar efter text på specifika X/Y-koordinater snarare än att läsa rad för rad.

---

## Komma igång

```bash
git clone <repository-url>
cd TOOLS-RAINDANCE-pdfdecode

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

pip install -e .

# Testa mot en PDF
pdf-decode in/minfaktura.pdf -o out/
```

Utan installation (för lokal utveckling):
```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
python3 -m pdf_decode.cli in/ -o out/
```

Utökat loggläge för felsökning:
```bash
pdf-decode in/ -o out/ -vv   # DEBUG-nivå, visar fullständiga stacktraces
```

---

## Projektstruktur

```
src/pdf_decode/
├── cli.py          Ingångspunkt för kommandoraden (Click)
├── processor.py    Orkestrera hela parsningsflödet
├── extract.py      Läs in PDF med pdfplumber → lista av ord med koordinater
├── parser.py       Hitta och tolka header-fält (fakturanummer, datum, leverantör …)
├── table.py        Hitta tabellhuvud och extrahera fakturarader
├── geometry.py     Hjälpfunktioner för spatial/geometrisk logik (gruppera ord på rader, etc.)
├── constants.py    Konfiguration: ANCHORS och HEADER_KEYWORDS
├── schema.py       Pydantic-modeller som definierar JSON-schemat
└── utils.py        Texthjälpare: normalize_text, parse_swedish_amount, parse_swedish_date …

tests/
├── test_regression.py  Jämför parserns utdata mot sparad referens-JSON i out/before/
└── test_lint.py        Statisk kodanalys med ruff

in/                 Exempel-PDFer (testindata)
out/before/         Referens-JSON för regressionstester
```

---

## Dataflöde – steg för steg

```
PDF-fil
  │
  ▼
extract_layout()          [extract.py]
  │  pdfplumber läser varje sida och returnerar en lista med ord,
  │  där varje ord har: text, x0, top, x1, bottom
  │
  ▼
parse_header()            [parser.py]
  │  Letar efter "ankare" (nyckelord ur ANCHORS i constants.py),
  │  t.ex. "Fakturanummer:", och hämtar värdet som ligger
  │  till höger om eller under ankaret.
  │  Extraherar också leverantörsinformation, totalsummor och
  │  justeringar (frakt, rabatt, öresavrundning, etc.).
  │
  ▼
find_table_header()       [table.py]
  │  Hittar raden med kolumnrubriker (Rad, Artikelnr, Benämning …)
  │  genom att räkna hur många HEADER_KEYWORDS varje rad matchar.
  │
  ▼
extract_table_rows()      [table.py]
  │  Grupperar ord på rader och "snappar" numeriska värden
  │  till rätt kolumn baserat på X-koordinat.
  │
  ▼
Invoice (Pydantic)        [schema.py]
     Sammanfogar all data i ett validerat objekt och
     serialiserar till JSON med model_dump_json().
```

---

## Nyckelkoncept

### Spatial parsing
Parsern arbetar med koordinater, inte med radnummer. Funktionen `group_words_by_line` i `geometry.py` grupperar ord vars Y-koordinater ligger inom `LINE_Y_TOLERANCE` (5 px) av varandra till samma rad.

### Ankare (ANCHORS)
`constants.py` definierar vilka textsträngar som signalerar ett fält. T.ex.:
```python
"fakturanummer": ["Fakturanummer:", "Fakturanummer"]
```
Parser-koden söker igenom dokumentet efter dessa strängar och hämtar sedan värdet som befinner sig spatialt till höger om eller under ankaret.

### Tabellkolumner
`find_table_header` returnerar en dict med kolumnnamn → X-intervall, t.ex.:
```python
{"rad": (20, 50), "artikelnr": (50, 130), "benamning": (130, 350), ...}
```
Varje ord i en fakturarad tilldelas sedan den kolumn vars X-intervall ordet faller inom.

### Pydantic-modeller
All utdata valideras mot modellerna i `schema.py` (`Invoice`, `Supplier`, `InvoiceLine`, `Totals`, `Adjustment`). Monetära värden lagras som `Decimal` internt och serialiseras som `float` i JSON.

---

## Köra tester

```bash
# Alla tester
pytest

# Bara regressionstester
pytest tests/test_regression.py -v

# Linting
pytest tests/test_lint.py
```

Regressionstesterna kräver att det finns PDF-filer i `in/` med matchande referens-JSON i `out/before/`. Om en referens-JSON saknas hoppas testet automatiskt över.

För att uppdatera en referens-JSON efter en avsiktlig parsningsförändring:
```bash
pdf-decode in/faktura.pdf -o out/before/
```

---

## Lägga till stöd för ett nytt fältformat

1. **Nytt header-fält**: Lägg till etiketten i `ANCHORS` i `constants.py` och hämta värdet i `parse_header()` i `parser.py` med `find_anchor()` / `find_anchor_value()`.
2. **Ny tabellkolumn**: Lägg till kolumnrubriken i `HEADER_KEYWORDS` i `constants.py`. `find_table_header` och `extract_table_rows` hanterar resten automatiskt.
3. **Nytt JSON-fält**: Lägg till fältet i rätt Pydantic-modell i `schema.py` och populera det i `processor.py`.

---

## Beroenden

| Paket | Användning |
|---|---|
| `pdfplumber` | Extraherar ord och koordinater från PDF |
| `pydantic` | Datamodellering och JSON-serialisering |
| `click` | CLI-argument och -utskrift |
| `ruff` | Linting (dev-beroende) |

Python ≥ 3.9 krävs.
