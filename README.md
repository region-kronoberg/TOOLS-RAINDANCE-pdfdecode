# PDF-decode

A robust Python tool for parsing PDF invoices and extracting structured data into JSON format. Specifically designed to handle Swedish invoice formats (AXT e-invoices produced by Raindance), it extracts header information, supplier details, line items, and totals.

## Features

*   **Layout Extraction**: Uses `pdfplumber` to analyze the spatial layout of PDF documents.
*   **Header Parsing**: Identifies key invoice fields like Invoice Number, Date, Due Date, OCR, and Reference using configurable anchors.
*   **Supplier Extraction**: Intelligent extraction of supplier details (Name, Address, OrgNr, VAT, Bankgiro, etc.) based on spatial relationships.
*   **Table Extraction**: Automatically detects table headers and extracts line items (Article No, Description, Quantity, Unit Price, Total).
*   **Swedish Format Support**: Handles Swedish date formats (YYYY-MM-DD, etc.) and numeric formats (1 234,50 kr).
*   **CLI Interface**: Simple command-line interface for processing single files or batch processing directories.
*   **Structured Output**: Validates and outputs data using `Pydantic` models to ensure JSON schema consistency.

## Installation

1.  Clone the repository:
    ```bash
    git clone <repository-url>
    cd PDF-decode
    ```

2.  Create a virtual environment (recommended):
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

The tool can be used via the command line.

### Process a single file
```bash
pdf-decode path/to/invoice.pdf --output-dir out/
```

### Process a directory
```bash
pdf-decode in/ --output-dir out/
```

### Options
*   `input_path`: Path to a PDF file or a directory containing PDF files.
*   `--output-dir`, `-o`: Directory where the resulting JSON files will be saved (default: `out`).

## Project Structure

```
src/
└── pdf_decode/
    ├── cli.py          # Command-line interface entry point
    ├── processor.py    # Main processing orchestration
    ├── extract.py      # Low-level PDF layout extraction
    ├── parser.py       # Header and field parsing logic
    ├── table.py        # Table detection and row extraction
    ├── geometry.py     # Shared spatial/geometric utilities
    ├── constants.py    # Configuration (Anchors, Keywords)
    ├── schema.py       # Pydantic data models
    └── utils.py        # Text normalization and formatting helpers
```

## Development

This project uses `hatchling` for building.

To run locally without installing:
```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
python3 -m pdf_decode.cli in/ -o out/
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

Raindance is a registered trademark of CGI Inc. This project is an independent open-source tool developed by Region Kronoberg and is not affiliated with, endorsed by, or sponsored by CGI Inc. or the Raindance product owners.

Any use of third-party trademarks, service marks, trade names, or product names, including Raindance, in this project is for informational purposes only to identify the compatibility of this tool.

