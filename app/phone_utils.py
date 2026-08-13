import re

from app.exceptions import BusinessException

_PHONE_PATTERN = re.compile(r"^1\d{10}$")


def normalize_phone(phone: str) -> str:
    normalized = re.sub(r"\D", "", phone.strip())
    if normalized.startswith("86") and len(normalized) == 13:
        normalized = normalized[2:]
    return normalized


def validate_phone(phone: str) -> str:
    normalized = normalize_phone(phone)
    if not _PHONE_PATTERN.match(normalized):
        raise BusinessException(422, "请输入有效的 11 位手机号")
    return normalized


def mask_phone(phone: str) -> str:
    normalized = normalize_phone(phone)
    if len(normalized) != 11:
        return phone
    return f"{normalized[:3]}****{normalized[-4:]}"
