from datetime import datetime, timedelta, timezone

BEIJING_TZ = timezone(timedelta(hours=8))


def beijing_now_ms() -> int:
    """获取当前北京时间对应的13位毫秒时间戳。"""
    return int(datetime.now(BEIJING_TZ).timestamp() * 1000)


def beijing_now() -> datetime:
    """获取当前北京时间。"""
    return datetime.now(BEIJING_TZ)


def ms_to_beijing_datetime(ms: int) -> datetime:
    """将13位毫秒时间戳转换为北京时间 datetime。"""
    return datetime.fromtimestamp(ms / 1000, tz=BEIJING_TZ)
