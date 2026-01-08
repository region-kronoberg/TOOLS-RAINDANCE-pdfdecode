from typing import List, Dict, Any, Optional
from .utils import normalize_text, parse_swedish_date, parse_swedish_amount
from .geometry import group_words_by_line
from .constants import ANCHORS, LINE_Y_TOLERANCE
import re

def find_anchor(words: List[Dict[str, Any]], anchor_keys: List[str], strategy: str = "first") -> Optional[Dict[str, Any]]:
    """
    Finds the anchor. Supports multi-word anchors by checking lines.
    Returns the LAST word of the matched anchor phrase.
    strategy: "first" (default) or "last" (finds the last occurrence on the page, useful for totals at bottom)
    """
    # Group by line
    lines = group_words_by_line(words, tolerance=LINE_Y_TOLERANCE)
            
    # Sort lines by Y
    sorted_y = sorted(lines.keys())
    if strategy == "last":
        sorted_y = list(reversed(sorted_y))
        
    for y in sorted_y:
        line_words = lines[y]
        line_words.sort(key=lambda w: w['x0'])
        
        # Build mapping from normalized line text back to words
        full_text = ""
        word_map = [] # list of (start, end, word_obj)
        
        for w in line_words:
            nt = normalize_text(w['text'])
            if not nt: continue 
            
            start = len(full_text)
            if start > 0:
                full_text += " "
                start += 1
            full_text += nt
            end = len(full_text)
            word_map.append((start, end, w))

        for key in anchor_keys:
            # Check if key is in line using word boundaries
            pattern = r'\b' + re.escape(key) + r'\b'
            match = re.search(pattern, full_text)
            if match:
                m_end = match.end()
                # Find the word that corresponds to the end of the match
                # Loop backwards to find the word that covers the last character of the match
                target_word = None
                for start, end, w in word_map:
                    if start <= (m_end - 1) < end:
                         target_word = w
                         break
                
                if target_word:
                    return target_word
                
                # Fallback: if we couldn't map (maybe logic error), keep old flawed logic logic?
                # Or try to find word containing last part?
                last_key_part = key.split()[-1]
                for word in line_words:
                     if normalize_text(word['text']) == last_key_part:
                         return word

    return None

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
    lines = [line for _, line in sorted_lines]
        
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
        anchor_word = find_anchor(first_page_words, ANCHORS.get(field_key, []), strategy=strategy)
        if anchor_word:
            # Try right first
            val_right = get_text_right_of(first_page_words, anchor_word, max_word_gap=max_word_gap)
            
            # If we have a parser function, check if the value is valid
            if val_right and parser_func:
                res = parser_func(val_right)
                if res is not None:
                    return res
                # If parsing failed, treat as if we didn't find anything right (unless we want to return raw text?)
                # But here we want to fallback to below if right is garbage (like "Varav moms")
                val_right = None
            elif val_right:
                return val_right

            # Try below if right failed or was empty
            val_below = get_text_below(first_page_words, anchor_word, multiline=multiline)
            
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
    result['supplier_bankgiro'] = try_extract('bankgiro')
    result['supplier_plusgiro'] = try_extract('plusgiro')
    result['supplier_vat'] = try_extract('vat')
    result['supplier_part_id'] = try_extract('part_id')
    result['supplier_kontakt'] = try_extract('kontakt')
    result['supplier_email'] = try_extract('email')
    result['supplier_telefon'] = try_extract('telefon')

    return result
