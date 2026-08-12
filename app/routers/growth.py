from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.child_access import get_child_for_user, get_user_family, today_beijing_str
from app.database import get_db
from app.deps import get_current_user
from app.domain_schemas import (
    ChildIdRequest,
    GameCompleteRequest,
    GameCompleteResult,
    GrowthReportDailyItem,
    GrowthReportSummary,
    LedgerItem,
    LedgerListData,
    PlantInfo,
    PlantRenameRequest,
)
from app.exceptions import BusinessException
from app.models import GrowthLedger, PointLedger, Task, TaskCompletion, User
from app.plant_stages import stage_for_growth
from app.response import ApiResponse, success
from app.serializers import build_plant_info
from app.services.rewards_engine import _add_growth_ledger, _add_point_ledger
from app.subscription_service import get_family_features, ledger_cutoff_ms
from app.time_utils import beijing_now, beijing_now_ms

router = APIRouter(tags=["growth"])

GAME_POINT_REWARD = 3
GAME_GROWTH_REWARD = 2
DAY_LABELS = ["一", "二", "三", "四", "五", "六", "日"]


def _week_range_ms() -> tuple[int, int]:
    now = beijing_now()
    start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)


def _ledger_items(rows) -> list[LedgerItem]:
    return [
        LedgerItem(
            id=r.id,
            amount=r.amount,
            source_type=r.source_type,
            description=r.description,
            created_at=r.created_at,
        )
        for r in rows
    ]


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
    family = get_user_family(db, current_user)
    features = get_family_features(db, family)
    if not features.get("plant_reset"):
        raise BusinessException(
            403,
            "植物重置为 Pro 专属功能，升级后可使用",
            error_code="PRO_REQUIRED",
        )
    child = get_child_for_user(db, current_user, body.child_id)
    child.total_growth_value = 0
    child.current_stage = 0
    child.plant_planted = True
    child.plant_name = "小绿豆"
    db.commit()
    return success(build_plant_info(child))


@router.get("/growth/ledger", response_model=ApiResponse[LedgerListData])
def growth_ledger(
    child_id: int = Query(..., description="宝贝 ID"),
    limit: int = Query(default=50, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    family = get_user_family(db, current_user)
    features = get_family_features(db, family)
    get_child_for_user(db, current_user, child_id)
    cutoff = ledger_cutoff_ms(features)
    q = db.query(GrowthLedger).filter(GrowthLedger.child_id == child_id)
    if cutoff is not None:
        q = q.filter(GrowthLedger.created_at >= cutoff)
    rows = q.order_by(GrowthLedger.id.desc()).limit(limit).all()
    return success(
        LedgerListData(
            items=_ledger_items(rows),
            days_limit=features.get("ledger_days"),
            is_limited=features.get("ledger_days") is not None,
        )
    )


@router.get("/growth/report", response_model=ApiResponse[GrowthReportSummary])
def growth_report(
    child_id: int = Query(..., description="宝贝 ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    family = get_user_family(db, current_user)
    features = get_family_features(db, family)
    is_full = bool(features.get("growth_report_full"))
    child = get_child_for_user(db, current_user, child_id)
    week_start, week_end = _week_range_ms()

    tasks_total = db.query(Task).filter(Task.child_id == child.id, Task.is_hidden.is_(False)).count()
    tasks_completed = (
        db.query(TaskCompletion)
        .filter(
            TaskCompletion.child_id == child.id,
            TaskCompletion.status == "approved",
            TaskCompletion.reviewed_at >= week_start,
            TaskCompletion.reviewed_at < week_end,
        )
        .count()
    )
    growth_earned = (
        db.query(func.coalesce(func.sum(GrowthLedger.amount), 0))
        .filter(
            GrowthLedger.child_id == child.id,
            GrowthLedger.created_at >= week_start,
            GrowthLedger.created_at < week_end,
        )
        .scalar()
    )
    growth_earned = int(growth_earned or 0)

    if not is_full:
        return success(
            GrowthReportSummary(
                week_label="本周简报",
                tasks_completed=tasks_completed,
                tasks_total=max(tasks_total, 1),
                growth_earned=growth_earned,
                is_full=False,
                upgrade_hint="升级 Pro 查看完整周报：每日趋势、积分统计与专注训练时长",
            )
        )

    points_earned = (
        db.query(func.coalesce(func.sum(PointLedger.amount), 0))
        .filter(
            PointLedger.child_id == child.id,
            PointLedger.amount > 0,
            PointLedger.created_at >= week_start,
            PointLedger.created_at < week_end,
        )
        .scalar()
    )
    daily_breakdown: list[GrowthReportDailyItem] = []
    for i, label in enumerate(DAY_LABELS):
        day_start_dt = beijing_now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
            days=beijing_now().weekday() - i
        )
        day_end_dt = day_start_dt + timedelta(days=1)
        day_start = int(day_start_dt.timestamp() * 1000)
        day_end = int(day_end_dt.timestamp() * 1000)
        day_done = (
            db.query(TaskCompletion)
            .filter(
                TaskCompletion.child_id == child.id,
                TaskCompletion.status == "approved",
                TaskCompletion.reviewed_at >= day_start,
                TaskCompletion.reviewed_at < day_end,
            )
            .count()
        )
        daily_breakdown.append(GrowthReportDailyItem(day_label=label, tasks_completed=day_done))

    return success(
        GrowthReportSummary(
            week_label="本周完整报告",
            tasks_completed=tasks_completed,
            tasks_total=max(tasks_total, 1),
            points_earned=int(points_earned or 0),
            growth_earned=growth_earned,
            puzzle_minutes_estimate=child.puzzle_points_today * 2,
            is_full=True,
            daily_breakdown=daily_breakdown,
        )
    )


@router.post("/games/complete", response_model=ApiResponse[GameCompleteResult])
def complete_game(
    body: GameCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    family = get_user_family(db, current_user)
    features = get_family_features(db, family)
    puzzle_cap = int(features["puzzle_daily_cap"])
    child = get_child_for_user(db, current_user, body.child_id)
    if child.puzzle_points_today >= puzzle_cap:
        raise BusinessException(429, "今日益智训练积分已达上限")

    points = min(GAME_POINT_REWARD, puzzle_cap - child.puzzle_points_today)
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
            puzzle_daily_cap=puzzle_cap,
        )
    )


@router.get("/points/ledger", response_model=ApiResponse[LedgerListData])
def points_ledger(
    child_id: int = Query(..., description="宝贝 ID"),
    limit: int = Query(default=50, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    family = get_user_family(db, current_user)
    features = get_family_features(db, family)
    get_child_for_user(db, current_user, child_id)
    cutoff = ledger_cutoff_ms(features)
    q = db.query(PointLedger).filter(PointLedger.child_id == child_id)
    if cutoff is not None:
        q = q.filter(PointLedger.created_at >= cutoff)
    rows = q.order_by(PointLedger.id.desc()).limit(limit).all()
    return success(
        LedgerListData(
            items=_ledger_items(rows),
            days_limit=features.get("ledger_days"),
            is_limited=features.get("ledger_days") is not None,
        )
    )
