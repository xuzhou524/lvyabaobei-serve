import secrets
import string

import bcrypt
from sqlalchemy.orm import Session

from app.exceptions import BusinessException
from app.models import Child, Family, FamilyMember, Task, User
from app.onboarding import SYSTEM_ONBOARDING_TASKS
from app.time_utils import beijing_now_ms


def hash_parent_pin(pin: str) -> str:
    return bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()


def verify_parent_pin(pin: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    return bcrypt.checkpw(pin.encode(), hashed.encode())


def generate_invite_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(6))


def mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if not domain:
        return email
    if len(local) <= 1:
        masked_local = "*"
    else:
        masked_local = local[0] + "***"
    return f"{masked_local}@{domain}"


def join_family_by_invite(db: Session, user: User, invite_code: str) -> Family:
    normalized = "".join(invite_code.split()).upper()
    target = db.query(Family).filter(Family.invite_code == normalized).first()
    if not target:
        raise BusinessException(404, "邀请码无效，请核对后重试")

    membership = db.query(FamilyMember).filter(FamilyMember.user_id == user.id).first()
    if not membership:
        ensure_user_family(db, user)
        membership = db.query(FamilyMember).filter(FamilyMember.user_id == user.id).one()

    if membership.family_id == target.id:
        return target

    current_family = db.query(Family).filter(Family.id == membership.family_id).one()
    child_count = db.query(Child).filter(Child.family_id == current_family.id).count()
    if child_count > 0:
        raise BusinessException(
            409,
            "当前账号所在家庭已有宝贝，无法加入其他家庭。请用新邮箱注册后再输入邀请码。",
        )

    old_family_id = current_family.id
    db.delete(membership)
    db.flush()

    members_left = (
        db.query(FamilyMember).filter(FamilyMember.family_id == old_family_id).count()
    )
    if members_left == 0:
        orphan = db.query(Family).filter(Family.id == old_family_id).one()
        db.delete(orphan)

    db.add(
        FamilyMember(
            family_id=target.id,
            user_id=user.id,
            role="parent",
            joined_at=beijing_now_ms(),
        )
    )
    db.commit()
    db.refresh(target)
    return target


def ensure_user_family(db: Session, user: User) -> Family:
    membership = (
        db.query(FamilyMember).filter(FamilyMember.user_id == user.id).first()
    )
    if membership:
        return db.query(Family).filter(Family.id == membership.family_id).one()

    for _ in range(10):
        code = generate_invite_code()
        if not db.query(Family).filter(Family.invite_code == code).first():
            break
    else:
        code = generate_invite_code() + "X"

    family = Family(
        name="我的家庭",
        invite_code=code,
        owner_user_id=user.id,
        created_at=beijing_now_ms(),
    )
    db.add(family)
    db.flush()
    db.add(
        FamilyMember(
            family_id=family.id,
            user_id=user.id,
            role="owner",
            joined_at=beijing_now_ms(),
        )
    )
    db.commit()
    db.refresh(family)
    return family


def seed_onboarding_tasks(db: Session, child: Child) -> None:
    now = beijing_now_ms()
    for index, item in enumerate(SYSTEM_ONBOARDING_TASKS):
        db.add(
            Task(
                child_id=child.id,
                title=item["title"],
                category=item["category"],
                point_reward=item["point_reward"],
                growth_reward=item["growth_reward"],
                frequency="once",
                is_system_task=True,
                system_key=item["system_key"],
                is_hidden=False,
                sort_order=index,
                created_at=now,
            )
        )
    db.commit()
