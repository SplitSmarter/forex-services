import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.constant.db.forex import Currency
from src.core.config import RATE_REFRESH_INTERVAL_HOURS, get_logger
from src.database.dao.forex_dao import ForexDAO
from src.models.forex import DailyExchangeRate, ExchangeRate
from src.utils.forex.external import fetch_historical_from_exchange_rate, fetch_latest_rates


def _ensure_aware_utc(value: datetime) -> datetime:
    """Normalize datetimes for safe age comparisons."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _is_rate_stale(latest_rate: ExchangeRate | None) -> bool:
    if latest_rate is None:
        return True
    created_on = _ensure_aware_utc(latest_rate.created_on)
    age = datetime.now(timezone.utc) - created_on
    return age > timedelta(hours=RATE_REFRESH_INTERVAL_HOURS)


async def convert_currency(
    amount1: float,
    from_currency: Currency,
    to_currency: Currency,
    db_currency: AsyncSession,
    logger: logging.Logger = None,
):
    """Convert amount from one currency to another using latest exchange rates."""
    if logger is None:
        logger = get_logger()

    currency_codes = [c.name for c in Currency]
    if from_currency.name not in currency_codes or to_currency.name not in currency_codes:
        logger.debug("Unsupported currency code")
        raise ValueError("Unsupported currency.")

    latest_rate = await ForexDAO.get_latest_exchange_rate(db_currency, logger)

    if _is_rate_stale(latest_rate):
        await fetch_latest_rates(db_currency, logger)
        latest_rate = await ForexDAO.get_latest_exchange_rate(db_currency, logger)

    if latest_rate is None:
        raise ValueError("Error while querying latest rate")

    rate_from = getattr(latest_rate, from_currency.name, None)
    rate_to = getattr(latest_rate, to_currency.name, None)

    if rate_from is None or rate_to is None:
        logger.debug(
            f"Missing exchange rate for {from_currency.name} or {to_currency.name}"
        )
        raise ValueError(
            f"Missing exchange rate for {from_currency.name} or {to_currency.name}"
        )

    amount_in_inr = amount1 / rate_from
    converted_amount = amount_in_inr * rate_to
    return converted_amount, rate_from, rate_to, latest_rate


async def get_latest_rate(
    db_currency: AsyncSession, logger: logging.Logger = None
) -> ExchangeRate:
    """Get the latest exchange rate, fetching from API if needed."""
    if logger is None:
        logger = get_logger()

    latest_rate = await ForexDAO.get_latest_exchange_rate(db_currency, logger)

    if _is_rate_stale(latest_rate):
        await fetch_latest_rates(db_currency, logger)
        latest_rate = await ForexDAO.get_latest_exchange_rate(db_currency, logger)

    if latest_rate is None:
        raise ValueError("Error while querying latest rate")

    return latest_rate


async def get_rate_at_time(
    db_currency: AsyncSession,
    target_time: datetime,
    logger: logging.Logger = None,
) -> ExchangeRate | None:
    """Get the exchange rate closest to a specific time."""
    if logger is None:
        logger = get_logger()

    target_time = _ensure_aware_utc(target_time)
    return await ForexDAO.get_exchange_rate_at_time(db_currency, target_time, logger)


async def convert_currency_exchange_rate(
    amount1: float,
    from_currency: Currency,
    to_currency: Currency,
    exchange_rate: ExchangeRate | DailyExchangeRate,
    logger: logging.Logger = None,
):
    """Convert amount using a specific exchange rate object."""
    if logger is None:
        logger = get_logger()

    rate_from = getattr(exchange_rate, from_currency.name, None)
    rate_to = getattr(exchange_rate, to_currency.name, None)

    if rate_from is None or rate_to is None:
        logger.debug(
            f"Missing exchange rate for {from_currency.name} or {to_currency.name}"
        )
        raise ValueError(
            f"Missing exchange rate for {from_currency.name} or {to_currency.name}"
        )

    amount_in_inr = amount1 / rate_from
    converted_amount = amount_in_inr * rate_to
    return converted_amount, rate_from, rate_to


async def convert_currency_historical(
    amount: float,
    from_currency: Currency,
    to_currency: Currency,
    target_date: date,
    db_currency: AsyncSession,
    logger: logging.Logger = None,
):
    """Convert currency based on a specific date's daily reference rate."""
    if logger is None:
        logger = get_logger()

    daily_rate = await get_daily_rate(db_currency, target_date, logger)
    converted_amount, rate_from, rate_to = await convert_currency_exchange_rate(
        amount, from_currency, to_currency, daily_rate, logger
    )
    return converted_amount, rate_from, rate_to, daily_rate


async def get_daily_rate(
    db_currency: AsyncSession,
    target_date: date,
    logger: logging.Logger = None,
) -> DailyExchangeRate:
    """Retrieves the static daily rate for a specific date.

    Triggers a fetch if the date is missing.
    """
    if logger is None:
        logger = get_logger()

    rate = await ForexDAO.get_daily_exchange_rate(db_currency, target_date, logger)

    if not rate:
        await fetch_historical_from_exchange_rate(db_currency, target_date, logger)
        rate = await ForexDAO.get_daily_exchange_rate(db_currency, target_date, logger)

    if not rate:
        logger.error(f"Failed to obtain daily rate for {target_date}")
        raise ValueError(f"Rate for date {target_date} is unavailable.")

    return rate
