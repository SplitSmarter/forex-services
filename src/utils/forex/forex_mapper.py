from datetime import date, datetime
from typing import Any

from sqlalchemy import inspect as sa_inspect

from src.constant.db.forex import Currency
from src.dto.forex.exchange_rate import (
    CurrencyConversionResponse,
    ExchangeRateDetails,
    HistoricalRateDetails,
)
from src.models.forex import DailyExchangeRate, ExchangeRate

_METADATA_COLUMNS = {"id", "source", "created_on", "timestamp", "date"}


def _currency_rate_dict(model: Any) -> dict[str, float]:
    """Extract ISO currency rate columns from an ORM model."""
    mapper = sa_inspect(model.__class__)
    rates: dict[str, float] = {}
    for column in mapper.columns:
        name = column.key
        if name in _METADATA_COLUMNS:
            continue
        value = getattr(model, name, None)
        if value is not None:
            rates[name] = float(value)
    return rates


def map_exchange_rate_to_details(exchange_rate: ExchangeRate) -> ExchangeRateDetails:
    source = (
        exchange_rate.source.value
        if hasattr(exchange_rate.source, "value")
        else str(exchange_rate.source)
    )
    rates = _currency_rate_dict(exchange_rate)
    return ExchangeRateDetails(
        source=source,
        timestamp=exchange_rate.timestamp,
        created_on=getattr(exchange_rate, "created_on", None),
        **rates,
    )


def map_daily_rate_to_details(daily_rate: DailyExchangeRate) -> HistoricalRateDetails:
    source = (
        daily_rate.source.value
        if hasattr(daily_rate.source, "value")
        else str(daily_rate.source)
    )
    rates = _currency_rate_dict(daily_rate)
    return HistoricalRateDetails(
        source=source,
        date=daily_rate.date,
        **rates,
    )


def map_conversion_response(
    *,
    converted_amount: float,
    rate_from: float,
    rate_to: float,
    original_amount: float,
    from_currency: Currency,
    to_currency: Currency,
    source: str | None = None,
    rate_timestamp: datetime | None = None,
    rate_date: date | None = None,
) -> CurrencyConversionResponse:
    return CurrencyConversionResponse(
        converted_amount=converted_amount,
        rate_from=rate_from,
        rate_to=rate_to,
        original_amount=original_amount,
        from_currency=from_currency,
        to_currency=to_currency,
        source=source,
        rate_timestamp=rate_timestamp,
        rate_date=rate_date,
    )
