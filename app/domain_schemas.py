from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class SendCodeRequest(BaseModel):
    email: EmailStr
    purpose: str = Field(default="login", pattern="^(register|login)$")


class RegisterRequest(BaseModel):
    phone: str = Field(..., min_length=11, max_length=20)
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)
    password: str = Field(..., min_length=8, max_length=32)

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("验证码必须为 6 位数字")
        return v


class LoginRequest(BaseModel):
    login_type: str = Field(default="phone_password", pattern="^(phone_password|email_code)$")
    phone: str | None = None
    password: str | None = None
    email: EmailStr | None = None
    code: str | None = None

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
    debug_code: str | None = None


class TokenData(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    phone: str
    email: str
    has_parent_pin: bool = False
    family_id: int | None = None
    invite_code: str | None = None
    subscription_tier: str = "free"
    pro_expires_at: int | None = None
    is_family_owner: bool = False
    pro_features: "ProFeatures"


class ProFeatures(BaseModel):
    max_children: int
    max_parents: int
    puzzle_daily_cap: int
    ledger_days: int | None = None
    growth_report_full: bool
    plant_reset: bool
    multi_parent: bool


class SubscriptionInfo(BaseModel):
    subscription_tier: str
    pro_expires_at: int | None = None
    is_family_owner: bool
    product_id: str | None = None
    pro_features: ProFeatures


class IapVerifyRequest(BaseModel):
    product_id: str = Field(..., min_length=3, max_length=64)
    transaction_id: str = Field(..., min_length=1, max_length=128)
    jws_representation: str | None = Field(default=None, max_length=8192)


class SetParentPinRequest(BaseModel):
    pin: str = Field(..., min_length=4, max_length=4)

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("家长密码须为 4 位数字")
        return v


class VerifyParentPinRequest(BaseModel):
    pin: str = Field(..., min_length=4, max_length=4)


class ChildCreateRequest(BaseModel):
    nickname: str = Field(..., min_length=1, max_length=32)
    gender: str = Field(default="unknown", pattern="^(boy|girl|unknown)$")
    avatar_emoji: str = Field(default="child", max_length=16)


class ChildUpdateRequest(BaseModel):
    child_id: int
    nickname: str | None = Field(default=None, max_length=32)
    gender: str | None = Field(default=None, pattern="^(boy|girl|unknown)$")
    avatar_emoji: str | None = Field(default=None, max_length=8)


class ChildIdRequest(BaseModel):
    child_id: int


class ChildSummary(BaseModel):
    id: int
    nickname: str
    gender: str
    avatar_emoji: str
    points: int
    total_growth_value: int
    current_stage: int
    plant_name: str
    plant_planted: bool
    consecutive_checkin_days: int
    total_checkin_days: int
    badge_count: int

    model_config = {"from_attributes": True}


class PlantStagePreview(BaseModel):
    stage: int
    emoji: str
    name: str
    threshold: int


class PlantInfo(BaseModel):
    plant_name: str
    plant_type: str
    plant_planted: bool
    stage: int
    stage_emoji: str
    stage_name: str
    total_growth_value: int
    progress_current: int
    progress_total: int
    progress_hint: str
    stages: list[PlantStagePreview]


class TaskItem(BaseModel):
    id: int
    title: str
    category: str
    point_reward: int
    growth_reward: int
    frequency: str
    is_system_task: bool
    sort_order: int
    status: str
    completion_id: int | None = None

    model_config = {"from_attributes": True}


class HomeDashboard(BaseModel):
    child: ChildSummary
    plant: PlantInfo
    today_tasks: list[TaskItem]
    consecutive_checkin_days: int
    total_checkin_days: int
    badge_count: int
    today_points_delta: int
    onboarding_just_completed: bool = False


class TaskCreateRequest(BaseModel):
    child_id: int
    title: str = Field(..., min_length=1, max_length=64)
    category: str = Field(..., pattern="^(study|chore|habit|sport)$")
    point_reward: int = Field(default=5, ge=1, le=100)
    growth_reward: int = Field(default=5, ge=1, le=50)
    frequency: str = Field(default="daily", pattern="^(daily|once)$")


class TaskUpdateRequest(BaseModel):
    task_id: int
    title: str | None = Field(default=None, max_length=64)
    category: str | None = Field(default=None, pattern="^(study|chore|habit|sport)$")
    point_reward: int | None = Field(default=None, ge=1, le=100)
    growth_reward: int | None = Field(default=None, ge=1, le=50)
    frequency: str | None = Field(default=None, pattern="^(daily|once)$")


class TaskReorderRequest(BaseModel):
    child_id: int
    task_ids: list[int]


class TaskIdRequest(BaseModel):
    task_id: int


class RewardItem(BaseModel):
    id: int
    title: str
    cost_points: int
    emoji: str
    is_active: bool
    pending_redemption_id: int | None = None

    model_config = {"from_attributes": True}


class RewardCreateRequest(BaseModel):
    child_id: int
    title: str = Field(..., min_length=1, max_length=64)
    cost_points: int = Field(..., ge=1, le=9999)
    emoji: str = Field(default="gift", max_length=16)


class RewardUpdateRequest(BaseModel):
    reward_id: int
    title: str | None = Field(default=None, max_length=64)
    cost_points: int | None = Field(default=None, ge=1, le=9999)
    emoji: str | None = Field(default=None, max_length=8)
    is_active: bool | None = None


class RewardIdRequest(BaseModel):
    reward_id: int


class RedemptionIdRequest(BaseModel):
    redemption_id: int


class LedgerItem(BaseModel):
    id: int
    amount: int
    source_type: str
    description: str
    created_at: int


class LedgerListData(BaseModel):
    items: list[LedgerItem]
    days_limit: int | None = None
    is_limited: bool = False


class GrowthReportDailyItem(BaseModel):
    day_label: str
    tasks_completed: int


class GrowthReportSummary(BaseModel):
    week_label: str
    tasks_completed: int
    tasks_total: int
    points_earned: int | None = None
    growth_earned: int
    puzzle_minutes_estimate: int | None = None
    is_full: bool = False
    daily_breakdown: list[GrowthReportDailyItem] | None = None
    upgrade_hint: str | None = None


class GameCompleteRequest(BaseModel):
    child_id: int
    game_key: str = Field(default="schulte", max_length=32)


class GameCompleteResult(BaseModel):
    points_added: int
    growth_added: int
    puzzle_points_today: int
    puzzle_daily_cap: int = 15


class PlantRenameRequest(BaseModel):
    child_id: int
    plant_name: str = Field(..., min_length=1, max_length=32)


class FamilyInfo(BaseModel):
    id: int
    name: str
    invite_code: str


class JoinFamilyRequest(BaseModel):
    invite_code: str = Field(..., min_length=4, max_length=8)

    @field_validator("invite_code")
    @classmethod
    def normalize_invite(cls, v: str) -> str:
        normalized = "".join(v.split()).upper()
        if not normalized:
            raise ValueError("邀请码不能为空")
        return normalized


class FamilyMemberItem(BaseModel):
    phone: str
    email: str
    role: str
    is_self: bool = False


class PendingItem(BaseModel):
    kind: str
    id: int
    title: str
    child_nickname: str
    submitted_at: int
