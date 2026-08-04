from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.child_access import get_child_for_user, get_user_family, list_children
from app.database import get_db
from app.deps import get_current_user
from app.domain_schemas import (
    ChildCreateRequest,
    ChildSummary,
    ChildUpdateRequest,
    HomeDashboard,
)
from app.models import Child, OperationLog, User
from app.response import ApiResponse, success
from app.serializers import build_plant_info, list_visible_tasks
from app.services.rewards_engine import check_onboarding_complete
from app.family_utils import seed_onboarding_tasks
from app.services.child_lifecycle import delete_child_and_all_data
from app.time_utils import beijing_now_ms

router = APIRouter(prefix="/children", tags=["children"])


def _child_summary(child: Child) -> ChildSummary:
    return ChildSummary.model_validate(child)


@router.get("", response_model=ApiResponse[list[ChildSummary]])
def get_children(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    children = list_children(db, current_user)
    return success([_child_summary(c) for c in children])


@router.post("", response_model=ApiResponse[ChildSummary])
def create_child(
    body: ChildCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    family = get_user_family(db, current_user)
    now = beijing_now_ms()
    child = Child(
        family_id=family.id,
        nickname=body.nickname.strip(),
        gender=body.gender,
        avatar_emoji=body.avatar_emoji,
        created_at=now,
    )
    db.add(child)
    db.commit()
    db.refresh(child)
    seed_onboarding_tasks(db, child)
    db.add(
        OperationLog(
            family_id=family.id,
            user_id=current_user.id,
            action="child.create",
            detail=f"添加宝贝 {child.nickname}",
            created_at=now,
        )
    )
    db.commit()
    return success(_child_summary(child))


@router.put("", response_model=ApiResponse[ChildSummary])
def update_child(
    body: ChildUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    child = get_child_for_user(db, current_user, body.child_id)
    if body.nickname is not None:
        child.nickname = body.nickname.strip()
    if body.gender is not None:
        child.gender = body.gender
    if body.avatar_emoji is not None:
        child.avatar_emoji = body.avatar_emoji
    db.commit()
    db.refresh(child)
    return success(_child_summary(child))


@router.delete("", response_model=ApiResponse[dict])
def delete_child(
    child_id: int = Query(..., description="宝贝 ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    child = get_child_for_user(db, current_user, child_id)
    delete_child_and_all_data(db, child, current_user)
    return success({"deleted": True})


@router.get("/home", response_model=ApiResponse[HomeDashboard])
def home_dashboard(
    child_id: int = Query(..., description="宝贝 ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    child = get_child_for_user(db, current_user, child_id)
    tasks = list_visible_tasks(db, child)[:20]
    onboarding_flag = check_onboarding_complete(db, child)
    if onboarding_flag:
        db.commit()
        db.refresh(child)
    return success(
        HomeDashboard(
            child=_child_summary(child),
            plant=build_plant_info(child),
            today_tasks=tasks,
            consecutive_checkin_days=child.consecutive_checkin_days,
            total_checkin_days=child.total_checkin_days,
            badge_count=child.badge_count,
            today_points_delta=child.today_points_delta,
            onboarding_just_completed=onboarding_flag,
        )
    )
