import re

import bcrypt

from app.exceptions import BusinessException

_PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,32}$")


def validate_password_strength(password: str) -> str:
    if not _PASSWORD_PATTERN.match(password):
        raise BusinessException(422, "密码须为 8–32 位，且同时包含字母和数字")
    return password


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    return bcrypt.checkpw(password.encode(), hashed.encode())
