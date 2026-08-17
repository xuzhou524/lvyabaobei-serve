from datetime import timedelta

from jose import jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User
from app.time_utils import beijing_now, beijing_now_ms

USER_STATUS_ACTIVE = "active"
USER_STATUS_DELETED = "deleted"


def create_access_token(user_id: int) -> str:
    expire = beijing_now() + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def get_user_by_email(db: Session, email: str) -> User | None:
    normalized = email.strip().lower()
    return (
        db.query(User)
        .filter(User.email == normalized, User.status == USER_STATUS_ACTIVE)
        .first()
    )


def get_user_by_phone(db: Session, phone: str) -> User | None:
    return (
        db.query(User)
        .filter(User.phone == phone, User.status == USER_STATUS_ACTIVE)
        .first()
    )


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def get_active_user_by_id(db: Session, user_id: int) -> User | None:
    return (
        db.query(User)
        .filter(User.id == user_id, User.status == USER_STATUS_ACTIVE)
        .first()
    )


def deactivate_user(db: Session, user: User) -> None:
    """逻辑注销：标记状态并释放手机号/邮箱，便于同号重新注册为新账号。"""
    now = beijing_now_ms()
    user.status = USER_STATUS_DELETED
    user.deleted_at = now
    user.phone = f"{user.phone}__deleted__{user.id}"
    user.email = f"{user.email}__deleted__{user.id}"
    db.commit()


def normalize_email(email: str) -> str:
    return email.strip().lower()
