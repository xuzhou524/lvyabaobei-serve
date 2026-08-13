
from sqlalchemy.orm import Session

from app.auth import get_user_by_email, get_user_by_phone, normalize_email
from app.exceptions import BusinessException
from app.phone_utils import validate_phone


def assert_phone_available(db: Session, phone: str) -> str:
    normalized = validate_phone(phone)
    if get_user_by_phone(db, normalized):
        raise BusinessException(409, "该手机号已注册")
    return normalized


def assert_email_available_for_register(db: Session, email: str) -> str:
    normalized = normalize_email(email)
    if get_user_by_email(db, normalized):
        raise BusinessException(409, "该邮箱已注册")
    return normalized
