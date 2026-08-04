from sqlalchemy.orm import Session

from app.models import Child, GrowthLedger, PointLedger, Task, TaskCompletion
from app.plant_stages import stage_for_growth
from app.time_utils import beijing_now_ms


def _add_point_ledger(
    db: Session,
    child: Child,
    amount: int,
    source_type: str,
    source_id: int | None,
    description: str,
) -> None:
    child.points += amount
    db.add(
        PointLedger(
            child_id=child.id,
            amount=amount,
            source_type=source_type,
            source_id=source_id,
            description=description,
            created_at=beijing_now_ms(),
        )
    )


def _add_growth_ledger(
    db: Session,
    child: Child,
    amount: int,
    source_type: str,
    source_id: int | None,
    description: str,
) -> None:
    child.total_growth_value += amount
    child.current_stage = stage_for_growth(child.total_growth_value)
    db.add(
        GrowthLedger(
            child_id=child.id,
            amount=amount,
            source_type=source_type,
            source_id=source_id,
            description=description,
            created_at=beijing_now_ms(),
        )
    )


from app.child_access import today_beijing_str


def _maybe_checkin(db: Session, child: Child) -> None:
    today = today_beijing_str()
    if child.last_checkin_date == today:
        return
    if child.last_checkin_date:
        from datetime import datetime, timedelta, timezone

        BEIJING = timezone(timedelta(hours=8))
        last = datetime.strptime(child.last_checkin_date, "%Y-%m-%d").date()
        cur = datetime.strptime(today, "%Y-%m-%d").date()
        if (cur - last).days == 1:
            child.consecutive_checkin_days += 1
        else:
            child.consecutive_checkin_days = 1
    else:
        child.consecutive_checkin_days = 1
    child.last_checkin_date = today
    child.total_checkin_days += 1


def apply_task_rewards(db: Session, child: Child, task: Task, completion: TaskCompletion) -> None:
    _maybe_checkin(db, child)
    _add_point_ledger(
        db,
        child,
        task.point_reward,
        "task",
        task.id,
        f"完成任务「{task.title}」",
    )
    _add_growth_ledger(
        db,
        child,
        task.growth_reward,
        "task",
        task.id,
        f"完成任务「{task.title}」",
    )
    completion.status = "approved"
    completion.reviewed_at = beijing_now_ms()
    if task.is_system_task and task.system_key:
        task.is_hidden = True


def check_onboarding_complete(db: Session, child: Child) -> bool:
    if child.plant_planted:
        return False
    keys = {t.system_key for t in child.tasks if t.is_system_task and t.is_hidden}
    required = {"garden_intro", "play_puzzle", "set_alarm"}
    if keys >= required:
        child.plant_planted = True
        child.plant_name = child.plant_name or "小绿豆"
        child.current_stage = stage_for_growth(child.total_growth_value)
        return True
    return False
