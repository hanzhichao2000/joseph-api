"""Market and account DTOs. Missing numeric values are float('nan'), never pd.NA."""

from __future__ import annotations

import math
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator

from joseph_api.enums import Exchange


def _require_finite_or_nan(value: float) -> float:
    if isinstance(value, float) and math.isnan(value):
        return value
    return float(value)


class _Dto(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Bar(_Dto):
    symbol: str
    exchange: Exchange
    start: datetime
    end: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = math.nan
    open_interest: float = math.nan
    freq: str = "1d"

    @field_validator("volume", "open_interest", mode="before")
    @classmethod
    def _numeric(cls, v: object) -> float:
        return _require_finite_or_nan(v)  # type: ignore[arg-type]


class Tick(_Dto):
    symbol: str
    exchange: Exchange
    ts: datetime
    last: float = math.nan
    bid: float = math.nan
    ask: float = math.nan
    bid_volume: float = math.nan
    ask_volume: float = math.nan
    volume: float = math.nan
    open_interest: float = math.nan


class Settlement(_Dto):
    symbol: str
    trade_date: date
    settlement_price: float
    prev_settlement: float = math.nan


class Margin(_Dto):
    symbol: str
    trade_date: date
    margin_rate_long: float
    margin_rate_short: float
    margin_per_lot: float = math.nan
    provenance: str = "declared"


class Fee(_Dto):
    symbol: str
    trade_date: date
    fee_open: float
    fee_close: float
    fee_close_today: float
    fee_unit: str = "per_lot"
    provenance: str = "declared"
