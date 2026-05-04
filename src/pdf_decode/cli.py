import logging
import sys
import traceback
from pathlib import Path

import click

from .processor import InvoiceProcessor

logger = logging.getLogger(__name__)


@click.command()
@click.argument('input_path', type=click.Path(exists=True))
@click.option('--output-dir', '-o', type=click.Path(), default='out',
              help='Output directory for JSON files')
@click.option('-v', '--verbose', count=True,
              help='Increase verbosity: -v for INFO, -vv for DEBUG. '
                   'Also enables full tracebacks on errors.')
def main(input_path, output_dir, verbose):
    """
    Parses PDF invoices and outputs JSON.
    INPUT_PATH can be a file or a directory.
    """
    # Configure logging based on verbosity. Without this, logger.debug/info
    # calls inside parser/table modules are silently dropped.
    if verbose >= 2:
        level = logging.DEBUG
    elif verbose == 1:
        level = logging.INFO
    else:
        level = logging.WARNING
    logging.basicConfig(
        level=level,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    )

    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if input_path.is_file():
        files = [input_path]
    else:
        # Sort for deterministic processing order across filesystems.
        files = sorted(input_path.glob('*.pdf'))

    if not files:
        click.echo(f"No PDF files found in {input_path}", err=True)
        sys.exit(1)

    processor = InvoiceProcessor()
    failures = 0

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
                click.echo(f"No text found in {pdf_file.name}", err=True)
                failures += 1
        except Exception as e:
            failures += 1
            click.echo(f"Error processing {pdf_file.name}: {e}", err=True)
            if verbose:
                click.echo(traceback.format_exc(), err=True)
            logger.exception("Failed to process %s", pdf_file.name)

    if failures:
        click.echo(
            f"Completed with {failures} failure(s) out of {len(files)} file(s).",
            err=True,
        )
        sys.exit(1)


if __name__ == '__main__':
    main()
