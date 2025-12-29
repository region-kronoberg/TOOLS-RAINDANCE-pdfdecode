import click
from pathlib import Path
from .processor import InvoiceProcessor

@click.command()
@click.argument('input_path', type=click.Path(exists=True))
@click.option('--output-dir', '-o', type=click.Path(), default='out', help='Output directory for JSON files')
def main(input_path, output_dir):
    """
    Parses PDF invoices and outputs JSON.
    INPUT_PATH can be a file or a directory.
    """
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    files = [input_path] if input_path.is_file() else list(input_path.glob('*.pdf'))
    
    processor = InvoiceProcessor()
    
    for pdf_file in files:
        click.echo(f"Processing {pdf_file.name}...")
        try:
            invoice = processor.process(pdf_file)
            if invoice:
                out_file = output_dir / f"{pdf_file.stem}.json"
                with open(out_file, 'w', encoding='utf-8') as f:
                    f.write(invoice.model_dump_json(indent=2))
                click.echo(f"Wrote {out_file}")
            else:
                click.echo(f"No text found in {pdf_file.name}")
        except Exception as e:
            click.echo(f"Error processing {pdf_file.name}: {e}", err=True)

if __name__ == '__main__':
    main()
