from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.child_access import get_user_family
from app.database import get_db
from app.deps import get_current_user
from app.domain_schemas import FamilyInfo, FamilyMemberItem, JoinFamilyRequest, PendingItem
from app.family_utils import join_family_by_invite, mask_email
from app.models import Child, FamilyMember, Reward, RewardRedemption, Task, TaskCompletion, User
from app.response import ApiResponse, success

router = APIRouter(tags=["family"])


@router.get("/family", response_model=ApiResponse[FamilyInfo])
def get_family(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    family = get_user_family(db, current_user)
    return success(FamilyInfo(id=family.id, name=family.name, invite_code=family.invite_code))


@router.get("/family/members", response_model=ApiResponse[list[FamilyMemberItem]])
def list_family_members(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    family = get_user_family(db, current_user)
    rows = (
        db.query(FamilyMember, User)
        .join(User, User.id == FamilyMember.user_id)
        .filter(FamilyMember.family_id == family.id)
        .order_by(FamilyMember.joined_at.asc())
        .all()
    )
    return success(
        [
            FamilyMemberItem(
                email=mask_email(user.email),
                role=member.role,
                is_self=user.id == current_user.id,
            )
            for member, user in rows
        ]
    )


@router.post("/family/join", response_model=ApiResponse[FamilyInfo])
def join_family(
    body: JoinFamilyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current = get_user_family(db, current_user)
    if current.invite_code == body.invite_code:
        info = FamilyInfo(id=current.id, name=current.name, invite_code=current.invite_code)
        return success(info, message="您已在该家庭中")
    family = join_family_by_invite(db, current_user, body.invite_code)
    info = FamilyInfo(id=family.id, name=family.name, invite_code=family.invite_code)
    return success(info, message="已成功加入家庭")


@router.get("/pending", response_model=ApiResponse[list[PendingItem]])
def list_pending(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    family = get_user_family(db, current_user)
    child_ids = [c.id for c in family.children]
    if not child_ids:
        return success([])

    items: list[PendingItem] = []
    task_rows = (
        db.query(TaskCompletion, Task, Child)
        .join(Task, Task.id == TaskCompletion.task_id)
        .join(Child, Child.id == TaskCompletion.child_id)
        .filter(
            TaskCompletion.child_id.in_(child_ids),
            TaskCompletion.status == "pending",
        )
        .order_by(TaskCompletion.submitted_at.desc())
        .all()
    )
    for completion, task, child in task_rows:
        items.append(
            PendingItem(
                kind="task",
                id=task.id,
                title=task.title,
                child_nickname=child.nickname,
                submitted_at=completion.submitted_at,
            )
        )

    reward_rows = (
        db.query(RewardRedemption, Reward, Child)
        .join(Reward, Reward.id == RewardRedemption.reward_id)
        .join(Child, Child.id == RewardRedemption.child_id)
        .filter(
            RewardRedemption.child_id.in_(child_ids),
            RewardRedemption.status == "pending",
        )
        .order_by(RewardRedemption.submitted_at.desc())
        .all()
    )
    for redemption, reward, child in reward_rows:
        items.append(
            PendingItem(
                kind="reward",
                id=redemption.id,
                title=reward.title,
                child_nickname=child.nickname,
                submitted_at=redemption.submitted_at,
            )
        )
    return success(items)
