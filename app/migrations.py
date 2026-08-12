"""SQLite 轻量迁移：为已有库补列、建表。"""

from sqlalchemy import inspect, text

from app.database import engine


def _column_names(table: str) -> set[str]:
    with engine.connect() as conn:
        rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return {row[1] for row in rows}


def _add_column_if_missing(table: str, column: str, ddl: str) -> None:
    if column in _column_names(table):
        return
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))


def _revoke_auto_trial_pro() -> None:
    """撤销未通过 IAP 购买的自动试用 Pro（幂等，可重复执行）。"""
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE users
                SET subscription_tier = 'free', pro_expires_at = NULL
                WHERE subscription_tier = 'pro'
                  AND id NOT IN (
                    SELECT user_id FROM subscriptions
                    WHERE is_active = 1 AND product_id IS NOT NULL
                  )
                """
            )
        )


def run_migrations() -> None:
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())

    if "users" in existing:
        _add_column_if_missing("users", "subscription_tier", "subscription_tier VARCHAR(16) DEFAULT 'free'")
        _add_column_if_missing("users", "pro_expires_at", "pro_expires_at BIGINT")
        _add_column_if_missing("users", "legacy_pro_trial_granted", "legacy_pro_trial_granted BOOLEAN DEFAULT 0")
        _revoke_auto_trial_pro()
