import pdfplumber
from typing import List, Dict, Any
from pathlib import Path

def extract_layout(pdf_path: Path) -> List[Dict[str, Any]]:
    """
    Extracts words and their bounding boxes from a PDF.
    Returns a list of pages, where each page contains 'page_number', 'width', 'height', and 'words'.
    """
    pages_data = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            # Extract words with x0, top, x1, bottom, text
            words = page.extract_words(
                keep_blank_chars=False,
                x_tolerance=3,
                y_tolerance=3
            )
            pages_data.append({
                "page_number": i + 1,
                "width": float(page.width),
                "height": float(page.height),
                "words": words
            })
    return pages_data
