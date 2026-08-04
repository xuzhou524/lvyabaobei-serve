from sqlalchemy.orm import Session

from app.child_access import today_beijing_str
from app.domain_schemas import PlantInfo, PlantStagePreview, TaskItem
from app.models import Child, RewardRedemption, Task, TaskCompletion
from app.plant_stages import STAGES, progress_to_next, stage_for_growth


def build_plant_info(child: Child) -> PlantInfo:
    stage = stage_for_growth(child.total_growth_value)
    stage_row = next(r for r in STAGES if r[0] == stage)
    done, span, hint = progress_to_next(child.total_growth_value)
    if not child.plant_planted:
        hint = "完成 3 个新手任务，就能种下希望种子啦！"
    previews = [
        PlantStagePreview(stage=s, emoji=e, name=n, threshold=t) for s, e, n, t in STAGES
    ]
    return PlantInfo(
        plant_name=child.plant_name,
        plant_type=child.plant_type,
        plant_planted=child.plant_planted,
        stage=stage,
        stage_emoji=stage_row[1],
        stage_name=stage_row[2] if child.plant_planted else "沉睡中",
        total_growth_value=child.total_growth_value,
        progress_current=done,
        progress_total=max(span, 1),
        progress_hint=hint,
        stages=previews,
    )


def task_status_for_today(db: Session, task: Task, child_id: int) -> tuple[str, int | None]:
    today = today_beijing_str()
    completion = (
        db.query(TaskCompletion)
        .filter(
            TaskCompletion.task_id == task.id,
            TaskCompletion.child_id == child_id,
            TaskCompletion.task_date == today,
        )
        .order_by(TaskCompletion.id.desc())
        .first()
    )
    if task.frequency == "once" and not task.is_system_task:
        completion = (
            db.query(TaskCompletion)
            .filter(TaskCompletion.task_id == task.id, TaskCompletion.child_id == child_id)
            .order_by(TaskCompletion.id.desc())
            .first()
        )
    if not completion:
        return "open", None
    return completion.status, completion.id


def list_visible_tasks(db: Session, child: Child, category: str | None = None) -> list[TaskItem]:
    q = (
        db.query(Task)
        .filter(Task.child_id == child.id, Task.is_hidden.is_(False))
        .order_by(Task.is_system_task.desc(), Task.sort_order.asc(), Task.id.asc())
    )
    if category and category != "all":
        q = q.filter(Task.category == category)
    tasks = q.all()
    items: list[TaskItem] = []
    for task in tasks:
        status, completion_id = task_status_for_today(db, task, child.id)
        if task.frequency == "once" and status == "approved" and not task.is_system_task:
            continue
        items.append(
            TaskItem(
                id=task.id,
                title=task.title,
                category=task.category,
                point_reward=task.point_reward,
                growth_reward=task.growth_reward,
                frequency=task.frequency,
                is_system_task=task.is_system_task,
                sort_order=task.sort_order,
                status=status,
                completion_id=completion_id,
            )
        )
    return items


def reward_pending_map(db: Session, child_id: int) -> dict[int, int]:
    rows = (
        db.query(RewardRedemption)
        .filter(
            RewardRedemption.child_id == child_id,
            RewardRedemption.status == "pending",
        )
        .all()
    )
    return {r.reward_id: r.id for r in rows}
