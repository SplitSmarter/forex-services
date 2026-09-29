import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.config import (
    ENABLE_DB_SCHEMA_INIT,
    get_request_logger,
)
from src.database.forex_connection import BaseForex, engine_forex


async def initialize_database_schemas(logger: logging.Logger) -> None:
    """Initialize database schemas for forex service."""
    if not ENABLE_DB_SCHEMA_INIT:
        logger.info("Database schema initialization is disabled via ENABLE_DB_SCHEMA_INIT.")
        return

    logger.info("Initializing database schemas...")
    
    async with engine_forex.begin() as conn:
        await conn.run_sync(BaseForex.metadata.create_all)
    
    logger.info("Database schemas initialized successfully.")


async def dispose_database_engines(logger: logging.Logger) -> None:
    """Dispose of database connection pools."""
    logger.info("Disposing database connection pool...")
    try:
        await engine_forex.dispose()
        logger.debug("Disposed engine pool: engine_forex")
    except Exception as e:
        logger.error(f"Failed to dispose engine: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for forex service startup and shutdown."""
    logger = get_request_logger()
    logger.info("Starting forex service lifespan...")

    try:
        # Initialize database schemas
        await initialize_database_schemas(logger)
        
        logger.info("Forex service startup completed successfully.")
        
        yield  # --- APPLICATION SERVES REQUESTS HERE ---

    except Exception as e:
        logger.error(f"Error during forex service startup: {e}")
        raise
    finally:
        logger.info("Executing forex service graceful shutdown...")
        
        # Dispose database engines
        await dispose_database_engines(logger)
        
        logger.info("Forex service lifespan shutdown completed successfully.")