import logging
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_request_logger
from src.database.forex_connection import get_forex_db
from src.dto.base import SuccessResponse
from src.dto.forex.exchange_rate import (
    ConvertAtTimeRequest,
    ConvertHistoricalRequest,
    CurrenciesResponse,
    CurrencyConversionRequest,
    CurrencyConversionResponse,
    ExchangeRateDetails,
    HistoricalRateDetails,
)
from src.schemas.error_codes import ErrorCode, get_error_http_exception
from src.schemas.success_codes import SuccessCode
from src.services.forex.forex_service import ForexService

router = APIRouter(tags=["forex"], prefix="/v1")


@router.get("/rates/latest", response_model=SuccessResponse[ExchangeRateDetails, None])
async def get_latest_exchange_rate(
    db: AsyncSession = Depends(get_forex_db),
    logger: logging.Logger = Depends(get_request_logger),
):
    """Get the latest exchange rates (auto-refresh if stale)."""
    try:
        rate_details = await ForexService.get_latest_exchange_rate(db, logger)
        return SuccessResponse[ExchangeRateDetails, None](
            message=SuccessCode.EXCHANGE_RATE_RETRIEVED.value,
            data=rate_details,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to get latest exchange rate")
        raise get_error_http_exception(ErrorCode.SERVICE_INTERNAL_SERVER_ERROR)


@router.get("/rates/at-time", response_model=SuccessResponse[ExchangeRateDetails, None])
async def get_rate_at_time(
    timestamp: datetime = Query(..., description="Timestamp in ISO-8601 format"),
    db: AsyncSession = Depends(get_forex_db),
    logger: logging.Logger = Depends(get_request_logger),
):
    """Get exchange rate closest to a specific time (timestamp <= target)."""
    try:
        rate_details = await ForexService.get_rate_at_datetime(timestamp, db, logger)
        return SuccessResponse[ExchangeRateDetails, None](
            message=SuccessCode.EXCHANGE_RATE_RETRIEVED.value,
            data=rate_details,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to get rate at time")
        raise get_error_http_exception(ErrorCode.SERVICE_INTERNAL_SERVER_ERROR)


@router.get(
    "/rates/historical",
    response_model=SuccessResponse[HistoricalRateDetails, None],
)
async def get_historical_rate(
    date: date = Query(..., description="Date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_forex_db),
    logger: logging.Logger = Depends(get_request_logger),
):
    """Get historical exchange rate for a specific date."""
    try:
        rate_details = await ForexService.get_historical_rate(date, db, logger)
        return SuccessResponse[HistoricalRateDetails, None](
            message=SuccessCode.HISTORICAL_RATE_RETRIEVED.value,
            data=rate_details,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to get historical rate")
        raise get_error_http_exception(ErrorCode.SERVICE_INTERNAL_SERVER_ERROR)


@router.post("/rates/refresh", response_model=SuccessResponse[ExchangeRateDetails, None])
async def refresh_rates(
    db: AsyncSession = Depends(get_forex_db),
    logger: logging.Logger = Depends(get_request_logger),
):
    """Manually refresh exchange rates from external APIs."""
    try:
        rate_details = await ForexService.refresh_rates(db, logger)
        return SuccessResponse[ExchangeRateDetails, None](
            message=SuccessCode.RATES_REFRESHED.value,
            data=rate_details,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to refresh rates")
        raise get_error_http_exception(ErrorCode.EXTERNAL_API_ERROR)


@router.post("/convert", response_model=SuccessResponse[CurrencyConversionResponse, None])
async def convert_currency(
    data: CurrencyConversionRequest,
    db: AsyncSession = Depends(get_forex_db),
    logger: logging.Logger = Depends(get_request_logger),
):
    """Convert amount using the latest exchange rates."""
    try:
        response = await ForexService.convert_amount(
            amount=data.amount,
            from_currency=data.from_currency,
            to_currency=data.to_currency,
            db=db,
            logger=logger,
        )
        return SuccessResponse[CurrencyConversionResponse, None](
            message=SuccessCode.CURRENCY_CONVERTED.value,
            data=response,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to convert currency")
        raise get_error_http_exception(ErrorCode.SERVICE_INTERNAL_SERVER_ERROR)


@router.post(
    "/convert/at-time",
    response_model=SuccessResponse[CurrencyConversionResponse, None],
)
async def convert_currency_at_time(
    data: ConvertAtTimeRequest,
    db: AsyncSession = Depends(get_forex_db),
    logger: logging.Logger = Depends(get_request_logger),
):
    """Convert amount using the rate snapshot closest to the given timestamp."""
    try:
        response = await ForexService.convert_amount_at_time(
            amount=data.amount,
            from_currency=data.from_currency,
            to_currency=data.to_currency,
            target_time=data.timestamp,
            db=db,
            logger=logger,
        )
        return SuccessResponse[CurrencyConversionResponse, None](
            message=SuccessCode.CURRENCY_CONVERTED.value,
            data=response,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to convert currency at time")
        raise get_error_http_exception(ErrorCode.SERVICE_INTERNAL_SERVER_ERROR)


@router.post(
    "/convert/historical",
    response_model=SuccessResponse[CurrencyConversionResponse, None],
)
async def convert_currency_historical(
    data: ConvertHistoricalRequest,
    db: AsyncSession = Depends(get_forex_db),
    logger: logging.Logger = Depends(get_request_logger),
):
    """Convert amount using the daily historical rate for a date."""
    try:
        response = await ForexService.convert_amount_historical(
            amount=data.amount,
            from_currency=data.from_currency,
            to_currency=data.to_currency,
            target_date=data.date,
            db=db,
            logger=logger,
        )
        return SuccessResponse[CurrencyConversionResponse, None](
            message=SuccessCode.CURRENCY_CONVERTED.value,
            data=response,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to convert currency historically")
        raise get_error_http_exception(ErrorCode.SERVICE_INTERNAL_SERVER_ERROR)


@router.get("/currencies", response_model=SuccessResponse[CurrenciesResponse, None])
async def list_currencies(
    logger: logging.Logger = Depends(get_request_logger),
):
    """List supported ISO currency codes."""
    try:
        response = ForexService.list_currencies()
        return SuccessResponse[CurrenciesResponse, None](
            message=SuccessCode.CURRENCIES_RETRIEVED.value,
            data=response,
        )
    except Exception:
        logger.exception("Failed to list currencies")
        raise get_error_http_exception(ErrorCode.SERVICE_INTERNAL_SERVER_ERROR)
