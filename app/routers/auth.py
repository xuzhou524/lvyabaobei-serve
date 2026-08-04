from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_user_by_email, normalize_email
from app.family_utils import ensure_user_family
from app.config import settings
from app.database import get_db
from app.email_service import generate_verification_code, send_verification_email
from app.models import User
from app.response import ApiResponse, success
from app.schemas import LoginRequest, SendCodeData, SendCodeRequest, TokenData
from app.time_utils import beijing_now_ms
from app.verification import assert_can_send_code, save_verification_code, verify_code

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/send-code", response_model=ApiResponse[SendCodeData])
def send_code(body: SendCodeRequest, db: Session = Depends(get_db)):
    email = normalize_email(str(body.email))
    assert_can_send_code(db, email)

    code = generate_verification_code()
    expires_in = save_verification_code(db, email, code)
    send_verification_email(email, code)

    debug_code = code if settings.expose_code_in_response or not settings.smtp_host else None
    return success(
        SendCodeData(email=email, expires_in_seconds=expires_in, debug_code=debug_code),
        message="验证码已发送",
    )


@router.post("/login", response_model=ApiResponse[TokenData])
def login(body: LoginRequest, db: Session = Depends(get_db)):
    email = normalize_email(str(body.email))
    verify_code(db, email, body.code)

    user = get_user_by_email(db, email)
    if not user:
        user = User(email=email, created_at=beijing_now_ms())
        db.add(user)
    db.commit()
    db.refresh(user)
    ensure_user_family(db, user)

    token = create_access_token(user.id)
    return success(TokenData(access_token=token))
