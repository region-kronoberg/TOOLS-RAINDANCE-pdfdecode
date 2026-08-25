from decimal import Decimal

from pdf_decode.utils import parse_swedish_amount


def test_parse_swedish_amount_reads_standard_decimal_amount():
    assert parse_swedish_amount("1 234,56") == Decimal("1234.56")


def test_parse_swedish_amount_ignores_amount_like_text_inside_serial_number():
    serials = "2603N2635,2603N2636,2603N2637"

    assert parse_swedish_amount(serials) is None
