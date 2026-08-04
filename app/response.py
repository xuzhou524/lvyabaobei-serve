from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int
    data: T | None = None
    message: str


def success(data: T, message: str = "成功") -> ApiResponse[T]:
    return ApiResponse(code=200, data=data, message=message)


def fail(code: int, message: str, data: T | None = None) -> ApiResponse[T]:
    return ApiResponse(code=code, data=data, message=message)
