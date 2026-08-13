from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(11), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_pin_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subscription_tier: Mapped[str] = mapped_column(String(16), default="free")
    pro_expires_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    legacy_pro_trial_granted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)

    family_memberships: Mapped[list["FamilyMember"]] = relationship(back_populates="user")
    subscription: Mapped["Subscription | None"] = relationship(back_populates="user", uselist=False)


class EmailVerificationCode(Base):
    __tablename__ = "email_verification_codes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    purpose: Mapped[str] = mapped_column(String(16), default="login", index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(6), nullable=False)
    expires_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)


class Family(Base):
    __tablename__ = "families"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), default="我的家庭")
    invite_code: Mapped[str] = mapped_column(String(8), unique=True, index=True, nullable=False)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)

    children: Mapped[list["Child"]] = relationship(back_populates="family")
    members: Mapped[list["FamilyMember"]] = relationship(back_populates="family")


class FamilyMember(Base):
    __tablename__ = "family_members"
    __table_args__ = (UniqueConstraint("family_id", "user_id", name="uq_family_user"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), default="parent")
    joined_at: Mapped[int] = mapped_column(BigInteger, nullable=False)

    family: Mapped["Family"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="family_memberships")


class Child(Base):
    __tablename__ = "children"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"), index=True, nullable=False)
    nickname: Mapped[str] = mapped_column(String(32), nullable=False)
    gender: Mapped[str] = mapped_column(String(8), default="unknown")
    avatar_emoji: Mapped[str] = mapped_column(String(16), default="child")
    points: Mapped[int] = mapped_column(Integer, default=0)
    total_growth_value: Mapped[int] = mapped_column(Integer, default=0)
    current_stage: Mapped[int] = mapped_column(Integer, default=0)
    plant_name: Mapped[str] = mapped_column(String(32), default="小绿豆")
    plant_type: Mapped[str] = mapped_column(String(32), default="希望树")
    plant_planted: Mapped[bool] = mapped_column(Boolean, default=False)
    consecutive_checkin_days: Mapped[int] = mapped_column(Integer, default=0)
    total_checkin_days: Mapped[int] = mapped_column(Integer, default=0)
    badge_count: Mapped[int] = mapped_column(Integer, default=1)
    today_points_delta: Mapped[int] = mapped_column(Integer, default=0)
    puzzle_points_today: Mapped[int] = mapped_column(Integer, default=0)
    last_checkin_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)

    family: Mapped["Family"] = relationship(back_populates="children")
    tasks: Mapped[list["Task"]] = relationship(back_populates="child")
    rewards: Mapped[list["Reward"]] = relationship(back_populates="child")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    point_reward: Mapped[int] = mapped_column(Integer, default=5)
    growth_reward: Mapped[int] = mapped_column(Integer, default=5)
    frequency: Mapped[str] = mapped_column(String(16), default="daily")
    is_system_task: Mapped[bool] = mapped_column(Boolean, default=False)
    system_key: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=100)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)

    child: Mapped["Child"] = relationship(back_populates="tasks")
    completions: Mapped[list["TaskCompletion"]] = relationship(back_populates="task")


class TaskCompletion(Base):
    __tablename__ = "task_completions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True, nullable=False)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    task_date: Mapped[str] = mapped_column(String(10), nullable=False)
    submitted_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reviewed_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    task: Mapped["Task"] = relationship(back_populates="completions")


class Reward(Base):
    __tablename__ = "rewards"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(64), nullable=False)
    cost_points: Mapped[int] = mapped_column(Integer, nullable=False)
    emoji: Mapped[str] = mapped_column(String(16), default="gift")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)

    child: Mapped["Child"] = relationship(back_populates="rewards")


class RewardRedemption(Base):
    __tablename__ = "reward_redemptions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    reward_id: Mapped[int] = mapped_column(ForeignKey("rewards.id"), index=True, nullable=False)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    submitted_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reviewed_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)


class PointLedger(Base):
    __tablename__ = "point_ledgers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id"), index=True, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)


class GrowthLedger(Base):
    __tablename__ = "growth_ledgers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id"), index=True, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    tier: Mapped[str] = mapped_column(String(16), default="free")
    product_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    original_transaction_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    expires_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(16), default="apple")
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)

    user: Mapped["User"] = relationship(back_populates="subscription")
