from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import (
    create_access_token,
    get_user_by_email,
    get_user_by_phone,
    normalize_email,
)
from app.family_utils import ensure_user_family
from app.config import settings
from app.database import get_db
from app.email_service import generate_verification_code, send_verification_email
from app.exceptions import BusinessException
from app.models import User
from app.password_utils import hash_password, verify_password
from app.phone_utils import validate_phone
from app.register_utils import assert_email_available_for_register, assert_phone_available
from app.response import ApiResponse, success
from app.schemas import LoginRequest, RegisterRequest, SendCodeData, SendCodeRequest, TokenData
from app.time_utils import beijing_now_ms
from app.verification import assert_can_send_code, save_verification_code, verify_code

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/send-code", response_model=ApiResponse[SendCodeData])
def send_code(body: SendCodeRequest, db: Session = Depends(get_db)):
    email = normalize_email(str(body.email))
    purpose = body.purpose

    if purpose == "register":
        assert_phone_available(db, body.phone or "")
        assert_email_available_for_register(db, email)
    elif purpose == "login":
        if not get_user_by_email(db, email):
            raise BusinessException(404, "该邮箱尚未注册")

    assert_can_send_code(db, email, purpose)

    code = generate_verification_code()
    expires_in = save_verification_code(db, email, code, purpose)
    send_verification_email(email, code, purpose=purpose)

    debug_code = code if settings.expose_code_in_response or not settings.smtp_host else None
    return success(
        SendCodeData(email=email, expires_in_seconds=expires_in, debug_code=debug_code),
        message="验证码已发送",
    )


@router.post("/register", response_model=ApiResponse[TokenData])
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    phone = assert_phone_available(db, body.phone)
    email = assert_email_available_for_register(db, str(body.email))

    verify_code(db, email, body.code, "register")

    user = User(
        phone=phone,
        email=email,
        password_hash=hash_password(body.password),
        created_at=beijing_now_ms(),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise BusinessException(409, "该手机号或邮箱已注册") from exc
    db.refresh(user)
    ensure_user_family(db, user)

    token = create_access_token(user.id)
    return success(TokenData(access_token=token), message="注册成功")


@router.post("/login", response_model=ApiResponse[TokenData])
def login(body: LoginRequest, db: Session = Depends(get_db)):
    if body.login_type == "phone_password":
        phone = validate_phone(body.phone or "")
        user = get_user_by_phone(db, phone)
        if not user or not verify_password(body.password or "", user.password_hash):
            raise BusinessException(401, "手机号或密码错误")
    else:
        email = normalize_email(str(body.email))
        verify_code(db, email, body.code or "", "login")
        user = get_user_by_email(db, email)
        if not user:
            raise BusinessException(404, "该邮箱尚未注册")

    ensure_user_family(db, user)
    token = create_access_token(user.id)
    return success(TokenData(access_token=token))
