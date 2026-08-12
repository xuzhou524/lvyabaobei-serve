"""Pro 订阅 tier 与权益配额配置。"""

TIER_FEATURES: dict[str, dict] = {
    "free": {
        "max_children": 1,
        "max_parents": 1,
        "puzzle_daily_cap": 15,
        "ledger_days": 7,
        "growth_report_full": False,
        "plant_reset": False,
        "multi_parent": False,
    },
    "pro": {
        "max_children": 10,
        "max_parents": 5,
        "puzzle_daily_cap": 30,
        "ledger_days": None,
        "growth_report_full": True,
        "plant_reset": True,
        "multi_parent": True,
    },
}

IAP_PRODUCT_DURATIONS: dict[str, int | None] = {
    "com.lvyabaobei.pro.monthly": 30,
    "com.lvyabaobei.pro.quarterly": 90,
    "com.lvyabaobei.pro.yearly": 365,
    "com.lvyabaobei.pro.lifetime": None,
}
