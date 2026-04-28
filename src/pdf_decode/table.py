from typing import List, Dict, Any, Optional
import re
import logging
from .utils import parse_swedish_amount
from .geometry import group_words_by_line
from .constants import HEADER_KEYWORDS, LINE_Y_TOLERANCE

logger = logging.getLogger(__name__)

# Sentinel for unbounded column right edge
_COL_END_SENTINEL = 10_000

# Pixel-distance thresholds for column assignment
_NUMERIC_SNAP_DISTANCE = 30   # how far left of a column start a digit can be snapped in
_BOUNDARY_ZONE = 60           # boundary zone around artikelnr/benamning split
_FRAGMENT_MAX_LEN = 4         # max chars to consider a word a "fragment"
_INTERLEAVE_MIN_DIGITS = 8    # min digit count to trigger deinterleave heuristic

# Footer / stop keywords
_TABLE_STOP_PHRASES = ["att betala", "totalsumma", "er tillgodo", "momsunderlag", "varav moms"]

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
        columns[last_col]['end'] = _COL_END_SENTINEL
        
        return {'top': line_top, 'bottom': line_bottom, 'columns': columns}
        
    return None

def _is_numeric_text(text: str) -> bool:
    """Check if *text* looks like a pure numeric token (digits, dots, commas,
    optionally with a leading or trailing minus sign)."""
    stripped = text.replace('.', '').replace(',', '').strip()
    if stripped.startswith('-'):
        stripped = stripped[1:]
    if stripped.endswith('-'):
        stripped = stripped[:-1]
    return stripped.isdigit()


def _snap_numeric_to_column(word: Dict[str, Any], columns: Dict[str, Any], row_data: Dict[str, Any]) -> bool:
    """Try to snap a numeric word to a nearby numeric column that it's slightly left of.

    Returns ``True`` if the word was assigned.
    """
    word_center_x = (word['x0'] + word['x1']) / 2
    for col_name in ('antal', 'a_pris', 'summa'):
        if col_name not in columns:
            continue
        x_range = columns[col_name]
        if (x_range['start'] - _NUMERIC_SNAP_DISTANCE) <= word_center_x < x_range['start'] + 5:
            current_val = row_data.get(col_name, "")
            row_data[col_name] = (current_val + " " + word['text']).strip()
            return True
    return False


def _resolve_article_description_boundary(
    word: Dict[str, Any], target_col: str, columns: Dict[str, Any], row_data: Dict[str, Any]
) -> str:
    """Refine column assignment for words near the artikelnr / benämning boundary.

    When PDF character bounding boxes overlap the column split, short text
    fragments may land in the wrong column.  This nudges them based on
    whether the fragment is alphabetic (→ benämning) or numeric (→ artikelnr).
    """
    if target_col not in ('artikelnr', 'benamning'):
        return target_col
    if 'artikelnr' not in columns or 'benamning' not in columns:
        return target_col

    art_end = columns['artikelnr']['end']
    if abs(columns['benamning']['start'] - art_end) >= 1:
        return target_col

    word_center_x = (word['x0'] + word['x1']) / 2
    if abs(word_center_x - art_end) >= _BOUNDARY_ZONE:
        return target_col

    txt = word['text'].strip()
    if len(txt) >= _FRAGMENT_MAX_LEN:
        return target_col

    if target_col == 'artikelnr' and txt.isalpha():
        return 'benamning'
    if target_col == 'benamning' and (txt.isdigit() or txt == '/'):
        # Only push digits/slashes back into artikelnr if the description
        # has not started yet on this line. Otherwise a digit that legitimately
        # belongs inside the description (e.g. "FS LIBRE 2 PLUS …") would be
        # appended to artikelnr.
        if row_data.get('artikelnr') and not row_data.get('benamning'):
            return 'artikelnr'

    return target_col


def _fix_interleaved_chars(row_data: Dict[str, Any]) -> None:
    """De-interleave artikelnr and benämning when PDF fragments overlap.

    Handles the case where character-level bounding boxes cause digits from
    an article number and letters from the description to be mixed together,
    e.g. artikelnr="40518F9r5e0su3b9i9n8", benämning="e5nergy …".
    """
    if 'artikelnr' not in row_data or 'benamning' not in row_data:
        return

    an = row_data['artikelnr']
    ben = row_data['benamning']
    ben_first = ben.split(' ')[0]

    # Only act if the first description word has mixed alpha+digit chars
    if not (any(c.isdigit() for c in ben_first) and any(c.isalpha() for c in ben_first)):
        return
    if not any(c.isalpha() for c in an):
        return

    cleaned_an = "".join(c for c in an if not c.isalpha())
    if sum(1 for c in cleaned_an if c.isdigit()) < _INTERLEAVE_MIN_DIGITS:
        return

    extracted_letters = "".join(c for c in an if c.isalpha())
    fw_digits = "".join(c for c in ben_first if c.isdigit())
    fw_letters = "".join(c for c in ben_first if c.isalpha())

    row_data['artikelnr'] = cleaned_an + fw_digits
    ben_rest = ben[len(ben_first):]
    row_data['benamning'] = (extracted_letters + " " + fw_letters + ben_rest).strip()


def _parse_row_numerics(row_data: Dict[str, Any]) -> None:
    """Parse antal (with unit extraction), a_pris and summa in *row_data* in-place."""
    if 'antal' in row_data:
        match_unit = re.search(
            r'(?:([A-Za-zåäöÅÄÖ]+(?:/[A-Za-zåäöÅÄÖ]+)?\.?)|(\s-))\s*$',
            row_data['antal'],
        )
        if match_unit:
            row_data['enhet'] = match_unit.group(0).strip()
            row_data['antal'] = row_data['antal'][:match_unit.start()] + row_data['antal'][match_unit.end():]
        row_data['antal'] = parse_swedish_amount(row_data['antal'])

    if 'a_pris' in row_data:
        row_data['a_pris'] = parse_swedish_amount(row_data['a_pris'])

    if 'summa' in row_data:
        row_data['summa'] = parse_swedish_amount(row_data['summa'])


def _is_table_footer(line_words: List[Dict[str, Any]]) -> bool:
    """Return ``True`` if the line looks like invoice totals or a page number."""
    raw_text = " ".join(w['text'] for w in line_words).lower()
    if any(phrase in raw_text for phrase in _TABLE_STOP_PHRASES):
        return True
    # Match page numbers like "1/6", "12/30" but not batch numbers like "286/2511192"
    m = re.search(r'^\s*(\d+)\s*/\s*(\d+)\s*$', raw_text)
    if m:
        page_num = int(m.group(1))
        page_total = int(m.group(2))
        if page_num <= page_total and page_total <= 999:
            return True
    return False


def _merge_continuation_lines(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge text-only continuation rows into the preceding data row."""
    if not rows:
        return []

    merged: List[Dict[str, Any]] = [rows[0]]
    for curr in rows[1:]:
        prev = merged[-1]

        # Drop info-only rows that carry only a_pris (e.g. discount/rebate info)
        is_apris_only = (
            curr.get('a_pris') is not None
            and curr.get('summa') is None
            and curr.get('antal') is None
            and not curr.get('benamning')
            and not curr.get('artikelnr')
            and not curr.get('rad')
        )
        if is_apris_only:
            continue

        is_continuation = (
            curr.get('summa') is None
            and curr.get('antal') is None
            and (curr.get('benamning') or curr.get('rad') or curr.get('artikelnr'))
        )

        if is_continuation:
            for field in ('rad', 'artikelnr', 'benamning'):
                if curr.get(field):
                    if prev.get(field):
                        separator = "" if curr[field].startswith('/') or curr[field].startswith('-') else " "
                        prev[field] += separator + curr[field]
                    else:
                        prev[field] = curr[field]
            if prev.get('rad'):
                prev['rad'] = prev['rad'].replace('--', '-')
        else:
            merged.append(curr)

    return merged


def extract_table_rows(words: List[Dict[str, Any]], header_info: Dict[str, Any], start_y: Optional[float] = None) -> List[Dict[str, Any]]:
    """
    Extracts rows based on header info.
    If start_y is provided, it overrides header_info['bottom'].
    """
    table_top = start_y if start_y is not None else header_info['bottom']
    columns = header_info['columns']

    # Filter words below header and group by line
    table_words = [w for w in words if w['top'] > table_top]
    lines_dict = group_words_by_line(table_words, tolerance=LINE_Y_TOLERANCE)
    sorted_lines = sorted(lines_dict.items(), key=lambda x: x[0])

    rows: List[Dict[str, Any]] = []
    for _y, line_words in sorted_lines:
        row_data: Dict[str, Any] = {}

        # Force all words into description for "SUMMA JOBB …" lines
        line_full_text = " ".join(w['text'] for w in line_words)
        force_desc = "SUMMA JOBB" in line_full_text.upper() and 'benamning' in columns

        # --- assign words to columns ---
        for word in line_words:
            if force_desc:
                current_val = row_data.get('benamning', "")
                row_data['benamning'] = (current_val + " " + word['text']).strip()
                continue

            word_center_x = (word['x0'] + word['x1']) / 2
            assigned = False

            # Snap misaligned numeric words to nearby numeric columns
            if _is_numeric_text(word['text']):
                assigned = _snap_numeric_to_column(word, columns, row_data)

            if assigned:
                continue

            # Standard column lookup by center-x
            target_col = None
            for col_name, x_range in columns.items():
                if x_range['start'] <= word_center_x < x_range['end']:
                    target_col = col_name
                    break

            # Refine near the artikelnr / benämning boundary
            if target_col:
                target_col = _resolve_article_description_boundary(word, target_col, columns, row_data)
                current_val = row_data.get(target_col, "")
                row_data[target_col] = (current_val + " " + word['text']).strip()

        # De-interleave overlapping artikelnr / benämning fragments
        _fix_interleaved_chars(row_data)

        # Parse numeric fields & extract unit from antal
        _parse_row_numerics(row_data)

        # Skip empty rows
        if not any(row_data.get(k) for k in ('rad', 'artikelnr', 'benamning', 'summa', 'antal', 'a_pris')):
            continue

        # Stop at footer / totals
        if _is_table_footer(line_words):
            break

        rows.append(row_data)

    return _merge_continuation_lines(rows)
