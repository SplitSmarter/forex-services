import logging
from datetime import date, datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.forex import DailyExchangeRate, ExchangeRate


class ForexDAO:
    """Data Access Object for forex-related database operations."""

    @staticmethod
    async def get_latest_exchange_rate(
        db: AsyncSession, logger: logging.Logger
    ) -> Optional[ExchangeRate]:
        """Get the most recent exchange rate from the database."""
        try:
            stmt = select(ExchangeRate).order_by(ExchangeRate.timestamp.desc())
            result = await db.execute(stmt)
            return result.scalars().first()
        except Exception as e:
            logger.error(f"Error fetching latest exchange rate: {e}")
            raise

    @staticmethod
    async def get_exchange_rate_at_time(
        db: AsyncSession, target_time: datetime, logger: logging.Logger
    ) -> Optional[ExchangeRate]:
        """Get the exchange rate closest to a specific time (not after the time)."""
        try:
            stmt = (
                select(ExchangeRate)
                .where(ExchangeRate.timestamp <= target_time)
                .order_by(ExchangeRate.timestamp.desc())
            )
            result = await db.execute(stmt)
            return result.scalars().first()
        except Exception as e:
            logger.error(f"Error fetching exchange rate at time {target_time}: {e}")
            raise

    @staticmethod
    async def get_daily_exchange_rate(
        db: AsyncSession, target_date: date, logger: logging.Logger
    ) -> Optional[DailyExchangeRate]:
        """Get the daily exchange rate for a specific date."""
        try:
            stmt = select(DailyExchangeRate).where(DailyExchangeRate.date == target_date)
            result = await db.execute(stmt)
            return result.scalars().first()
        except Exception as e:
            logger.error(f"Error fetching daily exchange rate for date {target_date}: {e}")
            raise

    @staticmethod
    async def save_exchange_rate(
        db: AsyncSession, exchange_rate: ExchangeRate, logger: logging.Logger
    ) -> ExchangeRate:
        """Save or merge an exchange rate to the database."""
        try:
            merged = await db.merge(exchange_rate)
            await db.flush()
            logger.info(f"Exchange rate saved with timestamp {exchange_rate.timestamp}")
            return merged
        except Exception as e:
            logger.error(f"Error saving exchange rate: {e}")
            await db.rollback()
            raise

    @staticmethod
    async def save_daily_exchange_rate(
        db: AsyncSession, daily_rate: DailyExchangeRate, logger: logging.Logger
    ) -> DailyExchangeRate:
        """Save or merge a daily exchange rate to the database."""
        try:
            merged = await db.merge(daily_rate)
            await db.flush()
            logger.info(f"Daily exchange rate saved for date {daily_rate.date}")
            return merged
        except Exception as e:
            logger.error(f"Error saving daily exchange rate: {e}")
            await db.rollback()
            raise
