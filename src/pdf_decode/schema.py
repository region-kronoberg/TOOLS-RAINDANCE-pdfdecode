from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

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
    rad: Optional[int] = None
    artikelnr: Optional[str] = None
    benamning: Optional[str] = None
    antal: Optional[float] = None
    enhet: Optional[str] = None
    a_pris: Optional[float] = None
    summa: Optional[float] = None

class Totals(BaseModel):
    delsumma_exkl_moms: Optional[float] = None
    moms_belopp: Optional[float] = None
    totalsumma: Optional[float] = None
    valuta: str = "SEK"

class Invoice(BaseModel):
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
    
    source_file: str
    extracted_at: str
    raw_extraction: Dict[str, Any] = Field(default_factory=dict)
