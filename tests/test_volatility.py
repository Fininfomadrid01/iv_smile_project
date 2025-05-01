import pytest
from datetime import datetime
from scraper.volatility import parse_spanish_date


def test_parse_numeric_date():
    assert parse_spanish_date("16/05/2025") == datetime(2025, 5, 16)


def test_parse_spanish_format():
    assert parse_spanish_date("16 may. 2025") == datetime(2025, 5, 16)


def test_parse_invalid_date():
    with pytest.raises(ValueError):
        parse_spanish_date("invalid-date") 