from pydantic import BaseModel, EmailStr, Field, field_validator


class SendCodeRequest(BaseModel):
    email: EmailStr = Field(..., description="登录邮箱")


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="登录邮箱")
    code: str = Field(..., min_length=6, max_length=6, description="6 位邮件验证码")

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("验证码必须为 6 位数字")
        return v


class SendCodeData(BaseModel):
    email: str
    expires_in_seconds: int
    debug_code: str | None = Field(default=None, description="仅开发调试时返回")


class TokenData(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    email: str

    model_config = {"from_attributes": True}
