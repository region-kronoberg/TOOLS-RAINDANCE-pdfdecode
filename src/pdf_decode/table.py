from typing import List, Dict, Any, Optional
from .utils import normalize_text, parse_swedish_amount
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
        line_text = " ".join([w['text'] for w in line_words]).lower()
        
        for key, variants in HEADER_KEYWORDS.items():
            for var in variants:
                if var in line_text:
                    matches += 1
                    break
        
        if matches > max_matches:
            max_matches = matches
            best_line = line_words
            
    if max_matches >= 2: # At least 2 columns identified
        # Determine column ranges based on header words
        columns = {}
        line_top = min(w['top'] for w in best_line)
        line_bottom = max(w['bottom'] for w in best_line)
        
        # Sort words by X
        best_line.sort(key=lambda w: w['x0'])
        
        for word in best_line:
            norm = normalize_text(word['text'])
            for col_name, variants in HEADER_KEYWORDS.items():
                if norm in variants:
                    # Found a column header. 
                    # Define range: start at word x0, end at next header x0 (or page width)
                    columns[col_name] = {'start': word['x0'], 'end': None} # Will fix end later
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
        row_data = {}
        # Assign words to columns
        for word in line_words:
            word_center_x = (word['x0'] + word['x1']) / 2
            
            assigned = False
            for col_name, x_range in columns.items():
                if x_range['start'] <= word_center_x < x_range['end']:
                    current_val = row_data.get(col_name, "")
                    row_data[col_name] = (current_val + " " + word['text']).strip()
                    assigned = True
                    break
            
            # Fallback: if not assigned (maybe left of first col?), add to first col if it's description
            if not assigned and 'benamning' in columns:
                 # Heuristic: if it's close to benamning
                 pass 

        # Parse numeric fields
        if 'antal' in row_data:
            row_data['antal'] = parse_swedish_amount(row_data['antal'])
        if 'a_pris' in row_data:
            row_data['a_pris'] = parse_swedish_amount(row_data['a_pris'])
        if 'summa' in row_data:
            row_data['summa'] = parse_swedish_amount(row_data['summa'])
        
        # Filter empty rows or footer noise (e.g. "Att betala" line might be caught)
        if not row_data.get('benamning') and not row_data.get('summa'):
            continue
            
        # Stop if we hit totals (heuristic)
        raw_text = " ".join([w['text'] for w in line_words]).lower()
        if "att betala" in raw_text or "totalsumma" in raw_text or "moms" in raw_text:
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
            # Criteria: has benamning, but NO numeric values (antal, a_pris, summa)
            has_numerics = curr.get('antal') is not None or curr.get('a_pris') is not None or curr.get('summa') is not None
            has_benamning = bool(curr.get('benamning'))
            
            if has_benamning and not has_numerics:
                # Merge with previous
                if prev.get('benamning'):
                    prev['benamning'] += " " + curr['benamning']
                else:
                    prev['benamning'] = curr['benamning']
            else:
                merged_rows.append(curr)
                
    return merged_rows
