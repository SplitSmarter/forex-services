from enum import Enum


class SuccessCode(str, Enum):
    SUCCESS = "response.success"
    EXCHANGE_RATE_RETRIEVED = "response.forex.exchange_rate_retrieved"
    CURRENCY_CONVERTED = "response.forex.currency_converted"
    HISTORICAL_RATE_RETRIEVED = "response.forex.historical_rate_retrieved"
    RATES_REFRESHED = "response.forex.rates_refreshed"
    CURRENCIES_RETRIEVED = "response.forex.currencies_retrieved"
