import pdfplumber
import sys

def inspect_pdf(pdf_path):
    print(f"Inspecting {pdf_path}")
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        words = page.extract_words(
            keep_blank_chars=False,
            x_tolerance=3,
            y_tolerance=3
        )
        
        # Sort by top position
        words.sort(key=lambda w: (w['top'], w['x0']))
        
        # Print words in the top section
        print("--- Top 300px Words ---")
        for w in words:
            if w['top'] < 300:
                print(f"Text: '{w['text']}' | x0: {w['x0']:.1f}, top: {w['top']:.1f}, x1: {w['x1']:.1f}, bottom: {w['bottom']:.1f}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        inspect_pdf(sys.argv[1])
    else:
        print("Please provide a PDF path")
