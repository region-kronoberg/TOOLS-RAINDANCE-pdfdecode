from decimal import Decimal
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_serializer

# Monetary values are stored as Decimal to avoid binary floating-point
# representation errors. They are serialized as JSON numbers (via float) so
# that existing consumers continue to receive numeric output. Internal Python
# code can rely on exact decimal arithmetic where needed (e.g. reconciling
# sum-of-lines against totals).

class Supplier(BaseModel):
    namn: Optional[str] = None
    orgnr: Optional[str] = None
    vat_nr: Optional[str] = None
    adress: Optional[str] = None
    bankgiro: Optional[str] = None
    plusgiro: Optional[str] = None
    iban: Optional[str] = None
    bic: Optional[str] = None
    peppol_id: Optional[str] = None
    part_id: Optional[str] = None
    kontakt: Optional[str] = None
    email: Optional[str] = None
    telefon: Optional[str] = None

class InvoiceLine(BaseModel):
    row_no: Optional[int] = None
    rad: Optional[str] = None
    artikelnr: Optional[str] = None
    benamning: Optional[str] = None
    antal: Optional[Decimal] = None
    enhet: Optional[str] = None
    a_pris: Optional[Decimal] = None
    summa: Optional[Decimal] = None

    @field_serializer('antal', 'a_pris', 'summa', when_used='json')
    def _ser_decimal(self, v: Optional[Decimal]) -> Optional[float]:
        return float(v) if v is not None else None

class Adjustment(BaseModel):
    typ: Optional[str] = None
    beskrivning: str
    belopp: Optional[Decimal] = None

    @field_serializer('belopp', when_used='json')
    def _ser_decimal(self, v: Optional[Decimal]) -> Optional[float]:
        return float(v) if v is not None else None

class Totals(BaseModel):
    delsumma_exkl_moms: Optional[Decimal] = None
    moms_belopp: Optional[Decimal] = None
    totalsumma: Optional[Decimal] = None
    oresavrundning: Optional[Decimal] = None
    valuta: str = "SEK"

    @field_serializer('delsumma_exkl_moms', 'moms_belopp', 'totalsumma', 'oresavrundning', when_used='json')
    def _ser_decimal(self, v: Optional[Decimal]) -> Optional[float]:
        return float(v) if v is not None else None

class Invoice(BaseModel):
    fakturatyp: str = "Faktura"
    fakturanummer: Optional[str] = None
    fakturadatum: Optional[str] = None # YYYY-MM-DD
    forfallodatum: Optional[str] = None # YYYY-MM-DD
    ocr_nummer: Optional[str] = None
    order_nr: Optional[str] = None
    referens: Optional[str] = None # Er referens
    referenser: Optional[str] = None # Referenser
    var_referens: Optional[str] = None
    
    supplier: Supplier = Field(default_factory=Supplier)
    lines: List[InvoiceLine] = Field(default_factory=list)
    totals: Totals = Field(default_factory=Totals)
    justeringar: List[Adjustment] = Field(default_factory=list)
    
    source_file: str
    extracted_at: str
    raw_extraction: Dict[str, Any] = Field(default_factory=dict)

    @field_serializer('raw_extraction', when_used='json')
    def _ser_raw(self, v: Dict[str, Any]) -> Dict[str, Any]:
        # raw_extraction is typed as Any, so Decimal values inside it would be
        # serialized as strings by default. Convert recursively to keep JSON
        # numeric form consistent with the typed monetary fields.
        def _conv(x: Any) -> Any:
            if isinstance(x, Decimal):
                return float(x)
            if isinstance(x, dict):
                return {k: _conv(val) for k, val in x.items()}
            if isinstance(x, list):
                return [_conv(i) for i in x]
            return x
        return _conv(v)
