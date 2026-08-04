"""宝贝生命周期：删除时级联清理，再添加同名宝贝视为全新记录（新 id）。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Child,
    GrowthLedger,
    OperationLog,
    PointLedger,
    Reward,
    RewardRedemption,
    Task,
    TaskCompletion,
    User,
)
from app.time_utils import beijing_now_ms


def delete_child_and_all_data(db: Session, child: Child, actor: User) -> None:
    """
    物理删除宝贝及其全部业务数据（任务、流水、奖励等）。
    不保留 child 行，因此再次 POST /children 同名宝贝一定是新 id、新手任务与初始积分。
    家庭级 operation_logs 保留一条审计摘要（不含可恢复的业务数据）。
    """
    child_id = child.id
    nickname = child.nickname
    family_id = child.family_id

    task_ids = list(db.scalars(select(Task.id).where(Task.child_id == child_id)))
    if task_ids:
        db.query(TaskCompletion).filter(TaskCompletion.task_id.in_(task_ids)).delete(
            synchronize_session=False
        )
    db.query(TaskCompletion).filter(TaskCompletion.child_id == child_id).delete(
        synchronize_session=False
    )
    db.query(Task).filter(Task.child_id == child_id).delete(synchronize_session=False)

    reward_ids = list(db.scalars(select(Reward.id).where(Reward.child_id == child_id)))
    if reward_ids:
        db.query(RewardRedemption).filter(
            RewardRedemption.reward_id.in_(reward_ids)
        ).delete(synchronize_session=False)
    db.query(RewardRedemption).filter(RewardRedemption.child_id == child_id).delete(
        synchronize_session=False
    )
    db.query(Reward).filter(Reward.child_id == child_id).delete(synchronize_session=False)

    db.query(PointLedger).filter(PointLedger.child_id == child_id).delete(
        synchronize_session=False
    )
    db.query(GrowthLedger).filter(GrowthLedger.child_id == child_id).delete(
        synchronize_session=False
    )

    db.add(
        OperationLog(
            family_id=family_id,
            user_id=actor.id,
            action="child.delete",
            detail=f"已删除宝贝「{nickname}」(id={child_id})，相关任务/积分/成长/奖励数据已一并清除",
            created_at=beijing_now_ms(),
        )
    )

    db.delete(child)
    db.commit()
