import math
from datetime import date, datetime

from joseph_api import Bar, Exchange, Fee, Margin, Settlement, Tick


def test_bar_missing_volume_is_nan():
    bar = Bar(
        symbol="IF2412",
        exchange=Exchange.CFFEX,
        start=datetime(2024, 1, 2, 9, 30),
        end=datetime(2024, 1, 2, 9, 35),
        open=1.0,
        high=2.0,
        low=0.5,
        close=1.5,
    )
    assert math.isnan(bar.volume) and math.isnan(bar.open_interest)


def test_account_dtos_carry_provenance():
    s = Settlement(symbol="IF2412", trade_date=date(2024, 1, 2), settlement_price=1.5)
    m = Margin(
        symbol="IF2412", trade_date=date(2024, 1, 2), margin_rate_long=0.12, margin_rate_short=0.12
    )
    fee = Fee(
        symbol="IF2412",
        trade_date=date(2024, 1, 2),
        fee_open=0.3e-4,
        fee_close=0.3e-4,
        fee_close_today=3.45e-4,
    )
    assert (s.settlement_price, m.provenance, fee.fee_unit) == (1.5, "declared", "per_lot")


def test_tick_nan_sides():
    t = Tick(symbol="IF2412", exchange=Exchange.CFFEX, ts=datetime(2024, 1, 2, 9, 30), last=1.0)
    assert math.isnan(t.bid) and math.isnan(t.ask)
