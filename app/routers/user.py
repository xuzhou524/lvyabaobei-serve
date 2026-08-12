from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.domain_schemas import SetParentPinRequest, UserInfo, VerifyParentPinRequest
from app.exceptions import BusinessException
from app.family_utils import hash_parent_pin, verify_parent_pin
from app.models import User
from app.response import ApiResponse, success
from app.user_info import build_user_info

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/info", response_model=ApiResponse[UserInfo])
def get_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return success(build_user_info(db, current_user))


@router.put("/parent-pin", response_model=ApiResponse[dict])
def set_parent_pin(
    body: SetParentPinRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.parent_pin_hash = hash_parent_pin(body.pin)
    db.commit()
    return success({"ok": True})


@router.post("/verify-parent-pin", response_model=ApiResponse[dict])
def verify_parent_pin_api(
    body: VerifyParentPinRequest,
    current_user: User = Depends(get_current_user),
):
    if not verify_parent_pin(body.pin, current_user.parent_pin_hash):
        raise BusinessException(401, "家长密码错误")
    return success({"ok": True})
