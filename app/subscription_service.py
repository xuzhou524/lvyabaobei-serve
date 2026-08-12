"""家庭级 Pro 订阅判定与开通。"""

from sqlalchemy.orm import Session

from app.family_utils import ensure_user_family
from app.models import Child, Family, FamilyMember, Subscription, User
from app.subscription_config import IAP_PRODUCT_DURATIONS, TIER_FEATURES
from app.time_utils import beijing_now_ms


def effective_tier(user: User) -> str:
    tier = user.subscription_tier or "free"
    if tier != "pro":
        return "free"
    if user.pro_expires_at is not None and user.pro_expires_at < beijing_now_ms():
        return "free"
    return "pro"


def get_family_owner(db: Session, family: Family) -> User:
    return db.query(User).filter(User.id == family.owner_user_id).one()


def get_family_tier(db: Session, family: Family) -> str:
    owner = get_family_owner(db, family)
    return effective_tier(owner)


def get_features_for_tier(tier: str) -> dict:
    return dict(TIER_FEATURES.get(tier, TIER_FEATURES["free"]))


def get_family_features(db: Session, family: Family) -> dict:
    return get_features_for_tier(get_family_tier(db, family))


def is_family_pro(db: Session, family: Family) -> bool:
    return get_family_tier(db, family) == "pro"


def apply_product_to_user(
    db: Session,
    user: User,
    product_id: str,
    original_transaction_id: str | None = None,
) -> None:
    duration = IAP_PRODUCT_DURATIONS.get(product_id)
    now = beijing_now_ms()
    user.subscription_tier = "pro"
    if duration is None:
        user.pro_expires_at = None
    else:
        base = user.pro_expires_at if user.pro_expires_at and user.pro_expires_at > now else now
        user.pro_expires_at = base + duration * 24 * 60 * 60 * 1000

    sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    if not sub:
        sub = Subscription(user_id=user.id, created_at=now, updated_at=now)
        db.add(sub)
    sub.tier = "pro"
    sub.product_id = product_id
    sub.original_transaction_id = original_transaction_id
    sub.expires_at = user.pro_expires_at
    sub.is_active = True
    sub.source = "apple"
    sub.updated_at = now
    db.commit()


def count_family_children(db: Session, family: Family) -> int:
    return db.query(Child).filter(Child.family_id == family.id).count()


def count_family_parents(db: Session, family: Family) -> int:
    return db.query(FamilyMember).filter(FamilyMember.family_id == family.id).count()


def ensure_user_is_family_owner(db: Session, user: User) -> Family:
    family = ensure_user_family(db, user)
    if family.owner_user_id != user.id:
        from app.exceptions import BusinessException

        raise BusinessException(403, "仅家庭创建者可购买或管理 Pro 订阅", error_code="NOT_FAMILY_OWNER")
    return family


def ledger_cutoff_ms(features: dict) -> int | None:
    days = features.get("ledger_days")
    if days is None:
        return None
    return beijing_now_ms() - int(days) * 24 * 60 * 60 * 1000
