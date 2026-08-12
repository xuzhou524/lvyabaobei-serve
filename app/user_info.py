from sqlalchemy.orm import Session

from app.domain_schemas import ProFeatures, UserInfo
from app.family_utils import ensure_user_family
from app.models import User
from app.subscription_service import (
    get_family_features,
    get_family_tier,
)


def _pro_features_from_dict(features: dict) -> ProFeatures:
    return ProFeatures(
        max_children=features["max_children"],
        max_parents=features["max_parents"],
        puzzle_daily_cap=features["puzzle_daily_cap"],
        ledger_days=features.get("ledger_days"),
        growth_report_full=features["growth_report_full"],
        plant_reset=features["plant_reset"],
        multi_parent=features["multi_parent"],
    )


def build_user_info(db: Session, user: User) -> UserInfo:
    family = ensure_user_family(db, user)
    tier = get_family_tier(db, family)
    features = get_family_features(db, family)
    owner = db.query(User).filter(User.id == family.owner_user_id).one()
    return UserInfo(
        email=user.email,
        has_parent_pin=bool(user.parent_pin_hash),
        family_id=family.id,
        invite_code=family.invite_code,
        subscription_tier=tier,
        pro_expires_at=owner.pro_expires_at if tier == "pro" else None,
        is_family_owner=family.owner_user_id == user.id,
        pro_features=_pro_features_from_dict(features),
    )
