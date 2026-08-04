from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_SERVE_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_DB = _SERVE_ROOT / "lvyabao.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    secret_key: str = "change-me-in-production-use-env-var"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days
    # 固定落在 lvyabao-serve 目录，避免 uvicorn 工作目录不同导致「每次登录都是新家庭」
    database_url: str = f"sqlite:///{_DEFAULT_DB}"
    verification_code_expire_minutes: int = 10
    verification_code_resend_seconds: int = 60
    # 开发环境可在日志中打印验证码；生产环境应配置 SMTP
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@lvyabao.app"
    expose_code_in_response: bool = False


settings = Settings()
