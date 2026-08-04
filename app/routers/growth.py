from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.child_access import get_child_for_user, today_beijing_str
from app.database import get_db
from app.deps import get_current_user
from app.domain_schemas import (
    ChildIdRequest,
    GameCompleteRequest,
    GameCompleteResult,
    GrowthReportSummary,
    LedgerItem,
    PlantInfo,
    PlantRenameRequest,
)
from app.exceptions import BusinessException
from app.models import GrowthLedger, PointLedger, Task, TaskCompletion, User
from app.plant_stages import stage_for_growth
from app.response import ApiResponse, success
from app.serializers import build_plant_info
from app.services.rewards_engine import _add_growth_ledger, _add_point_ledger
from app.time_utils import beijing_now_ms

router = APIRouter(tags=["growth"])

PUZZLE_DAILY_CAP = 15
GAME_POINT_REWARD = 3
GAME_GROWTH_REWARD = 2


@router.get("/growth/plant", response_model=ApiResponse[PlantInfo])
def get_plant(
    child_id: int = Query(..., description="宝贝 ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    child = get_child_for_user(db, current_user, child_id)
    return success(build_plant_info(child))


@router.put("/growth/plant/name", response_model=ApiResponse[PlantInfo])
def rename_plant(
    body: PlantRenameRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    child = get_child_for_user(db, current_user, body.child_id)
    child.plant_name = body.plant_name.strip()
    db.commit()
    return success(build_plant_info(child))


@router.post("/growth/plant/reset", response_model=ApiResponse[PlantInfo])
def reset_plant(
    body: ChildIdRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    child = get_child_for_user(db, current_user, body.child_id)
    child.total_growth_value = 0
    child.current_stage = 0
    child.plant_planted = True
    child.plant_name = "小绿豆"
    db.commit()
    return success(build_plant_info(child))


@router.get("/growth/ledger", response_model=ApiResponse[list[LedgerItem]])
def growth_ledger(
    child_id: int = Query(..., description="宝贝 ID"),
    limit: int = Query(default=50, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_child_for_user(db, current_user, child_id)
    rows = (
        db.query(GrowthLedger)
        .filter(GrowthLedger.child_id == child_id)
        .order_by(GrowthLedger.id.desc())
        .limit(limit)
        .all()
    )
    return success(
        [
            LedgerItem(
                id=r.id,
                amount=r.amount,
                source_type=r.source_type,
                description=r.description,
                created_at=r.created_at,
            )
            for r in rows
        ]
    )


@router.get("/growth/report", response_model=ApiResponse[GrowthReportSummary])
def growth_report(
    child_id: int = Query(..., description="宝贝 ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    child = get_child_for_user(db, current_user, child_id)
    tasks_total = len(child.tasks)
    tasks_done = sum(1 for t in child.tasks if t.is_hidden)
    return success(
        GrowthReportSummary(
            week_label="本周",
            tasks_completed=tasks_done,
            tasks_total=max(tasks_total, 1),
            points_earned=child.today_points_delta,
            growth_earned=child.total_growth_value,
            puzzle_minutes_estimate=child.puzzle_points_today * 2,
        )
    )


@router.post("/games/complete", response_model=ApiResponse[GameCompleteResult])
def complete_game(
    body: GameCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    child = get_child_for_user(db, current_user, body.child_id)
    if child.puzzle_points_today >= PUZZLE_DAILY_CAP:
        raise BusinessException(429, "今日益智训练积分已达上限")

    points = min(GAME_POINT_REWARD, PUZZLE_DAILY_CAP - child.puzzle_points_today)
    _add_point_ledger(db, child, points, "game", None, f"完成专注训练（{body.game_key}）")
    _add_growth_ledger(db, child, GAME_GROWTH_REWARD, "game", None, "完成专注训练")
    child.puzzle_points_today += points
    child.today_points_delta += points
    child.current_stage = stage_for_growth(child.total_growth_value)

    puzzle_task = (
        db.query(Task)
        .filter(
            Task.child_id == child.id,
            Task.system_key == "play_puzzle",
            Task.is_hidden.is_(False),
        )
        .first()
    )
    if puzzle_task:
        today = today_beijing_str()
        exists = (
            db.query(TaskCompletion)
            .filter(TaskCompletion.task_id == puzzle_task.id, TaskCompletion.task_date == today)
            .first()
        )
        if not exists:
            db.add(
                TaskCompletion(
                    task_id=puzzle_task.id,
                    child_id=child.id,
                    status="pending",
                    task_date=today,
                    submitted_at=beijing_now_ms(),
                )
            )

    db.commit()
    return success(
        GameCompleteResult(
            points_added=points,
            growth_added=GAME_GROWTH_REWARD,
            puzzle_points_today=child.puzzle_points_today,
        )
    )


@router.get("/points/ledger", response_model=ApiResponse[list[LedgerItem]])
def points_ledger(
    child_id: int = Query(..., description="宝贝 ID"),
    limit: int = Query(default=50, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_child_for_user(db, current_user, child_id)
    rows = (
        db.query(PointLedger)
        .filter(PointLedger.child_id == child_id)
        .order_by(PointLedger.id.desc())
        .limit(limit)
        .all()
    )
    return success(
        [
            LedgerItem(
                id=r.id,
                amount=r.amount,
                source_type=r.source_type,
                description=r.description,
                created_at=r.created_at,
            )
            for r in rows
        ]
    )
