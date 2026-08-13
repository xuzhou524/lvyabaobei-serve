from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class SendCodeRequest(BaseModel):
    email: EmailStr = Field(..., description="邮箱")
    purpose: Literal["register", "login"] = Field(default="login", description="register=注册, login=邮箱验证码登录")
    phone: str | None = Field(default=None, description="注册时必填，用于校验手机号是否已占用")

    @field_validator("purpose")
    @classmethod
    def validate_purpose(cls, v: str) -> str:
        if v not in {"register", "login"}:
            raise ValueError("purpose 须为 register 或 login")
        return v

    @model_validator(mode="after")
    def validate_register_phone(self) -> "SendCodeRequest":
        if self.purpose == "register" and not self.phone:
            raise ValueError("注册发送验证码时须填写手机号")
        return self


class RegisterRequest(BaseModel):
    phone: str = Field(..., min_length=11, max_length=20, description="手机号")
    email: EmailStr = Field(..., description="邮箱")
    code: str = Field(..., min_length=6, max_length=6, description="邮箱验证码")
    password: str = Field(..., min_length=8, max_length=32, description="登录密码")

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("验证码必须为 6 位数字")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        import re

        if not re.fullmatch(r"(?=.*[A-Za-z])(?=.*\d).{8,32}", v):
            raise ValueError("密码须为 8–32 位，且同时包含字母和数字")
        return v


class LoginRequest(BaseModel):
    login_type: Literal["phone_password", "email_code"] = Field(
        default="phone_password",
        description="phone_password=手机号+密码, email_code=邮箱+验证码",
    )
    phone: str | None = Field(default=None, description="手机号")
    password: str | None = Field(default=None, description="登录密码")
    email: EmailStr | None = Field(default=None, description="邮箱")
    code: str | None = Field(default=None, description="6 位邮箱验证码")

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not v.isdigit() or len(v) != 6:
            raise ValueError("验证码必须为 6 位数字")
        return v

    @model_validator(mode="after")
    def validate_login_fields(self) -> "LoginRequest":
        if self.login_type == "phone_password":
            if not self.phone or not self.password:
                raise ValueError("手机号和密码不能为空")
        elif self.login_type == "email_code":
            if not self.email or not self.code:
                raise ValueError("邮箱和验证码不能为空")
        return self


class SendCodeData(BaseModel):
    email: str
    expires_in_seconds: int
    debug_code: str | None = Field(default=None, description="仅开发调试时返回")


class TokenData(BaseModel):
    access_token: str
    token_type: str = "bearer"
