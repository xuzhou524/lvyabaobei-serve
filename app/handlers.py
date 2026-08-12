from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions import BusinessException
from app.response import fail


def _validation_message(exc: RequestValidationError) -> str:
    for error in exc.errors():
        msg = error.get("msg", "")
        if msg.startswith("Value error, "):
            return msg.removeprefix("Value error, ")
        if msg:
            return msg
    return "请求参数校验失败"


async def business_exception_handler(_: Request, exc: BusinessException) -> JSONResponse:
    data = {"error_code": exc.error_code} if exc.error_code else None
    return JSONResponse(
        status_code=200,
        content=fail(exc.code, exc.message, data=data).model_dump(),
    )


async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content=fail(422, _validation_message(exc)).model_dump(),
    )


async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "请求失败"
    return JSONResponse(
        status_code=200,
        content=fail(exc.status_code, message).model_dump(),
    )
