from datetime import date

from pydantic import TypeAdapter

from joseph_api import AssetType, Exchange, Future, InstrumentRegistry, Option


def test_future_round_trips():
    f = Future(
        symbol="CFFEX.IF2412",
        exchange_symbol="IF2412",
        product="IF",
        exchange=Exchange.CFFEX,
        asset_type=AssetType.FUTURE,
        multiplier=300.0,
        margin_rate=0.12,
        tick_size=0.2,
        maturity_date=date(2024, 11, 15),
    )
    adapter = TypeAdapter(Future)
    assert adapter.validate_json(adapter.dump_json(f)) == f


def test_option_and_registry():
    o = Option(
        symbol="CFFEX.IO2412-C-4000",
        exchange_symbol="IO2412-C-4000",
        product="IO",
        exchange=Exchange.CFFEX,
        asset_type=AssetType.OPTION,
        underlying_symbol="IF2412",
        strike=4000.0,
        expiry=date(2024, 11, 15),
        multiplier=100.0,
        tick_size=0.2,
        option_type="call",
        margin_rate=0.12,
    )
    assert o.strike == 4000.0
    assert InstrumentRegistry() is not None
