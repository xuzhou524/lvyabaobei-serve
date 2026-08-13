# 绿芽宝贝 API 接口文档

> 服务：FastAPI · 版本 `1.0.0` · 默认地址 `http://127.0.0.1:8010`  
> 交互式文档：启动服务后访问 [`/docs`](http://127.0.0.1:8010/docs)（Swagger）、[`/redoc`](http://127.0.0.1:8010/redoc)

---

## 1. 通用约定

### 1.1 鉴权

| 范围 | 说明 |
|------|------|
| 无需 Token | `POST /auth/*`、`GET /health` |
| 需登录 | 其余所有接口 |

请求头：

```http
Authorization: Bearer <access_token>
Accept: application/json
Content-Type: application/json
```

### 1.2 统一响应

成功与业务失败均通常返回 **HTTP 200**，通过 body 内 `code` 区分：

```json
{
  "code": 200,
  "data": {},
  "message": "成功"
}
```

| `code` | 含义 |
|--------|------|
| `200` | 成功，`data` 为业务载荷 |
| `401` | 未登录、Token 失效、家长密码错误等 |
| `403` | 无权限（如编辑系统新手任务） |
| `404` | 资源不存在 |
| `409` | 业务冲突（重复提交、积分不足等） |
| `422` | 请求参数校验失败 |
| `429` | 频率/上限（如今日益智积分已满） |

### 1.3 路径与参数

**URL 路径中不出现 `{id}` 等动态段。** 业务 ID 与筛选条件按下列方式传递：

| 方法 | 参数位置 |
|------|----------|
| `GET` | Query String，如 `?child_id=1&category=all` |
| `DELETE` | Query String，如 `?task_id=10` |
| `POST` / `PUT` | JSON Body，如 `{ "child_id": 1, "task_id": 10 }` |

### 1.4 数据权限

- 用户登录后绑定一个家庭；`child_id` 相关接口仅能操作**本家庭**下的宝贝。
- 时间戳字段（如 `created_at`、`submitted_at`）为 **毫秒**，北京时间语义下的「今日」以服务端为准。

---

## 2. 系统

### GET `/health`

健康检查（无需鉴权）。

**响应 `data`**

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | string | 固定 `"ok"` |
| `database_url` | string | 当前数据库连接配置 |

---

## 3. 认证 `/auth`

### POST `/auth/send-code`

发送邮箱验证码（注册或邮箱验证码登录）。

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `email` | string | 是 | 邮箱 |
| `purpose` | string | 否 | `register`（注册，邮箱/手机号须未占用）或 `login`（登录，邮箱须已注册），默认 `login` |
| `phone` | string | 注册时必填 | 11 位手机号，注册时用于校验手机号是否已占用 |

**响应 `data`（SendCodeData）**

| 字段 | 类型 | 说明 |
|------|------|------|
| `email` | string | 规范化后的邮箱 |
| `expires_in_seconds` | int | 验证码有效秒数 |
| `debug_code` | string \| null | 仅开发/未配置 SMTP 时可能返回，便于调试 |

**message**：`验证码已发送`

---

### POST `/auth/register`

注册新账号（手机号 + 邮箱 + 邮箱验证码 + 密码），并 **自动创建家庭**。

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `phone` | string | 是 | 11 位手机号 |
| `email` | string | 是 | 邮箱 |
| `code` | string | 是 | 6 位邮箱验证码（`purpose=register` 发送） |
| `password` | string | 是 | 8–32 位，须含字母与数字 |

**响应 `data`（TokenData）**

| 字段 | 类型 | 说明 |
|------|------|------|
| `access_token` | string | JWT |
| `token_type` | string | 默认 `"bearer"` |

**message**：`注册成功`

---

### POST `/auth/login`

登录（两种方式）。

**请求体 · 手机号 + 密码（默认）**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `login_type` | string | 是 | 固定 `phone_password` |
| `phone` | string | 是 | 11 位手机号 |
| `password` | string | 是 | 登录密码 |

**请求体 · 邮箱 + 验证码**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `login_type` | string | 是 | 固定 `email_code` |
| `email` | string | 是 | 已注册邮箱 |
| `code` | string | 是 | 6 位邮箱验证码（`purpose=login` 发送） |

**响应 `data`（TokenData）**

| 字段 | 类型 | 说明 |
|------|------|------|
| `access_token` | string | JWT |
| `token_type` | string | 默认 `"bearer"` |

---

## 4. 用户 `/user`

### GET `/user/info`

当前用户信息。

**响应 `data`（UserInfo）**

| 字段 | 类型 | 说明 |
|------|------|------|
| `phone` | string | 脱敏手机号 |
| `email` | string | 邮箱 |
| `has_parent_pin` | bool | 是否已设置家长密码 |
| `family_id` | int \| null | 家庭 ID |
| `invite_code` | string \| null | 家庭邀请码 |

---

### PUT `/user/parent-pin`

设置 4 位数字家长密码。

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `pin` | string | 是 | 4 位数字 |

**响应 `data`**：`{ "ok": true }`

---

### POST `/user/verify-parent-pin`

验证家长密码（宝贝模式切换家长模式）。

**请求体**：同 `parent-pin`

**响应 `data`**：`{ "ok": true }`

**错误**：密码错误时 `code: 401`，`message: 家长密码错误`

---

## 5. 家庭与待办

### GET `/family`

**响应 `data`（FamilyInfo）**

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 家庭 ID |
| `name` | string | 家庭名称 |
| `invite_code` | string | 邀请码 |

---

### GET `/family/members`

当前家庭成员列表（邮箱脱敏）。

**响应 `data`**：`FamilyMemberItem[]`

| 字段 | 类型 | 说明 |
|------|------|------|
| `email` | string | 脱敏邮箱 |
| `role` | string | `owner` 或 `parent` |
| `is_self` | bool | 是否为当前登录用户 |

---

### POST `/family/join`

使用邀请码加入其他家庭。

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `invite_code` | string | 是 | 4–8 位，大小写不敏感 |

**响应 `data`**：同 `FamilyInfo`

**规则**

- 已在目标家庭：成功，`message` 为「您已在该家庭中」
- 邀请码不存在：`404`
- 当前家庭已有宝贝：`409`，需用新账号注册后再加入

---

### GET `/pending`

家长待处理列表：待确认任务 + 待审批兑换。

**响应 `data`**：`PendingItem[]`

| 字段 | 类型 | 说明 |
|------|------|------|
| `kind` | string | `"task"` 或 `"reward"` |
| `id` | int | `kind=task` 时为 **task_id**；`kind=reward` 时为 **redemption_id** |
| `title` | string | 任务或奖励标题 |
| `child_nickname` | string | 宝贝昵称 |
| `submitted_at` | int | 提交时间（毫秒） |

---

## 6. 宝贝 `/children`

### GET `/children`

本家庭宝贝列表。

**响应 `data`**：`ChildSummary[]`

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 宝贝 ID |
| `nickname` | string | 昵称 |
| `gender` | string | `boy` / `girl` / `unknown` |
| `avatar_emoji` | string | 头像 emoji 键 |
| `points` | int | 当前积分 |
| `total_growth_value` | int | 累计成长值 |
| `current_stage` | int | 植物阶段序号 |
| `plant_name` | string | 植物名称 |
| `plant_planted` | bool | 是否已种下（新手任务完成后为 true） |
| `consecutive_checkin_days` | int | 连续打卡天数 |
| `total_checkin_days` | int | 累计打卡天数 |
| `badge_count` | int | 徽章数量 |

---

### POST `/children`

添加宝贝，并自动创建 **3 个新手系统任务**。

**请求体（ChildCreateRequest）**

| 字段 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `nickname` | string | 是 | — | 1–32 字 |
| `gender` | string | 否 | `unknown` | `boy` / `girl` / `unknown` |
| `avatar_emoji` | string | 否 | `child` | 最长 16 |

**响应 `data`**：`ChildSummary`

---

### PUT `/children`

编辑宝贝资料。

**请求体（ChildUpdateRequest）**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `child_id` | int | 是 | 宝贝 ID |
| `nickname` | string | 否 | 昵称 |
| `gender` | string | 否 | 性别 |
| `avatar_emoji` | string | 否 | 头像 emoji |

**响应 `data`**：`ChildSummary`

---

### DELETE `/children`

**Query**：`child_id`（必填）

**物理删除**宝贝及关联任务、流水、奖励等。再次添加同名宝贝视为新档案。

**响应 `data`**：`{ "deleted": true }`

---

### GET `/children/home`

**Query**：`child_id`（必填）

首页聚合数据。

**响应 `data`（HomeDashboard）**

| 字段 | 类型 | 说明 |
|------|------|------|
| `child` | ChildSummary | 宝贝摘要 |
| `plant` | PlantInfo | 植物信息 |
| `today_tasks` | TaskItem[] | 今日可见任务（最多 20 条） |
| `consecutive_checkin_days` | int | 连续打卡 |
| `total_checkin_days` | int | 累计打卡 |
| `badge_count` | int | 徽章 |
| `today_points_delta` | int | 今日已获得积分增量 |
| `onboarding_just_completed` | bool | 本次请求是否刚完成新手引导（种下种子） |

---

## 7. 任务

### GET `/tasks`

**Query**

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `child_id` | int | — | 必填，宝贝 ID |
| `category` | string | `all` | `all` / `study` / `chore` / `habit` / `sport` |

**响应 `data`**：`TaskItem[]`

**TaskItem**

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 任务 ID |
| `title` | string | 标题 |
| `category` | string | 分类 |
| `point_reward` | int | 积分奖励 |
| `growth_reward` | int | 成长值奖励 |
| `frequency` | string | `daily` / `once` |
| `is_system_task` | bool | 是否系统新手任务 |
| `sort_order` | int | 排序 |
| `status` | string | `open` / `pending` / `approved` / `rejected` |
| `completion_id` | int \| null | 当日（或 once 任务）完成记录 ID |

---

### POST `/tasks`

家长添加任务。

**请求体（TaskCreateRequest）**

| 字段 | 类型 | 必填 | 默认 | 约束 |
|------|------|------|------|------|
| `child_id` | int | 是 | — | 宝贝 ID |
| `title` | string | 是 | — | 1–64 字 |
| `category` | string | 是 | — | `study` / `chore` / `habit` / `sport` |
| `point_reward` | int | 否 | 5 | 1–100 |
| `growth_reward` | int | 否 | 5 | 1–50 |
| `frequency` | string | 否 | `daily` | `daily` / `once` |

**响应 `data`**：`TaskItem`

---

### PUT `/tasks`

编辑任务。**系统新手任务不可编辑**（`403`）。

**请求体（TaskUpdateRequest）**：`task_id`（必填），以及可选 `title` / `category` / `point_reward` / `growth_reward` / `frequency`。

**响应 `data`**：`TaskItem`

---

### DELETE `/tasks`

**Query**：`task_id`（必填）

删除任务。**系统新手任务不可删除**（`403`）。

**响应 `data`**：`{ "deleted": true }`

---

### POST `/tasks/reorder`

调整非系统任务排序。

**请求体**

| 字段 | 类型 | 说明 |
|------|------|------|
| `child_id` | int | 宝贝 ID |
| `task_ids` | int[] | 期望顺序的任务 ID 列表 |

**响应 `data`**：`{ "ok": true }`

---

### POST `/tasks/submit`

**请求体**：`{ "task_id": int }`

宝贝提交「已完成」申请。

**响应 `data`**：`TaskItem`

**错误**：今日已 pending 或 approved → `409`

---

### POST `/tasks/approve`

**请求体**：`{ "task_id": int }`

家长确认；积分与成长值入账，并可能触发新手完成、种下种子。

**响应 `data`**：`TaskItem`

**错误**：无待确认申请 → `404`

---

### POST `/tasks/reject`

**请求体**：`{ "task_id": int }`

家长拒绝待确认申请。

**响应 `data`**：`TaskItem`

---

## 8. 成长与积分

### GET `/growth/plant`

**Query**：`child_id`（必填）

**响应 `data`（PlantInfo）**

| 字段 | 类型 | 说明 |
|------|------|------|
| `plant_name` | string | 植物名 |
| `plant_type` | string | 植物类型 |
| `plant_planted` | bool | 是否已种下 |
| `stage` | int | 当前阶段 |
| `stage_emoji` | string | 阶段 emoji |
| `stage_name` | string | 阶段名称 |
| `total_growth_value` | int | 累计成长值 |
| `progress_current` | int | 当前阶段内进度 |
| `progress_total` | int | 当前阶段进度总量 |
| `progress_hint` | string | 进度提示文案 |
| `stages` | PlantStagePreview[] | 各阶段预览 |

**PlantStagePreview**：`stage`, `emoji`, `name`, `threshold`

阶段阈值（成长值）：0 → 50 → 150 → 300 → 500 → 800（详见 `app/plant_stages.py`）。

---

### PUT `/growth/plant/name`

**请求体**：`{ "child_id": int, "plant_name": string }`（plant_name 1–32 字）

**响应 `data`**：`PlantInfo`

---

### POST `/growth/plant/reset`

**请求体**：`{ "child_id": int }`

重置植物为种子状态（成长值清零等）。

**响应 `data`**：`PlantInfo`

---

### GET `/growth/ledger`

**Query**：`child_id`（必填），`limit` 默认 `50`，最大 `200`

**响应 `data`**：`LedgerItem[]`

**LedgerItem**：`id`, `amount`, `source_type`, `description`, `created_at`

---

### GET `/growth/report`

**Query**：`child_id`（必填）

周报摘要。

**响应 `data`（GrowthReportSummary）**

| 字段 | 类型 | 说明 |
|------|------|------|
| `week_label` | string | 如「本周」 |
| `tasks_completed` | int | 已完成任务数（统计口径见实现） |
| `tasks_total` | int | 任务总数 |
| `points_earned` | int | 积分相关 |
| `growth_earned` | int | 成长相关 |
| `puzzle_minutes_estimate` | int | 益智时长估算 |

---

### POST `/games/complete`

完成益智训练领取奖励。

**请求体（GameCompleteRequest）**

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `child_id` | int | — | 必填，宝贝 ID |
| `game_key` | string | `schulte` | 训练标识 |

**响应 `data`（GameCompleteResult）**

| 字段 | 类型 | 说明 |
|------|------|------|
| `points_added` | int | 本次增加积分 |
| `growth_added` | int | 本次增加成长值（默认 2） |
| `puzzle_points_today` | int | 今日已通过训练获得的积分累计 |
| `puzzle_daily_cap` | int | 日上限，默认 15 |

**规则**：默认每次 +3 积分、+2 成长值；达日上限 `429`。若存在新手任务「完成一次专注训练」，可自动产生 pending 完成记录供家长确认。

---

### GET `/points/ledger`

**Query**：`child_id`（必填），`limit` 默认 `50`，最大 `200`

积分流水。

**响应 `data`**：`LedgerItem[]`

---

## 9. 奖励

### GET `/rewards`

**Query**：`child_id`（必填）

仅返回 `is_active=true` 的奖励项。

**响应 `data`**：`RewardItem[]`

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 奖励 ID |
| `title` | string | 标题 |
| `cost_points` | int | 兑换所需积分 |
| `emoji` | string | 展示 emoji |
| `is_active` | bool | 是否上架 |
| `pending_redemption_id` | int \| null | 若有待审批兑换，则为 redemption ID |

---

### POST `/rewards`

**请求体（RewardCreateRequest）**

| 字段 | 类型 | 必填 | 默认 |
|------|------|------|------|
| `child_id` | int | 是 | — |
| `title` | string | 是 | — |
| `cost_points` | int | 是 | 1–9999 |
| `emoji` | string | 否 | `gift` |

**响应 `data`**：`RewardItem`

---

### PUT `/rewards`

**请求体（RewardUpdateRequest）**：`reward_id`（必填），以及可选 `title` / `cost_points` / `emoji` / `is_active`。

**响应 `data`**：`RewardItem`

---

### DELETE `/rewards`

**Query**：`reward_id`（必填）

软下架（`is_active=false`）。

**响应 `data`**：`{ "deleted": true }`

---

### POST `/rewards/redeem`

**请求体**：`{ "reward_id": int }`

宝贝申请兑换。

**响应 `data`**：`RewardItem`

**错误**：已有 pending 兑换 → `409`

---

### POST `/redemptions/approve`

**请求体**：`{ "redemption_id": int }`

家长通过；扣减积分。

**响应 `data`**：`{ "approved": true }`

**错误**：积分不足或已处理 → `409`

---

### POST `/redemptions/reject`

**请求体**：`{ "redemption_id": int }`

**响应 `data`**：`{ "rejected": true }`

---

## 10. 业务规则摘要

| 主题 | 规则 |
|------|------|
| 新手任务 | 添加宝贝时创建 3 个系统任务；家长全部确认后 `plant_planted=true` |
| 成长值 | 只增不减（重置植物除外） |
| 积分 | 任务、训练增加；兑换奖励减少 |
| 系统任务 | 不可 PUT / DELETE |
| 删除宝贝 | 物理删除，级联关联数据 |

---

## 11. 接口索引

| # | 方法 | 路径 | 参数 | 鉴权 |
|---|------|------|------|------|
| 1 | GET | `/health` | — | 否 |
| 2 | POST | `/auth/send-code` | body | 否 |
| 3 | POST | `/auth/login` | body | 否 |
| 4 | GET | `/user/info` | — | 是 |
| 5 | PUT | `/user/parent-pin` | body | 是 |
| 6 | POST | `/user/verify-parent-pin` | body | 是 |
| 7 | GET | `/family` | — | 是 |
| 8 | GET | `/pending` | — | 是 |
| 9 | GET | `/children` | — | 是 |
| 10 | POST | `/children` | body | 是 |
| 11 | PUT | `/children` | body | 是 |
| 12 | DELETE | `/children` | query: child_id | 是 |
| 13 | GET | `/children/home` | query: child_id | 是 |
| 14 | GET | `/tasks` | query | 是 |
| 15 | POST | `/tasks` | body | 是 |
| 16 | PUT | `/tasks` | body | 是 |
| 17 | DELETE | `/tasks` | query: task_id | 是 |
| 18 | POST | `/tasks/reorder` | body | 是 |
| 19 | POST | `/tasks/submit` | body | 是 |
| 20 | POST | `/tasks/approve` | body | 是 |
| 21 | POST | `/tasks/reject` | body | 是 |
| 22 | GET | `/growth/plant` | query: child_id | 是 |
| 23 | PUT | `/growth/plant/name` | body | 是 |
| 24 | POST | `/growth/plant/reset` | body | 是 |
| 25 | GET | `/growth/ledger` | query | 是 |
| 26 | GET | `/growth/report` | query: child_id | 是 |
| 27 | POST | `/games/complete` | body | 是 |
| 28 | GET | `/points/ledger` | query | 是 |
| 29 | GET | `/rewards` | query: child_id | 是 |
| 30 | POST | `/rewards` | body | 是 |
| 31 | PUT | `/rewards` | body | 是 |
| 32 | DELETE | `/rewards` | query: reward_id | 是 |
| 33 | POST | `/rewards/redeem` | body | 是 |
| 34 | POST | `/redemptions/approve` | body | 是 |
| 35 | POST | `/redemptions/reject` | body | 是 |

**合计：35 个业务接口 + 1 个健康检查 = 36 个 HTTP 端点**

---

## 12. 本地启动

```bash
cd lvyabao-serve
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8010
```

数据库文件：`lvyabao-serve/lvyabao.db`（与启动目录无关）。
