"""植物成长阶段阈值（与产品文档一致）。"""

STAGES: list[tuple[int, str, str, int]] = [
    # stage, emoji, name, threshold (累计成长值达到即处于该阶段)
    (0, "🌰", "种子", 0),
    (1, "🌱", "发芽", 50),
    (2, "🌿", "幼苗", 150),
    (3, "🌸", "开花", 300),
    (4, "🍎", "结果", 500),
    (5, "🌳", "大树", 800),
]


def stage_for_growth(total_growth: int) -> int:
    stage = 0
    for s, _, _, threshold in STAGES:
        if total_growth >= threshold:
            stage = s
    return stage


def next_stage_info(total_growth: int) -> tuple[int | None, str | None, int | None]:
    """返回 (下一阶段编号, 名称, 所需累计成长值)。"""
    current = stage_for_growth(total_growth)
    for s, _, name, threshold in STAGES:
        if s > current:
            return s, name, threshold
    return None, None, None


def progress_to_next(total_growth: int) -> tuple[int, int, str]:
    current = stage_for_growth(total_growth)
    thresholds = {s: t for s, _, _, t in STAGES}
    names = {s: n for s, _, n, _ in STAGES}
    current_threshold = thresholds[current]
    nxt_stage, nxt_name, next_threshold = next_stage_info(total_growth)
    if next_threshold is None:
        return total_growth - current_threshold, 1, "已经是最高阶段啦！"
    span = max(1, next_threshold - current_threshold)
    done = total_growth - current_threshold
    remaining = next_threshold - total_growth
    tasks_hint = max(1, (remaining + 9) // 10)
    return done, span, f"再完成约 {tasks_hint} 个任务就能{nxt_name}啦！"
