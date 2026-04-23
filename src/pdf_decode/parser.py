from typing import List, Dict, Any, Optional, Tuple, Callable
from .utils import normalize_text, parse_swedish_date, parse_swedish_amount, parse_bankgiro, parse_plusgiro
from .geometry import group_words_by_line
from .constants import ANCHORS, LINE_Y_TOLERANCE
import re
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Anchor matching helpers
# ---------------------------------------------------------------------------

def _build_positioned_text(
    line_words: List[Dict[str, Any]],
    transform: Optional[Callable[[str], str]] = None,
    skip_empty: bool = False,
) -> Tuple[str, List[Tuple[int, int, Dict[str, Any]]]]:
    """Build space-joined text from *line_words* with character→word mapping.

    *transform* is applied to each word's text before joining (e.g. ``normalize_text``).
    If *skip_empty* is ``True``, words whose transformed text is empty are excluded.
    Returns ``(text, positions)`` where *positions* maps ``[start, end)`` char ranges
    to the originating word dict.
    """
    text = ""
    positions: List[Tuple[int, int, Dict[str, Any]]] = []
    for w in line_words:
        t = transform(w['text']) if transform else w['text']
        if skip_empty and not t:
            continue
        start = len(text)
        if start > 0:
            text += " "
            start += 1
        text += t
        end = len(text)
        positions.append((start, end, w))
    return text, positions


def _word_at_position(
    positions: List[Tuple[int, int, Dict[str, Any]]], char_idx: int
) -> Optional[Dict[str, Any]]:
    """Return the word whose character range contains *char_idx*."""
    for start, end, word in positions:
        if start <= char_idx < end:
            return word
    return None


def find_all_anchors(words: List[Dict[str, Any]], anchor_keys: List[str]) -> List[Dict[str, Any]]:
    """Find all occurrences of *anchor_keys* in *words*.

    For each key two matching strategies are tried in order:
    1. **Raw substring match** – preserves case & punctuation (handles
       ``"Bankgiro:"``, ``"OCR Ref:"`` etc.).
    2. **Normalized word-boundary match** – case-insensitive with Swedish
       transliteration (handles ``"referens"``, ``"ocr nummer"`` etc.).

    Returns a list of word dicts (last word of matched phrase), ordered by
    Y position.
    """
    found_anchors: List[Dict[str, Any]] = []
    lines = group_words_by_line(words, tolerance=LINE_Y_TOLERANCE)

    for y in sorted(lines.keys()):
        line_words = sorted(lines[y], key=lambda w: w['x0'])

        raw_text, raw_pos = _build_positioned_text(line_words)
        norm_text, norm_pos = _build_positioned_text(
            line_words, transform=normalize_text, skip_empty=True
        )

        for key in anchor_keys:
            matched_words: List[Dict[str, Any]] = []

            # Keys with uppercase or colon are format-specific labels
            # (e.g. "Bankgiro:", "OCR Ref:") → raw substring search first.
            # All-lowercase keys (e.g. "referens", "ocr") need word-boundary
            # protection to avoid matching inside longer words → normalized first.
            prefer_raw = any(c.isupper() for c in key) or ':' in key

            if prefer_raw:
                # Strategy A — raw substring search, fallback to normalized
                idx = 0
                while True:
                    pos = raw_text.find(key, idx)
                    if pos == -1:
                        break
                    word = _word_at_position(raw_pos, pos + len(key) - 1)
                    if word:
                        matched_words.append(word)
                    idx = pos + 1

                if not matched_words:
                    norm_key = normalize_text(key)
                    if norm_key:
                        pattern = r'\b' + re.escape(norm_key) + r'\b'
                        for match in re.finditer(pattern, norm_text):
                            word = _word_at_position(norm_pos, match.end() - 1)
                            if word:
                                matched_words.append(word)
            else:
                # Strategy B — normalized word-boundary search only.
                # No raw fallback: boundary protection is essential for generic
                # lowercase keys to avoid matching inside longer words
                # (e.g. "referens" inside "referensränta").
                norm_key = normalize_text(key)
                if norm_key:
                    pattern = r'\b' + re.escape(norm_key) + r'\b'
                    for match in re.finditer(pattern, norm_text):
                        word = _word_at_position(norm_pos, match.end() - 1)
                        if word:
                            matched_words.append(word)

            for w in matched_words:
                if w not in found_anchors:
                    found_anchors.append(w)

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

def get_text_below(words: List[Dict[str, Any]], anchor: Dict[str, Any], max_dist_y: float = 50, max_width: float = 200, multiline: bool = False, left_tolerance: float = 100) -> str:
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
            if word['x0'] >= (anchor['x0'] - left_tolerance) and word['x1'] <= (anchor['x1'] + max_width):
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
    Extracts supplier name and address by looking above the address block anchors
    (e.g. "Godkänd för F-skatt", "Org.nr:", "Momsreg.nr:").
    """
    # Use find_anchor for consistent, phrase-aware matching
    supplier_anchors = [
        "Godkänd för F-skatt", "F-skatt", "F skatt",
        "Org.nr:", "Org.nr", "Momsreg.nr:", "Momsreg.nr",
    ]
    found_anchor = find_anchor(words, supplier_anchors, strategy="first")

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

def extract_adjustments(words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extracts adjustments like "Avgår egenavgift".
    Looks for headers like "Rabatter", "Avgifter", "Övrigt".
    """
    target_headers = ["Rabatter", "Avgifter", "Övrigt"]
    found_headers = []

    # Find all header words
    for w in words:
        # Check essentially exact match, allowing for case and trailing colon
        text_clean = w['text'].strip(" :").lower()
        if text_clean in [h.lower() for h in target_headers]:
            found_headers.append(w)
    
    if not found_headers:
        return []

    # Sort found headers by vertical position
    found_headers.sort(key=lambda w: (w['top'], w['x0']))

    adjustments: List[Dict[str, Any]] = []
    
    # Track processed Y ranges to avoid overlaps, though simplified logic usually suffices
    # We will process each header
    
    table_stop_keywords = ["Antal", "Artikelnr", "Benämning", "A'pris", "Summa", "Rad"]
    section_stop_keywords = ["Notering", "Betalningsvillkor"]

    # Detect the table header row(s) by finding lines that contain *multiple*
    # column-header keywords. A single "Summa" appearing in adjustment text
    # (e.g. "Summa Legeringstillägg") must not be treated as the table header.
    table_header_ys: List[float] = []
    table_header_lines = group_words_by_line(
        [w for w in words if w['text'] in table_stop_keywords],
        tolerance=LINE_Y_TOLERANCE,
    )
    for y, lw in table_header_lines.items():
        distinct = {w['text'] for w in lw}
        if len(distinct) >= 3:
            table_header_ys.append(min(w['top'] for w in lw))

    for header in found_headers:
        # Determine type
        header_clean = header['text'].strip(" :")
        typ = None
        for h in target_headers:
            if h.lower() == header_clean.lower():
                typ = h
                break
        if not typ:
            typ = header_clean.capitalize()

        header_left = header['x0'] - 20
        header_bottom = header['bottom']
        header_max_y = header_bottom + 200

        # Limit search area to stop before the table header row
        for y_top in table_header_ys:
            if y_top > header_bottom:
                header_max_y = min(header_max_y, y_top - 2)

        # Limit search area to stop before Notering/Betalningsvillkor sections
        for w in words:
            if w['top'] > header_bottom and w['text'] in section_stop_keywords:
                header_max_y = min(header_max_y, w['top'] - 2)

        # Also limit search area to stop before the next header
        for other_header in found_headers:
            if other_header['top'] > header['bottom'] + LINE_Y_TOLERANCE:
                header_max_y = min(header_max_y, other_header['top'] - 2)
                break

        # Determine right boundary by finding the nearest column to the right on the same line
        header_y_center = (header['top'] + header['bottom']) / 2
        next_column_x = None
        for w in words:
            w_y_center = (w['top'] + w['bottom']) / 2
            if abs(w_y_center - header_y_center) < LINE_Y_TOLERANCE:
                if w['x0'] > header['x1'] + 20:
                    if next_column_x is None or w['x0'] < next_column_x:
                        next_column_x = w['x0']
        header_right = (next_column_x - 5) if next_column_x is not None else (header['x1'] + 200)
        
        candidates = []
        for w in words:
            if w['top'] > header_bottom and w['top'] < header_max_y:
                if w['x0'] >= header_left and w['x0'] < header_right: 
                    candidates.append(w)

        if not candidates:
            continue

        lines = group_words_by_line(candidates, tolerance=LINE_Y_TOLERANCE)
        sorted_y = sorted(lines.keys())
        
        for y in sorted_y:
            line_words = sorted(lines[y], key=lambda w: w['x0'])
            full_text = " ".join([w['text'] for w in line_words])

            # Check if line is the table header row (contains multiple column headers)
            distinct_stop = {w['text'] for w in line_words if w['text'] in table_stop_keywords}
            if len(distinct_stop) >= 3:
                break

            # Try to parse amount from the rightmost words, combining consecutive
            # numeric tokens that form a single amount with space as thousands separator
            # e.g. "198" "727,50" -> "198 727,50" -> 198727.50
            amount = None
            amount_word_count = 0
            for n in range(1, min(len(line_words), 4) + 1):
                combined = " ".join([w['text'] for w in line_words[-n:]])
                parsed = parse_swedish_amount(combined)
                if parsed is not None:
                    # Check that the extra words are purely numeric (digits only)
                    if n == 1 or all(re.match(r'^\d+$', w['text']) for w in line_words[-n:-1]):
                        amount = parsed
                        amount_word_count = n
            
            if amount is not None:
                desc_words = line_words[:-amount_word_count]
                if desc_words:
                    # Filter out words separated by large gaps
                    final_desc_words = []
                    if desc_words:
                        final_desc_words.append(desc_words[0])
                        for i in range(1, len(desc_words)):
                            gap = desc_words[i]['x0'] - desc_words[i-1]['x1']
                            if gap > 60:
                                break
                            final_desc_words.append(desc_words[i])
                    
                    # Also filter out likely header labels that might have drifted in
                    stop_labels = ["förfallodatum", "fakturadatum", "ocr-nummer", "ocr"]
                    clean_words = []
                    for w in final_desc_words:
                        if any(s in w['text'].lower() for s in stop_labels):
                            break
                        clean_words.append(w)
                    
                    if clean_words:
                        description = " ".join([w['text'] for w in clean_words])
                        
                        # Add if not duplicate (same content)
                        exists = False
                        for adj in adjustments:
                            if (adj['typ'] == typ and 
                                adj['beskrivning'] == description and 
                                adj['belopp'] == amount):
                                exists = True
                                break
                        
                        if not exists:
                            adjustments.append({
                                "typ": typ,
                                "beskrivning": description,
                                "belopp": amount
                            })
            
    return adjustments

def parse_header(pages_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Parses header fields from the first page (usually).
    """
    if not pages_data:
        return {}
        
    first_page_words = pages_data[0]['words']
    result: Dict[str, Any] = {}
    
    # Helper to try finding a field
    def try_extract(field_key, parser_func=None, multiline=False, strategy="first", max_word_gap=60, left_tolerance=100, max_width=200, max_dist_y=50):
        anchors_list = ANCHORS.get(field_key, [])
        candidates = find_all_anchors(first_page_words, anchors_list)
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
                    logger.debug("Failed parsing %s from '%s'", field_key, val_right)
                else:
                    return val_right

        # Second Pass: If no value to right, try BELOW
        # Use strategy to pick which anchor to use (first or last)
        if candidates:
            for anchor in candidates:
                val_below = get_text_below(first_page_words, anchor, multiline=multiline, left_tolerance=left_tolerance, max_width=max_width, max_dist_y=max_dist_y)
                
                if val_below:
                    if parser_func:
                        res = parser_func(val_below)
                        if res is not None:
                            return res
                    else:
                        return val_below
        
        return None

    # Determine invoice type
    result['fakturatyp'] = "Faktura"
    for w in first_page_words:
        if "Kreditfaktura" in w['text'].replace(" ", ""):
            result['fakturatyp'] = "Kreditfaktura"
            break

    result['fakturanummer'] = try_extract('fakturanummer')
    result['fakturadatum'] = try_extract('fakturadatum', parse_swedish_date)
    result['forfallodatum'] = try_extract('forfallodatum', parse_swedish_date)
    result['ocr_nummer'] = try_extract('ocr')
    result['referens'] = try_extract('referens', multiline=True, max_width=120)
    result['referenser'] = try_extract('referenser', left_tolerance=5)
    result['totalsumma'] = try_extract('totalsumma', parse_swedish_amount, strategy="last", max_word_gap=150)
    result['moms_belopp'] = try_extract('moms', parse_swedish_amount, strategy="last", max_word_gap=150)
    result['delsumma_exkl_moms'] = try_extract('delsumma', parse_swedish_amount, max_word_gap=150)
    result['oresavrundning'] = try_extract('oresavrundning', parse_swedish_amount, strategy="last", max_word_gap=150)
    
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

    # Extract adjustments from all pages
    all_adjustments = []
    for page in pages_data:
        page_adjustments = extract_adjustments(page['words'])
        all_adjustments.extend(page_adjustments)
    
    # Remove duplicates based on description and amount?
    # Simple deduplication
    unique_adjustments = []
    seen_adj = set()
    for adj in all_adjustments:
        key = (adj['typ'], adj['beskrivning'], adj['belopp'])
        if key not in seen_adj:
            seen_adj.add(key)
            unique_adjustments.append(adj)

    result['justeringar'] = unique_adjustments

    return result
