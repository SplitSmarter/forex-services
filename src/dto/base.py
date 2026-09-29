from typing import Generic, Optional, TypeVar

from src.dto.strict_base_model import StrictBaseModel

T = TypeVar("T")
M = TypeVar("M")


class SuccessResponse(StrictBaseModel, Generic[T, M]):
    success: bool = True
    message: Optional[str] = None
    data: Optional[T] = None
    pagination: Optional[M] = None
    meta: Optional[M] = None


class ErrorResponse(StrictBaseModel, Generic[T, M]):
    success: bool = False
    message: Optional[str] = None
    error: Optional[T] = None
    meta: Optional[M] = None
