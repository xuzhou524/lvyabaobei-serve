from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.child_access import get_child_for_user
from app.database import get_db
from app.deps import get_current_user
from app.domain_schemas import (
    RedemptionIdRequest,
    RewardCreateRequest,
    RewardIdRequest,
    RewardItem,
    RewardUpdateRequest,
)
from app.exceptions import BusinessException
from app.models import Reward, RewardRedemption, User
from app.response import ApiResponse, success
from app.serializers import reward_pending_map
from app.services.rewards_engine import _add_point_ledger
from app.time_utils import beijing_now_ms

router = APIRouter(tags=["rewards"])


def _reward_item(reward: Reward, pending_map: dict[int, int]) -> RewardItem:
    return RewardItem(
        id=reward.id,
        title=reward.title,
        cost_points=reward.cost_points,
        emoji=reward.emoji,
        is_active=reward.is_active,
        pending_redemption_id=pending_map.get(reward.id),
    )


@router.get("/rewards", response_model=ApiResponse[list[RewardItem]])
def list_rewards(
    child_id: int = Query(..., description="宝贝 ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    child = get_child_for_user(db, current_user, child_id)
    pending = reward_pending_map(db, child.id)
    rewards = (
        db.query(Reward)
        .filter(Reward.child_id == child.id, Reward.is_active.is_(True))
        .order_by(Reward.sort_order.asc(), Reward.id.asc())
        .all()
    )
    return success([_reward_item(r, pending) for r in rewards])


@router.post("/rewards", response_model=ApiResponse[RewardItem])
def create_reward(
    body: RewardCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    child = get_child_for_user(db, current_user, body.child_id)
    reward = Reward(
        child_id=child.id,
        title=body.title.strip(),
        cost_points=body.cost_points,
        emoji=body.emoji,
        created_at=beijing_now_ms(),
    )
    db.add(reward)
    db.commit()
    db.refresh(reward)
    return success(_reward_item(reward, {}))


@router.put("/rewards", response_model=ApiResponse[RewardItem])
def update_reward(
    body: RewardUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reward = db.query(Reward).filter(Reward.id == body.reward_id).first()
    if not reward:
        raise BusinessException(404, "奖励不存在")
    child = get_child_for_user(db, current_user, reward.child_id)
    if body.title is not None:
        reward.title = body.title.strip()
    if body.cost_points is not None:
        reward.cost_points = body.cost_points
    if body.emoji is not None:
        reward.emoji = body.emoji
    if body.is_active is not None:
        reward.is_active = body.is_active
    db.commit()
    pending = reward_pending_map(db, child.id)
    return success(_reward_item(reward, pending))


@router.delete("/rewards", response_model=ApiResponse[dict])
def delete_reward(
    reward_id: int = Query(..., description="奖励 ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reward = db.query(Reward).filter(Reward.id == reward_id).first()
    if not reward:
        raise BusinessException(404, "奖励不存在")
    get_child_for_user(db, current_user, reward.child_id)
    reward.is_active = False
    db.commit()
    return success({"deleted": True})


@router.post("/rewards/redeem", response_model=ApiResponse[RewardItem])
def redeem_reward(
    body: RewardIdRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reward = db.query(Reward).filter(Reward.id == body.reward_id).first()
    if not reward or not reward.is_active:
        raise BusinessException(404, "奖励不存在")
    child = get_child_for_user(db, current_user, reward.child_id)
    pending = (
        db.query(RewardRedemption)
        .filter(
            RewardRedemption.reward_id == reward.id,
            RewardRedemption.status == "pending",
        )
        .first()
    )
    if pending:
        raise BusinessException(409, "已有待审批的兑换申请")
    db.add(
        RewardRedemption(
            reward_id=reward.id,
            child_id=child.id,
            status="pending",
            submitted_at=beijing_now_ms(),
        )
    )
    db.commit()
    pending_map = reward_pending_map(db, child.id)
    return success(_reward_item(reward, pending_map))


@router.post("/redemptions/approve", response_model=ApiResponse[dict])
def approve_redemption(
    body: RedemptionIdRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    redemption = db.query(RewardRedemption).filter(RewardRedemption.id == body.redemption_id).first()
    if not redemption:
        raise BusinessException(404, "兑换申请不存在")
    child = get_child_for_user(db, current_user, redemption.child_id)
    reward = db.query(Reward).filter(Reward.id == redemption.reward_id).one()
    if redemption.status != "pending":
        raise BusinessException(409, "申请已处理")
    if child.points < reward.cost_points:
        raise BusinessException(409, "积分不足，无法通过")
    _add_point_ledger(
        db,
        child,
        -reward.cost_points,
        "reward",
        reward.id,
        f"兑换奖励「{reward.title}」",
    )
    redemption.status = "approved"
    redemption.reviewed_at = beijing_now_ms()
    db.commit()
    return success({"approved": True})


@router.post("/redemptions/reject", response_model=ApiResponse[dict])
def reject_redemption(
    body: RedemptionIdRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    redemption = db.query(RewardRedemption).filter(RewardRedemption.id == body.redemption_id).first()
    if not redemption:
        raise BusinessException(404, "兑换申请不存在")
    get_child_for_user(db, current_user, redemption.child_id)
    redemption.status = "rejected"
    redemption.reviewed_at = beijing_now_ms()
    db.commit()
    return success({"rejected": True})
