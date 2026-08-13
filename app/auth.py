from datetime import timedelta

from jose import jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User
from app.time_utils import beijing_now


def create_access_token(user_id: int) -> str:
    expire = beijing_now() + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def get_user_by_email(db: Session, email: str) -> User | None:
    normalized = email.strip().lower()
    return db.query(User).filter(User.email == normalized).first()


def get_user_by_phone(db: Session, phone: str) -> User | None:
    return db.query(User).filter(User.phone == phone).first()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def normalize_email(email: str) -> str:
    return email.strip().lower()
