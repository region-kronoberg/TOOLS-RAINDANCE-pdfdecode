"""
Regressionstester för pdf_decode.

Kör parsern mot PDF-filer i in/ och jämför resultatet med
förväntad JSON i out/before/. Fältet 'extracted_at' ignoreras
vid jämförelse eftersom det är tidsstämpel.
"""
import json
import pytest
from pathlib import Path
from pdf_decode.processor import InvoiceProcessor

ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT / "in"
EXPECTED_DIR = ROOT / "out" / "before"

IGNORED_KEYS = {"extracted_at"}

# Bygg lista av (pdf_path, expected_json_path) för alla matchande filer
_test_cases = []
if EXPECTED_DIR.exists():
    for expected_json in sorted(EXPECTED_DIR.glob("*.json")):
        pdf_path = INPUT_DIR / f"{expected_json.stem}.pdf"
        if pdf_path.exists():
            _test_cases.append((pdf_path, expected_json))


def _remove_ignored_keys(data, ignored_keys):
    """Rekursivt ta bort nycklar som ska ignoreras vid jämförelse."""
    if isinstance(data, dict):
        return {k: _remove_ignored_keys(v, ignored_keys) for k, v in data.items() if k not in ignored_keys}
    elif isinstance(data, list):
        return [_remove_ignored_keys(item, ignored_keys) for item in data]
    return data


def _load_expected(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.parametrize(
    "pdf_path,expected_path",
    _test_cases,
    ids=[p.stem for p, _ in _test_cases],
)
def test_regression_output_matches(pdf_path: Path, expected_path: Path):
    """Parserns output ska matcha den sparade referens-JSONen."""
    processor = InvoiceProcessor()
    invoice = processor.process(pdf_path)

    assert invoice is not None, f"Parsern returnerade None för {pdf_path.name}"

    actual = json.loads(invoice.model_dump_json(indent=2))
    expected = _load_expected(expected_path)

    actual_clean = _remove_ignored_keys(actual, IGNORED_KEYS)
    expected_clean = _remove_ignored_keys(expected, IGNORED_KEYS)

    if actual_clean != expected_clean:
        # Skapa en läsbar diff för felsökning
        actual_str = json.dumps(actual_clean, indent=2, sort_keys=True, ensure_ascii=False)
        expected_str = json.dumps(expected_clean, indent=2, sort_keys=True, ensure_ascii=False)

        import difflib
        diff = "\n".join(difflib.unified_diff(
            expected_str.splitlines(),
            actual_str.splitlines(),
            fromfile=f"expected ({expected_path.name})",
            tofile=f"actual ({pdf_path.name})",
            lineterm="",
        ))
        pytest.fail(f"Regression i {pdf_path.stem}:\n{diff}")
