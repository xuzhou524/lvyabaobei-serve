from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.child_access import get_child_for_user, today_beijing_str
from app.database import get_db
from app.deps import get_current_user
from app.domain_schemas import (
    TaskCreateRequest,
    TaskIdRequest,
    TaskItem,
    TaskReorderRequest,
    TaskUpdateRequest,
)
from app.exceptions import BusinessException
from app.models import Task, TaskCompletion, User
from app.response import ApiResponse, success
from app.serializers import list_visible_tasks
from app.services.rewards_engine import apply_task_rewards, check_onboarding_complete
from app.time_utils import beijing_now_ms

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=ApiResponse[list[TaskItem]])
def list_tasks(
    child_id: int = Query(..., description="宝贝 ID"),
    category: str = Query(default="all"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    child = get_child_for_user(db, current_user, child_id)
    return success(list_visible_tasks(db, child, category))


@router.post("", response_model=ApiResponse[TaskItem])
def create_task(
    body: TaskCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    child = get_child_for_user(db, current_user, body.child_id)
    now = beijing_now_ms()
    max_order = (
        db.query(Task.sort_order).filter(Task.child_id == child.id).order_by(Task.sort_order.desc()).first()
    )
    task = Task(
        child_id=child.id,
        title=body.title.strip(),
        category=body.category,
        point_reward=body.point_reward,
        growth_reward=body.growth_reward,
        frequency=body.frequency,
        sort_order=(max_order[0] if max_order else 100) + 1,
        created_at=now,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    items = list_visible_tasks(db, child)
    item = next(i for i in items if i.id == task.id)
    return success(item)


@router.put("", response_model=ApiResponse[TaskItem])
def update_task(
    body: TaskUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == body.task_id).first()
    if not task:
        raise BusinessException(404, "任务不存在")
    child = get_child_for_user(db, current_user, task.child_id)
    if task.is_system_task:
        raise BusinessException(403, "系统新手任务不可编辑")
    if body.title is not None:
        task.title = body.title.strip()
    if body.category is not None:
        task.category = body.category
    if body.point_reward is not None:
        task.point_reward = body.point_reward
    if body.growth_reward is not None:
        task.growth_reward = body.growth_reward
    if body.frequency is not None:
        task.frequency = body.frequency
    db.commit()
    items = list_visible_tasks(db, child)
    item = next((i for i in items if i.id == task.id), None)
    if not item:
        raise BusinessException(404, "任务不可见")
    return success(item)


@router.delete("", response_model=ApiResponse[dict])
def delete_task(
    task_id: int = Query(..., description="任务 ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise BusinessException(404, "任务不存在")
    get_child_for_user(db, current_user, task.child_id)
    if task.is_system_task:
        raise BusinessException(403, "系统新手任务不可删除")
    db.delete(task)
    db.commit()
    return success({"deleted": True})


@router.post("/reorder", response_model=ApiResponse[dict])
def reorder_tasks(
    body: TaskReorderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    child = get_child_for_user(db, current_user, body.child_id)
    tasks = db.query(Task).filter(Task.child_id == child.id).all()
    task_map = {t.id: t for t in tasks}
    order = 10
    for tid in body.task_ids:
        task = task_map.get(tid)
        if task and not task.is_system_task:
            task.sort_order = order
            order += 1
    db.commit()
    return success({"ok": True})


def _task_by_id(db: Session, task_id: int) -> Task:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise BusinessException(404, "任务不存在")
    return task


@router.post("/submit", response_model=ApiResponse[TaskItem])
def submit_task(
    body: TaskIdRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = _task_by_id(db, body.task_id)
    child = get_child_for_user(db, current_user, task.child_id)
    today = today_beijing_str()
    existing = (
        db.query(TaskCompletion)
        .filter(
            TaskCompletion.task_id == task.id,
            TaskCompletion.child_id == child.id,
            TaskCompletion.task_date == today,
        )
        .order_by(TaskCompletion.id.desc())
        .first()
    )
    if existing and existing.status in ("pending", "approved"):
        raise BusinessException(409, "今日已提交或已完成该任务")
    completion = TaskCompletion(
        task_id=task.id,
        child_id=child.id,
        status="pending",
        task_date=today,
        submitted_at=beijing_now_ms(),
    )
    db.add(completion)
    db.commit()
    items = list_visible_tasks(db, child)
    item = next(i for i in items if i.id == task.id)
    return success(item)


@router.post("/approve", response_model=ApiResponse[TaskItem])
def approve_task(
    body: TaskIdRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = _task_by_id(db, body.task_id)
    child = get_child_for_user(db, current_user, task.child_id)
    completion = (
        db.query(TaskCompletion)
        .filter(TaskCompletion.task_id == task.id, TaskCompletion.status == "pending")
        .order_by(TaskCompletion.id.desc())
        .first()
    )
    if not completion:
        raise BusinessException(404, "没有待确认的申请")
    apply_task_rewards(db, child, task, completion)
    child.today_points_delta += task.point_reward
    check_onboarding_complete(db, child)
    db.commit()
    items = list_visible_tasks(db, child)
    item = next((i for i in items if i.id == task.id), TaskItem(
        id=task.id,
        title=task.title,
        category=task.category,
        point_reward=task.point_reward,
        growth_reward=task.growth_reward,
        frequency=task.frequency,
        is_system_task=task.is_system_task,
        sort_order=task.sort_order,
        status="approved",
        completion_id=completion.id,
    ))
    return success(item)


@router.post("/reject", response_model=ApiResponse[TaskItem])
def reject_task(
    body: TaskIdRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = _task_by_id(db, body.task_id)
    child = get_child_for_user(db, current_user, task.child_id)
    completion = (
        db.query(TaskCompletion)
        .filter(TaskCompletion.task_id == task.id, TaskCompletion.status == "pending")
        .order_by(TaskCompletion.id.desc())
        .first()
    )
    if not completion:
        raise BusinessException(404, "没有待确认的申请")
    completion.status = "rejected"
    completion.reviewed_at = beijing_now_ms()
    db.commit()
    items = list_visible_tasks(db, child)
    item = next(i for i in items if i.id == task.id)
    return success(item)
