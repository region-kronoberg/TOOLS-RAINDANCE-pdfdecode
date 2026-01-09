from typing import List, Dict, Any, Optional
from .utils import normalize_text, parse_swedish_date, parse_swedish_amount, parse_bankgiro, parse_plusgiro
from .geometry import group_words_by_line
from .constants import ANCHORS, LINE_Y_TOLERANCE
import re

def find_all_anchors(words: List[Dict[str, Any]], anchor_keys: List[str]) -> List[Dict[str, Any]]:
    """
    Finds all occurrences of anchors. Returns a list of anchor words (last word of the phrase), sorted by Y position.
    """
    found_anchors = []
    lines = group_words_by_line(words, tolerance=LINE_Y_TOLERANCE)
    sorted_y = sorted(lines.keys())
        
    for y in sorted_y:
        line_words = lines[y]
        line_words.sort(key=lambda w: w['x0'])
        
        # Build both normalized text and raw text mappings
        full_text = ""
        full_raw_text = ""
        
        word_map = [] # start, end (normalized)
        raw_word_map = [] # start, end (raw)
        
        for w in line_words:
            # Normalized construction
            nt = normalize_text(w['text'])
            if nt: 
                start = len(full_text)
                if start > 0:
                    full_text += " "
                    start += 1
                full_text += nt
                end = len(full_text)
                word_map.append((start, end, w))
            
            # Raw construction - use exact text but join with space
            rt = w['text']
            raw_start = len(full_raw_text)
            if raw_start > 0:
                full_raw_text += " "
                raw_start += 1
            full_raw_text += rt
            raw_end = len(full_raw_text)
            raw_word_map.append((raw_start, raw_end, w))

        for key in anchor_keys:
            # Check if key requires raw matching (contains punctuation or upper case)
            use_raw = any(c.isupper() for c in key) or not key.isalnum()
            # If standard normalization removes necessary chars (like colon), force raw
            if ":" in key:
                use_raw = True
            
            target_text = full_raw_text if use_raw else full_text
            target_map = raw_word_map if use_raw else word_map
            
            # If raw matching, we might not want \b boundaries if key ends with symbol
            if use_raw:
                # Use simple string search or regex without boundaries if needed
                # For "Bankgiro:", just search literal string
                try:
                    # Find all occurrences
                    start_idx = 0
                    while True:
                        idx = target_text.find(key, start_idx)
                        if idx == -1:
                            break
                        
                        m_end = idx + len(key)
                        
                        # Find matched word
                        target_word = None
                        for start, end, w in target_map:
                            if start <= (m_end - 1) < end:
                                 target_word = w
                                 break
                        
                        if target_word:
                            found_anchors.append(target_word)
                        
                        start_idx = idx + 1
                except Exception:
                     pass
            else:
                # Standard normalized regex search
                pattern = r'\b' + re.escape(key) + r'\b'
                for match in re.finditer(pattern, full_text):
                    m_end = match.end()
                    target_word = None
                    for start, end, w in word_map:
                        if start <= (m_end - 1) < end:
                             target_word = w
                             break
                    
                    if target_word:
                        found_anchors.append(target_word)
                    else: 
                        # Fallback logic for safety
                        last_key_part = key.split()[-1]
                        for word in line_words:
                             if normalize_text(word['text']) == last_key_part:
                                 found_anchors.append(word)
                                 break
    return found_anchors

def find_anchor(words: List[Dict[str, Any]], anchor_keys: List[str], strategy: str = "first") -> Optional[Dict[str, Any]]:
    anchors = find_all_anchors(words, anchor_keys)
    if not anchors:
        return None
    
    if strategy == "last":
        return anchors[-1]
    return anchors[0]


def get_text_right_of(words: List[Dict[str, Any]], anchor: Dict[str, Any], max_dist: float = 300, max_word_gap: float = 60) -> str:
    """
    Gets text to the right of the anchor on the same line (approximate Y).
    Stops if a gap between words exceeds max_word_gap.
    """
    line_y_center = (anchor['top'] + anchor['bottom']) / 2
    candidates = []
    
    for word in words:
        # Check if on same line (y overlap)
        word_y_center = (word['top'] + word['bottom']) / 2
        if abs(word_y_center - line_y_center) < LINE_Y_TOLERANCE:
            # Check if to the right
            if word['x0'] > anchor['x1'] and (word['x0'] - anchor['x1']) < max_dist:
                candidates.append(word)
                
    candidates.sort(key=lambda w: w['x0'])
    
    if not candidates:
        return ""

    # Filter by gap
    result_words = []
    last_x1 = anchor['x1']
    
    for word in candidates:
        gap = word['x0'] - last_x1
        if gap > max_word_gap:
            break
        result_words.append(word)
        last_x1 = word['x1']
        
    return " ".join([w['text'] for w in result_words])

def get_text_below(words: List[Dict[str, Any]], anchor: Dict[str, Any], max_dist_y: float = 50, max_width: float = 200, multiline: bool = False) -> str:
    """
    Gets text below the anchor.
    """
    target_words = []
    for word in words:
        # Check if below
        if word['top'] > anchor['bottom'] and (word['top'] - anchor['bottom']) < max_dist_y:
            # Check horizontal alignment (roughly within anchor's x range or slightly wider)
            # Increased left tolerance to catch words that start before the anchor's last word
            # Especially for multi-word anchors where the value aligns with the start of the anchor
            if word['x0'] >= (anchor['x0'] - 100) and word['x1'] <= (anchor['x1'] + max_width):
                target_words.append(word)
    
    # Sort by Y then X
    target_words.sort(key=lambda w: (w['top'], w['x0']))
    
    if not target_words:
        return ""
        
    # Group by line
    lines_dict = group_words_by_line(target_words, tolerance=LINE_Y_TOLERANCE)
    
    # Sort lines by Y
    sorted_lines = sorted(lines_dict.items(), key=lambda x: x[0])
    raw_lines = [line for _, line in sorted_lines]
    
    # Filter lines based on indentation consistency if multiline
    lines = []
    if raw_lines:
        # First line sets the standard
        first_line = raw_lines[0]
        first_line.sort(key=lambda w: w['x0'])
        ref_x = first_line[0]['x0']
        lines.append(first_line)
        
        for line in raw_lines[1:]:
             line.sort(key=lambda w: w['x0'])
             curr_x = line[0]['x0']
             
             # If strict alignment is needed (multiline mode)
             # If the next line starts significantly to the left (e.g. > 40px), assume it belongs to another column
             if multiline and curr_x < (ref_x - 40):
                 break
             
             lines.append(line)
        
    result_lines: List[str] = []
    for line in lines:
        line_text = " ".join([w['text'] for w in line])
        
        # Check if line looks like a label (e.g. "Label:")
        # If it is a label, we should stop.
        # If it's the first line, it means the anchor has no value (it's followed by another label).
        is_label = False
        if ":" in line_text:
            prefix = line_text.split(":")[0].strip()
            # Check length and if it contains letters (to avoid timestamps like 12:00 being treated as labels)
            if len(prefix) < 40 and any(c.isalpha() for c in prefix):
                 is_label = True
        
        if is_label:
            if not result_lines:
                return ""
            else:
                break
             
        result_lines.append(line_text)
        
        if not multiline:
            break
            
    return ", ".join(result_lines)

def extract_supplier_info(words: List[Dict[str, Any]]) -> Dict[str, Optional[str]]:
    """
    Extracts supplier name and address by looking above the address block anchors.
    Returns a dict with 'name' and 'address'.
    """
    anchors = ["godkand for f skatt", "f skatt", "org nr", "momsreg nr"]
    found_anchor = None
    
    # Find the anchor
    for word in words:
        norm_text = normalize_text(word['text'])
        if any(a in norm_text for a in anchors):
            found_anchor = word
            break
            
    if not found_anchor:
        return {'name': None, 'address': None}
        
    # Look upwards in the left column
    x_min = 0
    x_max = 220 # Limit to left column
    y_limit = found_anchor['top']
    y_start = y_limit - 100 # Look up 100px
    
    candidates = []
    for word in words:
        if word['bottom'] < y_limit and word['top'] > y_start and word['x0'] >= x_min and word['x0'] < x_max:
            candidates.append(word)
            
    if not candidates:
        return {'name': None, 'address': None}
        
    # Group by line
    lines = group_words_by_line(candidates, tolerance=LINE_Y_TOLERANCE)
            
    if not lines:
        return {'name': None, 'address': None}
        
    sorted_y = sorted(lines.keys())
    
    # First line is name
    name_words = sorted(lines[sorted_y[0]], key=lambda w: w['x0'])
    name = " ".join([w['text'] for w in name_words])
    
    # Remaining lines are address
    address_parts = []
    for y in sorted_y[1:]:
        line_words = sorted(lines[y], key=lambda w: w['x0'])
        line_text = " ".join([w['text'] for w in line_words]).strip().rstrip(',')
        if line_text:
            address_parts.append(line_text)
        
    address = ", ".join(address_parts) if address_parts else None
    
    return {'name': name, 'address': address}

def parse_header(pages_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Parses header fields from the first page (usually).
    """
    if not pages_data:
        return {}
        
    first_page_words = pages_data[0]['words']
    result = {}
    
    # Helper to try finding a field
    def try_extract(field_key, parser_func=None, multiline=False, strategy="first", max_word_gap=60):
        candidates = find_all_anchors(first_page_words, ANCHORS.get(field_key, []))
        if strategy == "last":
            candidates = list(reversed(candidates))
            
        # First Pass: Try finding value to the RIGHT for ANY candidate
        # This prioritizes "Label: Value" format which is most reliable
        for anchor_word in candidates:
            # Try right first
            val_right = get_text_right_of(first_page_words, anchor_word, max_word_gap=max_word_gap)
            
            # If we have a parser function, check if the value is valid
            if val_right:
                if parser_func:
                    res = parser_func(val_right)
                    if res is not None:
                        return res
                else:
                    return val_right

        # Second Pass: If no value to right, try BELOW
        # Use strategy to pick which anchor to use (first or last)
        if candidates:
            primary_anchor = candidates[0]
            val_below = get_text_below(first_page_words, primary_anchor, multiline=multiline)
            
            if val_below and parser_func:
                res = parser_func(val_below)
                return res
            return val_below if val_below else None
        
        return None

    result['fakturanummer'] = try_extract('fakturanummer')
    result['fakturadatum'] = try_extract('fakturadatum', parse_swedish_date)
    result['forfallodatum'] = try_extract('forfallodatum', parse_swedish_date)
    result['ocr_nummer'] = try_extract('ocr')
    result['referens'] = try_extract('referens', multiline=True)
    result['referenser'] = try_extract('referenser')
    result['totalsumma'] = try_extract('totalsumma', parse_swedish_amount, strategy="last")
    result['moms_belopp'] = try_extract('moms', parse_swedish_amount, max_word_gap=120)
    result['delsumma_exkl_moms'] = try_extract('delsumma', parse_swedish_amount, max_word_gap=150)
    
    # Supplier info (often found via OrgNr or Bankgiro)
    supplier_info = extract_supplier_info(first_page_words)
    result['supplier_name'] = supplier_info['name']
    result['supplier_address'] = supplier_info['address']
    
    result['supplier_orgnr'] = try_extract('orgnr')
    result['supplier_bankgiro'] = try_extract('bankgiro', parse_bankgiro)
    result['supplier_plusgiro'] = try_extract('plusgiro', parse_plusgiro)
    result['supplier_vat'] = try_extract('vat')
    result['supplier_part_id'] = try_extract('part_id')
    result['supplier_kontakt'] = try_extract('kontakt')
    result['supplier_email'] = try_extract('email')
    result['supplier_telefon'] = try_extract('telefon')
    result['supplier_iban'] = try_extract('iban')
    result['supplier_bic'] = try_extract('bic')
    result['supplier_peppol_id'] = try_extract('peppol_id')

    return result
