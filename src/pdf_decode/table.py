from typing import List, Dict, Any, Optional
import re
from .utils import parse_swedish_amount
from .geometry import group_words_by_line
from .constants import HEADER_KEYWORDS, LINE_Y_TOLERANCE

def find_table_header(words: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Finds the Y-coordinate and column mapping of the table header.
    Returns a dict with 'top', 'bottom', and 'columns' (mapping name -> x_range).
    """
    # Group words by line (approximate Y)
    lines = group_words_by_line(words, tolerance=LINE_Y_TOLERANCE)
            
    # Check each line for header keywords
    best_line = None
    max_matches = 0
    
    for y, line_words in lines.items():
        matches = 0
        # Check against raw text line for strict matching if needed, 
        # or normalize if variants are loosely defined.
        # Current HEADER_KEYWORDS are strict: ["Artikelnr"], ["Benämning"] etc.
        # So we should match against raw words.
        
        line_raw_words = [w['text'] for w in line_words]
        
        for key, variants in HEADER_KEYWORDS.items():
            for var in variants:
                # Exact match against any word in the line
                if var in line_raw_words:
                    matches += 1
                    break
        
        if matches > max_matches:
            max_matches = matches
            best_line = line_words
            
    if max_matches >= 2 and best_line is not None: # At least 2 columns identified
        # Determine column ranges based on header words
        columns = {}
        line_top = min(w['top'] for w in best_line)
        line_bottom = max(w['bottom'] for w in best_line)
        
        # Sort words by X
        best_line.sort(key=lambda w: w['x0'])
        
        for word in best_line:
            # Check raw text against strict variants
            raw_text = word['text']
            for col_name, variants in HEADER_KEYWORDS.items():
                if raw_text in variants:
                    # Found a column header. 
                    # Define range: start at word x0, end at next header x0 (or page width)
                    columns[col_name] = {'start': word['x0'], 'end': None} 
                    break
        
        # Fix 'end' coordinates
        sorted_cols = sorted(columns.items(), key=lambda x: x[1]['start'])
        for i in range(len(sorted_cols) - 1):
            curr_col = sorted_cols[i][0]
            next_col_start = sorted_cols[i+1][1]['start']
            columns[curr_col]['end'] = next_col_start
            
        # Last column goes to the right
        last_col = sorted_cols[-1][0]
        columns[last_col]['end'] = 10000 # Arbitrary large number
        
        return {'top': line_top, 'bottom': line_bottom, 'columns': columns}
        
    return None

def extract_table_rows(words: List[Dict[str, Any]], header_info: Dict[str, Any], start_y: Optional[float] = None) -> List[Dict[str, Any]]:
    """
    Extracts rows based on header info.
    If start_y is provided, it overrides header_info['bottom'].
    """
    table_top = start_y if start_y is not None else header_info['bottom']
    columns = header_info['columns']
    
    # Filter words below header
    table_words = [w for w in words if w['top'] > table_top]
    
    # Group by line
    lines_dict = group_words_by_line(table_words, tolerance=LINE_Y_TOLERANCE)
            
    # Sort lines by Y
    sorted_lines = sorted(lines_dict.items(), key=lambda x: x[0])
    
    rows = []
    for y, line_words in sorted_lines:
        row_data: Dict[str, Any] = {}
        # Assign words to columns
        for word in line_words:
            # Use improved check: check overlap with column range or center point
            # Center point is safer for narrow columns
            word_center_x = (word['x0'] + word['x1']) / 2
            
            assigned = False
            
            # Pre-emptive numeric check for misaligned columns (like Antal)
            # Prioritize assigning numeric values to Antal/A-pris if they are close to the left edge
            if word['text'].replace('.','').replace(',','').strip().isdigit():
                 for col_name in ['antal', 'a_pris', 'summa']:
                    if col_name in columns:
                        x_range = columns[col_name]
                        # If word is within 30pts left of start, grab it. +5 to allow slight overlap into column.
                        if (x_range['start'] - 30) <= word_center_x < x_range['start'] + 5:
                            current_val = row_data.get(col_name, "")
                            row_data[col_name] = (current_val + " " + word['text']).strip()
                            assigned = True
                            break
            
            if assigned:
                continue

            target_col = None
            for col_name, x_range in columns.items():
                # Allow a small tolerance for column boundaries?
                # Using 0 tolerance for strictness since headers define start
                if x_range['start'] <= word_center_x < x_range['end']:
                    target_col = col_name
                    break
            
            # Fix for overlapping Article Number and Description
            # If we have interleaved fragments near the boundary, separate them by type.
            if target_col in ['artikelnr', 'benamning'] and 'artikelnr' in columns and 'benamning' in columns:
                art_end = columns['artikelnr']['end']
                
                # Only apply if Benamning actually follows Artikelnr (adjacent)
                if abs(columns['benamning']['start'] - art_end) < 1:
                    dist = abs(word_center_x - art_end)
                    
                    # If within 60pt of the boundary
                    if dist < 60:
                        txt = word['text'].strip()
                        # If assigned to ArtNr but is clearly a text fragment (e.g. 'F', 'r', 'e' from Fresubin)
                        # Length < 4 to capture fragments
                        if target_col == 'artikelnr' and txt.isalpha() and len(txt) < 4:
                             target_col = 'benamning'
                        # If assigned to Benamning but is clearly a numeric fragment (e.g. '9', '5' from ArtNo)
                        elif target_col == 'benamning' and (txt.isdigit() or txt == '/') and len(txt) < 4:
                             # Only move to Artikelnr if Artikelnr already has content (continuation of split)
                             # This prevents false positives where description starts with a number (e.g. "1 1/2")
                             if row_data.get('artikelnr'):
                                 target_col = 'artikelnr'

            if target_col:
                current_val = row_data.get(target_col, "")
                row_data[target_col] = (current_val + " " + word['text']).strip()
                assigned = True
            
            # Fallback for "antal" and "a_pris" overlapping?
            # Handled by pre-emptive numeric check above.
            
            # Fallback: if not assigned (maybe left of first col?), add to first col if it's description
            if not assigned and 'benamning' in columns:
                 # Heuristic: if it's close to benamning
                 pass 

        # Clean up overlap between artikelnr and benamning where chars are interleaved
        # e.g. ArtNr: "40518F9r5e0su3b9i9n8" (Fresubin interleaved with digits)
        #      Ben: "e5nergy ..." (Digit 5 embedded in energy)
        if 'artikelnr' in row_data and 'benamning' in row_data:
            an = row_data['artikelnr']
            ben = row_data['benamning']
            
            ben_first = ben.split(' ')[0]
            # Check if Benamning start word is corrupted with digits (e.g. e5nergy)
            if any(c.isdigit() for c in ben_first) and any(c.isalpha() for c in ben_first):
                # Check if Artikelnr has letters (intruders)
                if any(c.isalpha() for c in an):
                    cleaned_an = "".join([c for c in an if not c.isalpha()])
                    # Safety check: ArtNr should be substantial (likely barcodes)
                    count_digits = sum(1 for c in cleaned_an if c.isdigit())
                    
                    if count_digits >= 8:
                        extracted_letters = "".join([c for c in an if c.isalpha()])
                        fw_digits = "".join([c for c in ben_first if c.isdigit()])
                        fw_letters = "".join([c for c in ben_first if c.isalpha()])
                        
                        row_data['artikelnr'] = cleaned_an + fw_digits
                        
                        ben_rest = ben[len(ben_first):]
                        row_data['benamning'] = (extracted_letters + " " + fw_letters + ben_rest).strip()

        # Parse numeric fields
        if 'antal' in row_data:
            # Extract unit from antal string before parsing number
            # Look for suffix like "KG", "TIM", "st", "M3" (handling alphanumeric if needed, but usually letters)
            # Assuming unit is mainly alphabetic characters
            # Also accept "-" as unit if it is separated by space (to distinguish from negative numbers like 5-)
            match_unit = re.search(r'(?:([A-Za-zåäöÅÄÖ]+(?:/[A-Za-zåäöÅÄÖ]+)?\.?)|(\s-))\s*$', row_data['antal'])
            if match_unit:
                 row_data['enhet'] = match_unit.group(0).strip()
                 # Remove the unit from the string
                 row_data['antal'] = row_data['antal'][:match_unit.start()] + row_data['antal'][match_unit.end():]
            
            row_data['antal'] = parse_swedish_amount(row_data['antal'])
        if 'a_pris' in row_data:
            row_data['a_pris'] = parse_swedish_amount(row_data['a_pris'])
        if 'summa' in row_data:
            row_data['summa'] = parse_swedish_amount(row_data['summa'])
        
        # Filter empty rows or footer noise
        # A row must have at least one meaningful field
        if not any(row_data.get(k) for k in ['rad', 'artikelnr', 'benamning', 'summa', 'antal', 'a_pris']):
            continue

        # Stop if we hit final totals or footer elements
        raw_text = " ".join([w['text'] for w in line_words]).lower()
        if any(x in raw_text for x in ["att betala", "totalsumma", "er tillgodo", "momsunderlag", "moms"]):
            break
            
        # Stop on page numbers with strict format (integer / integer)
        # e.g. "1 / 2"
        page_num_match = re.search(r'^\s*\d+\s*/\s*\d+\s*$', raw_text)
        if page_num_match:
            break
            
        rows.append(row_data)
    
    # Post-process to merge continuation lines
    merged_rows = []
    if rows:
        merged_rows.append(rows[0])
        for i in range(1, len(rows)):
            curr = rows[i]
            prev = merged_rows[-1]
            
            # Check if current row is a continuation
            # Criteria: has text (rad, benamning), but NO numeric values (antal, a_pris, summa)
            # Make sure we don't merge if the previous row was also empty? No, we want to accumulate text.
            # But the row must be valid line content.
            
            # Check strictly for emptiness of numeric fields (None or 0 is trickier, usually None or 0.0)
            # In FlexCare case, valid rows have 0.0 values, invalid/continuation rows have None/missing keys.
            # `parse_swedish_amount` returns None if missing/empty string.
            
            # Check raw values for keys to see if they were even present
            # But wait, we parsed them above.
            
            has_numerics = (curr.get('antal') is not None and curr.get('antal') != 0) or \
                           (curr.get('a_pris') is not None and curr.get('a_pris') != 0) or \
                           (curr.get('summa') is not None and curr.get('summa') != 0)
            
            # For FlexCare, the continuation lines have NO numeric values at all (None).
            # The lines 1, 2, 5, 6, 7 have 0.0 values.
            # So checking for is not None is enough?
            # Wait, 0.0 is not None.
            
            # Continuation line criteria:
            # 1. No Summa (None) - Summa is the most reliable indicator of a line item.
            # 2. Has text in rad or benamning.
            
            is_continuation = False
            
            if curr.get('summa') is None and curr.get('antal') is None:
                 if curr.get('benamning') or curr.get('rad') or curr.get('artikelnr'):
                     is_continuation = True
            
            if is_continuation:
                # Merge with previous
                for field in ['rad', 'artikelnr', 'benamning']:
                    if curr.get(field):
                        if prev.get(field):
                            # Special handling for 'rad' if it looks like a suffix (starts with / or -?)
                            # or just append with space? User wants "MED.../RS..."
                            separator = "" if curr[field].startswith('/') or curr[field].startswith('-') else " "
                            prev[field] += separator + curr[field]
                        else:
                            prev[field] = curr[field]
                
                # Cleanup common OCR/splitting artifacts
                if prev.get('rad'):
                     prev['rad'] = prev['rad'].replace('--', '-')
            else:
                merged_rows.append(curr)
                
    return merged_rows
