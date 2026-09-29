import logging
from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.constant.db.forex import Currency
from src.core.config import get_logger
from src.dto.forex.exchange_rate import (
    CurrenciesResponse,
    CurrencyConversionResponse,
    ExchangeRateDetails,
    HistoricalRateDetails,
)
from src.schemas.error_codes import ErrorCode, get_error_http_exception
from src.utils.forex.currency import (
    convert_currency,
    convert_currency_exchange_rate,
    convert_currency_historical,
    get_daily_rate,
    get_latest_rate,
    get_rate_at_time,
)
from src.utils.forex.external import fetch_latest_rates
from src.utils.forex.forex_mapper import (
    map_conversion_response,
    map_daily_rate_to_details,
    map_exchange_rate_to_details,
)


class ForexService:
    """Service layer for forex operations."""

    @staticmethod
    async def get_latest_exchange_rate(
        db: AsyncSession, logger: logging.Logger = None
    ) -> ExchangeRateDetails:
        if logger is None:
            logger = get_logger()
        try:
            exchange_rate = await get_latest_rate(db, logger)
            return map_exchange_rate_to_details(exchange_rate)
        except ValueError as e:
            logger.error(f"Failed to get latest exchange rate: {e}")
            raise get_error_http_exception(ErrorCode.RATE_NOT_AVAILABLE, str(e))
        except Exception as e:
            logger.exception(f"External API error while fetching latest rate: {e}")
            raise get_error_http_exception(ErrorCode.EXTERNAL_API_ERROR, str(e))

    @staticmethod
    async def convert_amount(
        amount: float,
        from_currency: Currency,
        to_currency: Currency,
        db: AsyncSession,
        logger: logging.Logger = None,
    ) -> CurrencyConversionResponse:
        if logger is None:
            logger = get_logger()
        try:
            converted_amount, rate_from, rate_to, latest_rate = await convert_currency(
                amount, from_currency, to_currency, db, logger
            )
            source = (
                latest_rate.source.value
                if hasattr(latest_rate.source, "value")
                else str(latest_rate.source)
            )
            return map_conversion_response(
                converted_amount=converted_amount,
                rate_from=rate_from,
                rate_to=rate_to,
                original_amount=amount,
                from_currency=from_currency,
                to_currency=to_currency,
                source=source,
                rate_timestamp=latest_rate.timestamp,
            )
        except ValueError as e:
            message = str(e)
            if "Unsupported currency" in message:
                raise get_error_http_exception(ErrorCode.UNSUPPORTED_CURRENCY, message)
            if "Missing exchange rate" in message:
                raise get_error_http_exception(ErrorCode.MISSING_EXCHANGE_RATE, message)
            raise get_error_http_exception(ErrorCode.RATE_NOT_AVAILABLE, message)
        except Exception as e:
            logger.exception(f"Failed to convert currency: {e}")
            raise get_error_http_exception(ErrorCode.EXTERNAL_API_ERROR, str(e))

    @staticmethod
    async def convert_amount_at_time(
        amount: float,
        from_currency: Currency,
        to_currency: Currency,
        target_time: datetime,
        db: AsyncSession,
        logger: logging.Logger = None,
    ) -> CurrencyConversionResponse:
        if logger is None:
            logger = get_logger()
        try:
            exchange_rate = await get_rate_at_time(db, target_time, logger)
            if not exchange_rate:
                raise get_error_http_exception(ErrorCode.RATE_NOT_AVAILABLE)

            converted_amount, rate_from, rate_to = await convert_currency_exchange_rate(
                amount, from_currency, to_currency, exchange_rate, logger
            )
            source = (
                exchange_rate.source.value
                if hasattr(exchange_rate.source, "value")
                else str(exchange_rate.source)
            )
            return map_conversion_response(
                converted_amount=converted_amount,
                rate_from=rate_from,
                rate_to=rate_to,
                original_amount=amount,
                from_currency=from_currency,
                to_currency=to_currency,
                source=source,
                rate_timestamp=exchange_rate.timestamp,
            )
        except ValueError as e:
            message = str(e)
            if "Unsupported currency" in message:
                raise get_error_http_exception(ErrorCode.UNSUPPORTED_CURRENCY, message)
            if "Missing exchange rate" in message:
                raise get_error_http_exception(ErrorCode.MISSING_EXCHANGE_RATE, message)
            raise get_error_http_exception(ErrorCode.RATE_NOT_AVAILABLE, message)

    @staticmethod
    async def get_historical_rate(
        target_date: date,
        db: AsyncSession,
        logger: logging.Logger = None,
    ) -> HistoricalRateDetails:
        if logger is None:
            logger = get_logger()
        try:
            daily_rate = await get_daily_rate(target_date=target_date, db_currency=db, logger=logger)
            return map_daily_rate_to_details(daily_rate)
        except ValueError as e:
            logger.error(f"Historical rate unavailable: {e}")
            raise get_error_http_exception(ErrorCode.RATE_NOT_AVAILABLE, str(e))
        except Exception as e:
            logger.exception(f"Failed to fetch historical rate: {e}")
            raise get_error_http_exception(ErrorCode.EXTERNAL_API_ERROR, str(e))

    @staticmethod
    async def get_rate_at_datetime(
        target_time: datetime,
        db: AsyncSession,
        logger: logging.Logger = None,
    ) -> ExchangeRateDetails:
        if logger is None:
            logger = get_logger()
        exchange_rate = await get_rate_at_time(db, target_time, logger)
        if not exchange_rate:
            raise get_error_http_exception(ErrorCode.RATE_NOT_AVAILABLE)
        return map_exchange_rate_to_details(exchange_rate)

    @staticmethod
    async def convert_amount_historical(
        amount: float,
        from_currency: Currency,
        to_currency: Currency,
        target_date: date,
        db: AsyncSession,
        logger: logging.Logger = None,
    ) -> CurrencyConversionResponse:
        if logger is None:
            logger = get_logger()
        try:
            converted_amount, rate_from, rate_to, daily_rate = await convert_currency_historical(
                amount, from_currency, to_currency, target_date, db, logger
            )
            source = (
                daily_rate.source.value
                if hasattr(daily_rate.source, "value")
                else str(daily_rate.source)
            )
            return map_conversion_response(
                converted_amount=converted_amount,
                rate_from=rate_from,
                rate_to=rate_to,
                original_amount=amount,
                from_currency=from_currency,
                to_currency=to_currency,
                source=source,
                rate_date=daily_rate.date,
            )
        except ValueError as e:
            message = str(e)
            if "Unsupported currency" in message:
                raise get_error_http_exception(ErrorCode.UNSUPPORTED_CURRENCY, message)
            if "Missing exchange rate" in message:
                raise get_error_http_exception(ErrorCode.MISSING_EXCHANGE_RATE, message)
            raise get_error_http_exception(ErrorCode.RATE_NOT_AVAILABLE, message)
        except Exception as e:
            logger.exception(f"Failed historical conversion: {e}")
            raise get_error_http_exception(ErrorCode.EXTERNAL_API_ERROR, str(e))

    @staticmethod
    async def refresh_rates(
        db: AsyncSession, logger: logging.Logger = None
    ) -> ExchangeRateDetails:
        if logger is None:
            logger = get_logger()
        try:
            logger.info("Manual refresh of exchange rates requested")
            await fetch_latest_rates(db, logger)
            exchange_rate = await get_latest_rate(db, logger)
            return map_exchange_rate_to_details(exchange_rate)
        except Exception as e:
            logger.exception(f"Failed to refresh rates: {e}")
            raise get_error_http_exception(ErrorCode.EXTERNAL_API_ERROR, str(e))

    @staticmethod
    def list_currencies() -> CurrenciesResponse:
        return CurrenciesResponse(
            currencies=[currency.value for currency in Currency],
            base_currency=Currency.INR.value,
        )
