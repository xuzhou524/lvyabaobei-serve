from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.exceptions import BusinessException
from app.family_utils import ensure_user_family
from app.models import Child, Family, FamilyMember, User

BEIJING_TZ = timezone(timedelta(hours=8))


def today_beijing_str() -> str:
    return datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")


def get_user_family(db: Session, user: User) -> Family:
    return ensure_user_family(db, user)


def get_child_for_user(db: Session, user: User, child_id: int) -> Child:
    family = get_user_family(db, user)
    child = (
        db.query(Child)
        .filter(Child.id == child_id, Child.family_id == family.id)
        .first()
    )
    if not child:
        raise BusinessException(404, "宝贝不存在")
    return child


def list_children(db: Session, user: User) -> list[Child]:
    family = get_user_family(db, user)
    return (
        db.query(Child)
        .filter(Child.family_id == family.id)
        .order_by(Child.sort_order.asc(), Child.id.asc())
        .all()
    )
