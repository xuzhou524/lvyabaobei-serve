from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.database import Base, engine
from app.exceptions import BusinessException
from app.handlers import (
    business_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.response import ApiResponse, success
from app.routers import auth, children, family, growth, rewards, tasks, user

Base.metadata.create_all(bind=engine)

app = FastAPI(title="绿芽宝贝 API", version="1.0.0")

app.add_exception_handler(BusinessException, business_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)

app.include_router(auth.router)
app.include_router(user.router)
app.include_router(children.router)
app.include_router(tasks.router)
app.include_router(growth.router)
app.include_router(rewards.router)
app.include_router(family.router)


@app.get("/health", response_model=ApiResponse[dict])
def health():
    from app.config import settings

    return success({"status": "ok", "database_url": settings.database_url})
