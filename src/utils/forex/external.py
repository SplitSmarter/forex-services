import logging
from datetime import date, datetime, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from src.constant.db.forex import Currency, CurrencySources
from src.core.config import (
    CURRENCYLAYER_ACCESS_KEY,
    EXCHANGERATE_ACCESS_KEY,
    currency_layer_api_url,
    exchange_rate_api_url,
    get_logger,
)
from src.database.dao.forex_dao import ForexDAO
from src.models.forex import DailyExchangeRate, ExchangeRate

HTTP_TIMEOUT_SECONDS = 30.0


def _non_inr_currency_codes() -> list[str]:
    return [currency.name for currency in Currency if currency != Currency.INR]


def _validate_and_build_rates(
    rates_response: dict, currency_list: list[str], logger: logging.Logger
) -> dict[str, float]:
    missing = []
    rates: dict[str, float] = {}
    for currency in currency_list:
        value = rates_response.get(currency)
        if value is None:
            missing.append(currency)
        else:
            rates[currency] = float(value)

    if missing:
        logger.error(f"API response missing non-nullable fields: {missing}")
        raise ValueError(f"Missing mandatory rates from API: {missing}")

    return rates


async def fetch_from_exchange_rate(
    db: AsyncSession,
    logger: logging.Logger = None,
) -> None:
    """Fetch latest exchange rates from ExchangeRate API."""
    if logger is None:
        logger = get_logger()
    if not EXCHANGERATE_ACCESS_KEY:
        raise ValueError("EXCHANGERATE_ACCESS_KEY is not configured")

    logger.info("Fetching exchange rates from ExchangeRate API...")
    currency_list = _non_inr_currency_codes()
    url = f"{exchange_rate_api_url}/{EXCHANGERATE_ACCESS_KEY}/latest/INR"

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()

    if data.get("result") != "success":
        logger.error(f"Failed to fetch exchange rates from ExchangeRate API: {data}")
        raise Exception("Failed to fetch from ExchangeRate API")

    timestamp = datetime.fromtimestamp(data["time_last_update_unix"], tz=timezone.utc)
    rates = _validate_and_build_rates(data["conversion_rates"], currency_list, logger)

    new_exchange_rate = ExchangeRate(
        source=CurrencySources.EXCHANGE_RATE,
        timestamp=timestamp,
        INR=1.0,
        **rates,
    )
    await ForexDAO.save_exchange_rate(db, new_exchange_rate, logger)
    await db.commit()
    logger.info("Exchange rates from ExchangeRate API saved.")


async def fetch_from_currency_layer(
    db: AsyncSession,
    logger: logging.Logger = None,
) -> None:
    """Fetch latest exchange rates from CurrencyLayer API."""
    if logger is None:
        logger = get_logger()
    if not CURRENCYLAYER_ACCESS_KEY:
        raise ValueError("CURRENCYLAYER_ACCESS_KEY is not configured")

    logger.info("Fetching exchange rates from CurrencyLayer API...")
    currency_list = _non_inr_currency_codes()
    currency_param = ",".join(currency_list)

    url = (
        f"{currency_layer_api_url}?access_key={CURRENCYLAYER_ACCESS_KEY}"
        f"&source=INR&currencies={currency_param}&format=1"
    )

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()

    if not data.get("success"):
        logger.error(f"Failed to fetch from CurrencyLayer API: {data}")
        raise Exception("Failed to fetch from CurrencyLayer API")

    unix_ts = data.get("timestamp")
    if unix_ts is None:
        raise ValueError("CurrencyLayer response missing timestamp")
    timestamp = datetime.fromtimestamp(unix_ts, tz=timezone.utc)
    quotes = data.get("quotes") or {}

    rates_response = {}
    for currency in currency_list:
        key = f"INR{currency}"
        if key in quotes:
            rates_response[currency] = quotes[key]

    rates = _validate_and_build_rates(rates_response, currency_list, logger)

    new_exchange_rate = ExchangeRate(
        source=CurrencySources.CURRENCY_LAYER,
        timestamp=timestamp,
        INR=1.0,
        **rates,
    )
    await ForexDAO.save_exchange_rate(db, new_exchange_rate, logger)
    await db.commit()
    logger.info("Exchange rates from CurrencyLayer saved.")


async def fetch_latest_rates(
    db: AsyncSession,
    logger: logging.Logger = None,
) -> None:
    """Fetch latest rates, preferring ExchangeRate-API with CurrencyLayer fallback."""
    if logger is None:
        logger = get_logger()

    try:
        await fetch_from_exchange_rate(db, logger)
        return
    except Exception as primary_error:
        logger.warning(
            f"ExchangeRate-API fetch failed, trying CurrencyLayer fallback: {primary_error}"
        )

    try:
        await fetch_from_currency_layer(db, logger)
    except Exception as fallback_error:
        logger.error(f"CurrencyLayer fallback also failed: {fallback_error}")
        raise


async def fetch_historical_from_exchange_rate(
    db: AsyncSession,
    target_date: date,
    logger: logging.Logger = None,
) -> None:
    """Fetch historical daily rates from ExchangeRate API."""
    if logger is None:
        logger = get_logger()
    if not EXCHANGERATE_ACCESS_KEY:
        raise ValueError("EXCHANGERATE_ACCESS_KEY is not configured")

    date_str = target_date.strftime("%Y-%m-%d")
    logger.info(f"Fetching historical rates for {date_str} from ExchangeRate API...")

    currency_list = _non_inr_currency_codes()
    url = (
        f"{exchange_rate_api_url}/{EXCHANGERATE_ACCESS_KEY}/history/"
        f"INR/{target_date.year}/{target_date.month}/{target_date.day}"
    )

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()

    if data.get("result") != "success":
        logger.error(f"Failed to fetch historical rates from ExchangeRate API: {data}")
        raise Exception(f"Failed to fetch historical rates for {date_str}")

    rates = _validate_and_build_rates(data["conversion_rates"], currency_list, logger)

    new_daily_rate = DailyExchangeRate(
        source=CurrencySources.EXCHANGE_RATE,
        date=target_date,
        INR=1.0,
        **rates,
    )
    await ForexDAO.save_daily_exchange_rate(db, new_daily_rate, logger)
    await db.commit()
    logger.info(f"Daily rate for {date_str} saved.")
