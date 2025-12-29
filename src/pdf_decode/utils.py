import re
from typing import Optional

def parse_swedish_amount(text: str) -> Optional[float]:
    """
    Parses a Swedish amount string (e.g., "1 234,50", "1.234,50", "1234,50-") into a float.
    Returns None if parsing fails.
    """
    if not text:
        return None
    
    # Try to find a pattern that looks like a currency amount:
    # 1. Digits, optional spaces/dots, comma, 2 digits (e.g. 10 059,00)
    # 2. Digits, optional spaces/dots (e.g. 5000)
    
    # Regex for standard Swedish format: 1 234,56 or 1234,56
    # We look for the LAST match if there are multiple, or the one that looks most like a full amount?
    # Actually, if we have "25% 10 059,00", we want 10059.00.
    # "25%" might be parsed as 25.
    
    # Let's try to extract potential numbers
    # Pattern: optional minus, digits/spaces/dots, optional comma+digits, optional minus
    
    # First, clean up text but keep spaces to separate numbers
    # Replace non-breaking spaces with normal spaces
    text = text.replace('\xa0', ' ')
    
    # Find all potential number candidates
    # A candidate is a sequence of digits, spaces, dots, commas, minuses
    # But we want to be specific.
    
    # Look for X,XX or X,X
    matches = re.findall(r'-?[\d\s\.]+,[\d]{1,2}-?', text)
    
    candidate = None
    if matches:
        # Pick the longest match or the one that isn't a percentage?
        # Usually the amount is the most significant number.
        # If we have "25% 10 059,00", matches might be ["10 059,00"] (since 25% has no comma)
        # If we have "10,5%", match is "10,5".
        
        # Let's try to parse each match and see.
        for m in matches:
            # Clean the match
            val = _parse_clean_amount(m)
            if val is not None:
                # Return the first valid amount found.
                # This is usually the one associated with the label if it's close.
                return val
        
        if candidate is not None:
            return candidate

    # If no comma pattern found, try simpler integer pattern
    # But be careful of dates, phone numbers etc.
    # If the text is just digits, it's fine.
    clean_text = re.sub(r'[^\d,\.\-\s]', '', text).strip()
    return _parse_clean_amount(clean_text)

def _parse_clean_amount(text: str) -> Optional[float]:
    clean_text = text.strip()
    is_negative = False
    if clean_text.endswith('-'):
        is_negative = True
        clean_text = clean_text[:-1]
    elif clean_text.startswith('-'):
        is_negative = True
        clean_text = clean_text[1:]
        
    if ',' in clean_text:
        parts = clean_text.split(',')
        if len(parts) != 2:
            return None
        integer_part = re.sub(r'[\s\.]', '', parts[0])
        decimal_part = re.sub(r'\D', '', parts[1]) # Remove any trailing non-digits
        try:
            val = float(f"{integer_part}.{decimal_part}")
            return -val if is_negative else val
        except ValueError:
            return None
    else:
        clean_text_no_space = re.sub(r'\s', '', clean_text)
        try:
            val = float(clean_text_no_space)
            return -val if is_negative else val
        except ValueError:
            return None


def parse_swedish_date(text: str) -> Optional[str]:
    """
    Parses a date string into ISO 8601 format (YYYY-MM-DD).
    Supports YYYY-MM-DD, YYYY.MM.DD, DD/MM/YYYY, etc.
    """
    if not text:
        return None
        
    text = text.strip()
    
    # Try ISO YYYY-MM-DD
    match = re.match(r'(\d{4})[\-\.](\d{2})[\-\.](\d{2})', text)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        
    # Try DD/MM/YYYY or DD-MM-YYYY
    match = re.match(r'(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})', text)
    if match:
        # Naive assumption: first is day, second is month
        day, month, year = match.group(1), match.group(2), match.group(3)
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
    # Try YYYYMMDD
    match = re.match(r'(\d{4})(\d{2})(\d{2})', text)
    if match:
         return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"

    return None

def normalize_text(text: str) -> str:
    """
    Normalizes text for anchor matching: lowercase, remove punctuation, collapse spaces.
    Also transliterates Swedish chars åäö -> aao.
    """
    if not text:
        return ""
    text = text.lower()
    # Transliterate Swedish chars
    text = text.replace('å', 'a').replace('ä', 'a').replace('ö', 'o')
    text = text.replace('é', 'e')
    
    text = re.sub(r'[^\w\s%]', ' ', text) # Keep % for VAT
    text = re.sub(r'\s+', ' ', text).strip()
    return text
