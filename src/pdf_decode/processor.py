from pathlib import Path
from datetime import datetime
from typing import Optional
from .extract import extract_layout
from .parser import parse_header
from .table import find_table_header, extract_table_rows
from .schema import Invoice, Supplier, Totals, InvoiceLine

class InvoiceProcessor:
    def process(self, pdf_path: Path) -> Optional[Invoice]:
        # 1. Extract Layout
        pages_data = extract_layout(pdf_path)
        if not pages_data:
            return None

        # 2. Parse Header
        header_data = parse_header(pages_data)
        
        # 3. Parse Table
        lines = []
        table_header = None
        
        # Try to find header on first page
        if pages_data:
            table_header = find_table_header(pages_data[0]['words'])
        
        if table_header:
            row_counter = 1
            for i, page in enumerate(pages_data):
                words = page['words']
                
                # Check if this page has its own header (e.g. repeated header)
                page_header = find_table_header(words)
                
                if page_header:
                    current_header = page_header
                    start_y = None # Use header bottom
                elif i > 0:
                    # Use first page header definition but start from top
                    current_header = table_header
                    start_y = 0
                else:
                    # First page, use found header
                    current_header = table_header
                    start_y = None
                    
                raw_rows = extract_table_rows(words, current_header, start_y=start_y)
                
                for r in raw_rows:
                    lines.append(InvoiceLine(
                        rad=row_counter,
                        artikelnr=r.get('artikelnr'),
                        benamning=r.get('benamning'),
                        antal=r.get('antal'),
                        enhet=r.get('enhet'),
                        a_pris=r.get('a_pris'),
                        summa=r.get('summa')
                    ))
                    row_counter += 1
        
        # 4. Construct Invoice Object
        invoice = Invoice(
            source_file=pdf_path.name,
            extracted_at=datetime.now().isoformat(),
            fakturanummer=header_data.get('fakturanummer'),
            fakturadatum=header_data.get('fakturadatum'),
            forfallodatum=header_data.get('forfallodatum'),
            ocr_nummer=header_data.get('ocr_nummer'),
            referens=header_data.get('referens'),
            referenser=header_data.get('referenser'),
            supplier=Supplier(
                namn=header_data.get('supplier_name'),
                orgnr=header_data.get('supplier_orgnr'),
                vat_nr=header_data.get('supplier_vat'),
                adress=header_data.get('supplier_address'),
                bankgiro=header_data.get('supplier_bankgiro'),
                plusgiro=header_data.get('supplier_plusgiro'),
                part_id=header_data.get('supplier_part_id'),
                kontakt=header_data.get('supplier_kontakt'),
                email=header_data.get('supplier_email'),
                telefon=header_data.get('supplier_telefon'),
            ),
            totals=Totals(
                totalsumma=header_data.get('totalsumma'),
                moms_belopp=header_data.get('moms_belopp'),
                delsumma_exkl_moms=header_data.get('delsumma_exkl_moms')
            ),
            lines=lines,
            raw_extraction=header_data # Store raw header data for debugging
        )
        
        return invoice
