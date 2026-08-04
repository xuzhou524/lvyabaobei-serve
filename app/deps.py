from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.auth import get_user_by_id
from app.config import settings
from app.database import get_db
from app.exceptions import BusinessException
from app.models import User

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise BusinessException(401, "未登录，请先登录")

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise BusinessException(401, "登录已失效，请重新登录") from None

    user = get_user_by_id(db, user_id)
    if not user:
        raise BusinessException(401, "用户不存在")

    return user
