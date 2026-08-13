import secrets

from sqlalchemy.orm import Session

from app.auth import normalize_email
from app.config import settings
from app.exceptions import BusinessException
from app.models import EmailVerificationCode
from app.time_utils import beijing_now_ms

Purpose = str  # "register" | "login"


def _latest_code(db: Session, email: str, purpose: Purpose) -> EmailVerificationCode | None:
    normalized = normalize_email(email)
    return (
        db.query(EmailVerificationCode)
        .filter(
            EmailVerificationCode.email == normalized,
            EmailVerificationCode.purpose == purpose,
        )
        .order_by(EmailVerificationCode.created_at.desc())
        .first()
    )


def assert_can_send_code(db: Session, email: str, purpose: Purpose) -> None:
    normalized = normalize_email(email)
    latest = _latest_code(db, normalized, purpose)
    if not latest:
        return

    elapsed_ms = beijing_now_ms() - latest.created_at
    if elapsed_ms < settings.verification_code_resend_seconds * 1000:
        remaining = settings.verification_code_resend_seconds - elapsed_ms // 1000
        raise BusinessException(429, f"发送过于频繁，请 {remaining} 秒后再试")


def save_verification_code(db: Session, email: str, code: str, purpose: Purpose) -> int:
    normalized = normalize_email(email)
    now_ms = beijing_now_ms()
    expires_at = now_ms + settings.verification_code_expire_minutes * 60 * 1000

    db.query(EmailVerificationCode).filter(
        EmailVerificationCode.email == normalized,
        EmailVerificationCode.purpose == purpose,
    ).delete()

    record = EmailVerificationCode(
        email=normalized,
        purpose=purpose,
        code=code,
        expires_at=expires_at,
        created_at=now_ms,
    )
    db.add(record)
    db.commit()
    return settings.verification_code_expire_minutes * 60


def verify_code(db: Session, email: str, code: str, purpose: Purpose) -> None:
    normalized = normalize_email(email)
    record = _latest_code(db, normalized, purpose)
    if not record:
        raise BusinessException(401, "验证码无效或已过期")

    now_ms = beijing_now_ms()
    if now_ms > record.expires_at:
        raise BusinessException(401, "验证码已过期，请重新获取")

    if not secrets.compare_digest(record.code, code):
        raise BusinessException(401, "验证码错误")

    db.delete(record)
    db.commit()
