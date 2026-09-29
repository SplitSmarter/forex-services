import enum

from fastapi import HTTPException
from starlette import status

from src.dto.base import ErrorResponse


class ErrorCode(enum.Enum):
    REQUEST_BAD_REQUEST = "error.request.bad_request"
    REQUEST_VALIDATION_ERROR = "error.request.validation_error"
    REQUEST_INVALID_INPUT = "error.request.invalid_input"

    UNSUPPORTED_CURRENCY = "error.forex.unsupported_currency"
    MISSING_EXCHANGE_RATE = "error.forex.missing_exchange_rate"
    INVALID_DATE_FORMAT = "error.forex.invalid_date_format"
    INVALID_TIMESTAMP_FORMAT = "error.forex.invalid_timestamp_format"
    RATE_NOT_AVAILABLE = "error.forex.rate_not_available"
    EXTERNAL_API_ERROR = "error.forex.external_api_error"

    SERVICE_INTERNAL_SERVER_ERROR = "error.service.internal_server_error"
    SERVICE_DEPENDENCY_ERROR = "error.service.dependency_error"


class ErrorHTTPStatus(enum.Enum):
    REQUEST_BAD_REQUEST = status.HTTP_400_BAD_REQUEST
    REQUEST_VALIDATION_ERROR = status.HTTP_422_UNPROCESSABLE_ENTITY
    REQUEST_INVALID_INPUT = status.HTTP_400_BAD_REQUEST
    UNSUPPORTED_CURRENCY = status.HTTP_400_BAD_REQUEST
    MISSING_EXCHANGE_RATE = status.HTTP_400_BAD_REQUEST
    INVALID_DATE_FORMAT = status.HTTP_400_BAD_REQUEST
    INVALID_TIMESTAMP_FORMAT = status.HTTP_400_BAD_REQUEST
    RATE_NOT_AVAILABLE = status.HTTP_404_NOT_FOUND
    EXTERNAL_API_ERROR = status.HTTP_502_BAD_GATEWAY
    SERVICE_INTERNAL_SERVER_ERROR = status.HTTP_500_INTERNAL_SERVER_ERROR
    SERVICE_DEPENDENCY_ERROR = status.HTTP_424_FAILED_DEPENDENCY


def get_error_http_exception(code: ErrorCode, message: str | None = None) -> HTTPException:
    """Return a standardized FastAPI HTTPException for the given error code."""
    return HTTPException(
        status_code=ErrorHTTPStatus[code.name].value,
        detail=ErrorResponse(
            error=code.value,
            message=message or code.value,
        ).model_dump(),
    )
