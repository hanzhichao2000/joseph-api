"""Option row DTOs mirror the lake contract (cnequity 0.25.0): one test per behavior."""

import math
from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from joseph_api import Exchange, OptionBar, OptionContract, OptionGreek
from joseph_api.instruments import normalize_symbol_case
from joseph_api.symbol_utils import exchange_from_code, option_internal_symbol

FETCHED_AT = datetime(2026, 11, 26, 8, 0, tzinfo=UTC)

CONTRACT_COLUMNS = {
    "data_version",
    "dates_basis",
    "exchange",
    "exchange_code",
    "exercise_style",
    "expiry_date",
    "expiry_month",
    "fetched_at",
    "first_seen_date",
    "last_seen_date",
    "list_date",
    "multiplier",
    "option_type",
    "product",
    "product_name",
    "source",
    "strike",
    "symbol",
    "tick_size",
    "underlying_kind",
    "underlying_symbol",
}
# `pre_settle` is in the exported data but absent from the lake's registered contract (0.25.0);
# the row follows the data and the drift is recorded in #31.
BAR_COLUMNS = {
    "amount",
    "close",
    "data_version",
    "delta",
    "exchange",
    "exchange_code",
    "exercise_volume",
    "fetched_at",
    "high",
    "implied_vol",
    "low",
    "oi_change",
    "open",
    "pre_settle",
    "open_interest",
    "option_type",
    "product",
    "series_implied_vol",
    "settle",
    "source",
    "strike",
    "symbol",
    "trade_date",
    "underlying_symbol",
    "volume",
}
GREEK_COLUMNS = {
    "data_version",
    "delta",
    "fetched_at",
    "forward_source",
    "gamma",
    "iv",
    "model",
    "rate",
    "rate_source",
    "rho",
    "source",
    "status",
    "symbol",
    "theta",
    "time_to_expiry",
    "trade_date",
    "underlying_price",
    "underlying_symbol",
    "vega",
}


def expired_contract_row() -> dict[str, object]:
    """An IO contract the lake no longer dates (before 2025-12-22): null list and expiry dates."""
    return {
        "symbol": "IO2403C3500.CFE",
        "exchange_code": "IO2403-C-3500",
        "exchange": "CFE",
        "product": "IO",
        "product_name": "沪深300股指期权",
        "underlying_kind": "index",
        "underlying_symbol": "000300.SH",
        "option_type": "C",
        "exercise_style": "european",
        "strike": 3500.0,
        "multiplier": 100.0,
        "tick_size": 0.2,
        "expiry_date": None,
        "expiry_month": date(2024, 3, 1),
        "list_date": None,
        "first_seen_date": date(2023, 11, 1),
        "last_seen_date": date(2024, 3, 15),
        "dates_basis": "observed_truncated",
        "source": "futures_exchange",
        "data_version": "v1",
        "fetched_at": FETCHED_AT,
    }


def bar_row() -> dict[str, object]:
    return {
        "symbol": "IO2403C3500.CFE",
        "exchange_code": "IO2403-C-3500",
        "exchange": "CFE",
        "product": "IO",
        "underlying_symbol": "000300.SH",
        "option_type": "C",
        "strike": 3500.0,
        "trade_date": date(2024, 3, 15),
        "open": 54.0,
        "high": 56.0,
        "low": 53.0,
        "close": 54.4,
        "settle": 54.21,
        "pre_settle": 71.8,
        "volume": 8343,
        "open_interest": 0,
        "exercise_volume": 0,
        "oi_change": -2835,
        "amount": None,
        "implied_vol": None,
        "series_implied_vol": None,
        "delta": None,
        "source": "futures_exchange",
        "data_version": "v1",
        "fetched_at": FETCHED_AT,
    }


def greek_row() -> dict[str, object]:
    return {
        "symbol": "IO2403C3500.CFE",
        "underlying_symbol": "000300.SH",
        "trade_date": date(2024, 3, 15),
        "status": "no_expiry",
        "model": "black76",
        "rate": None,
        "rate_source": "fallback_constant",
        "forward_source": "parity",
        "time_to_expiry": None,
        "underlying_price": None,
        "iv": None,
        "delta": None,
        "gamma": None,
        "vega": None,
        "theta": None,
        "rho": None,
        "source": "derived",
        "data_version": "v1",
        "fetched_at": FETCHED_AT,
    }


@pytest.mark.parametrize(
    ("model", "columns"),
    [
        (OptionContract, CONTRACT_COLUMNS),
        (OptionBar, BAR_COLUMNS),
        (OptionGreek, GREEK_COLUMNS),
    ],
)
def test_option_row_fields_equal_the_lake_contract(model: type, columns: set[str]) -> None:
    assert set(model.model_fields) == columns


def test_option_contract_keeps_source_strings_and_null_dates() -> None:
    contract = OptionContract.model_validate(expired_contract_row())
    assert contract.symbol == "IO2403C3500.CFE"
    assert contract.exchange_code == "IO2403-C-3500"
    assert contract.exchange is Exchange.CFFEX
    assert contract.list_date is None and contract.expiry_date is None
    assert contract.dates_basis == "observed_truncated"


def test_option_bar_missing_numeric_is_nan() -> None:
    bar = OptionBar.model_validate(bar_row())
    assert math.isnan(bar.delta) and math.isnan(bar.implied_vol) and math.isnan(bar.amount)
    assert bar.volume == 8343.0 and bar.settle == 54.21


def test_option_row_rejects_unknown_column() -> None:
    with pytest.raises(ValidationError, match="margin_rate"):
        OptionContract.model_validate({**expired_contract_row(), "margin_rate": 0.12})


def test_option_greek_keeps_incomplete_status() -> None:
    greek = OptionGreek.model_validate(greek_row())
    assert greek.status == "no_expiry" and greek.model == "black76"
    assert math.isnan(greek.delta) and math.isnan(greek.rate)


def test_exchange_from_lake_code_maps_cfe() -> None:
    assert exchange_from_code("CFE") is Exchange.CFFEX
    assert exchange_from_code("SHFE") is Exchange.SHFE
    assert exchange_from_code(Exchange.DCE) is Exchange.DCE
    with pytest.raises(ValueError, match="MARS"):
        exchange_from_code("MARS")


def test_option_internal_symbol_matches_the_cffex_pattern() -> None:
    internal = option_internal_symbol("HO2311-C-2125", "CFE")
    assert internal == "CFFEX.HO2311-C-2125"
    assert normalize_symbol_case("HO2311-C-2125", Exchange.CFFEX) == "HO2311-C-2125"
