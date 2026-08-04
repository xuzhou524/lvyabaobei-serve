import logging
import random
import smtplib
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger(__name__)


def generate_verification_code() -> str:
    return f"{random.randint(0, 999_999):06d}"


def send_verification_email(to_email: str, code: str) -> None:
    subject = "绿芽宝贝登录验证码"
    body = f"您的登录验证码为：{code}，{settings.verification_code_expire_minutes} 分钟内有效。如非本人操作请忽略此邮件。"

    if not settings.smtp_host:
        logger.info("[dev] 验证码邮件 -> %s : %s", to_email, code)
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from
    message["To"] = to_email
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(message)

    logger.info("验证码邮件已发送至 %s", to_email)
