from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.domain_schemas import IapVerifyRequest, SubscriptionInfo
from app.exceptions import BusinessException
from app.family_utils import ensure_user_family
from app.models import Subscription, User
from app.response import ApiResponse, success
from app.subscription_config import IAP_PRODUCT_DURATIONS
from app.subscription_service import (
    apply_product_to_user,
    ensure_user_is_family_owner,
    get_family_features,
    get_family_tier,
)
from app.user_info import _pro_features_from_dict

router = APIRouter(tags=["subscription"])


def _subscription_info(db: Session, user: User) -> SubscriptionInfo:
    family = ensure_user_family(db, user)
    tier = get_family_tier(db, family)
    features = get_family_features(db, family)
    owner = db.query(User).filter(User.id == family.owner_user_id).one()
    sub = db.query(Subscription).filter(Subscription.user_id == owner.id).first()
    return SubscriptionInfo(
        subscription_tier=tier,
        pro_expires_at=owner.pro_expires_at if tier == "pro" else None,
        is_family_owner=family.owner_user_id == user.id,
        product_id=sub.product_id if sub else None,
        pro_features=_pro_features_from_dict(features),
    )


@router.get("/user/subscription", response_model=ApiResponse[SubscriptionInfo])
def get_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return success(_subscription_info(db, current_user))


@router.post("/iap/verify", response_model=ApiResponse[SubscriptionInfo])
def verify_iap(
    body: IapVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.product_id not in IAP_PRODUCT_DURATIONS:
        raise BusinessException(422, "无效的产品 ID", error_code="INVALID_PRODUCT")

    ensure_user_is_family_owner(db, current_user)
    apply_product_to_user(
        db,
        current_user,
        body.product_id,
        original_transaction_id=body.transaction_id,
    )
    db.refresh(current_user)
    return success(_subscription_info(db, current_user))
