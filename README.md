# 绿芽宝贝 API

FastAPI 后端，支撑「任务积分 + 种植成长 + 家长/宝贝双模式」。

整体启动顺序（含 iOS）见 [`启动指南.md`](../启动指南.md)。  
生产环境部署与发版见 [`部署指南.md`](../部署指南.md)。

## 启动

```bash
cd lvyabao-serve
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8010
```

> 数据库文件固定为 **`lvyabao-serve/lvyabao.db`**（与从哪个目录启动 uvicorn 无关）。  
> 若曾用旧版数据库，请删除该文件后重启以重建表结构。

## 鉴权

除 `/auth/*`、`/health` 外，均需 Header：`Authorization: Bearer <token>`。

统一响应：`{ "code": 200, "data": ..., "message": "..." }`

**参数约定**：路径中不含 `{id}` 等动态段。`GET`/`DELETE` 用 **Query**（如 `?child_id=1`）；`POST`/`PUT` 用 **JSON Body** 传 `child_id`、`task_id` 等。详见 [`docs/API.md`](docs/API.md)。

## 接口一览

| 模块 | 方法 | 路径 | 主要参数 | 说明 |
|------|------|------|----------|------|
| 系统 | GET | `/health` | — | 健康检查 |
| 认证 | POST | `/auth/send-code` | body: email | 发送邮箱验证码 |
| 认证 | POST | `/auth/login` | body: email, code | 登录，自动创建家庭 |
| 用户 | GET | `/user/info` | — | 邮箱、家长密码、邀请码 |
| 用户 | PUT | `/user/parent-pin` | body: pin | 设置 4 位家长密码 |
| 用户 | POST | `/user/verify-parent-pin` | body: pin | 验证家长密码 |
| 家庭 | GET | `/family` | — | 家庭信息与邀请码 |
| 待办 | GET | `/pending` | — | 待确认任务 / 待审批兑换 |
| 宝贝 | GET/POST | `/children` | body（POST） | 列表 / 添加（含 3 个新手任务） |
| 宝贝 | PUT | `/children` | body: child_id, … | 编辑宝贝 |
| 宝贝 | DELETE | `/children` | query: child_id | 物理删除（级联） |
| 首页 | GET | `/children/home` | query: child_id | 花园 + 今日任务 |
| 任务 | GET | `/tasks` | query: child_id, category | 任务列表 |
| 任务 | POST | `/tasks` | body: child_id, … | 家长添加任务 |
| 任务 | PUT | `/tasks` | body: task_id, … | 编辑（系统任务不可改） |
| 任务 | DELETE | `/tasks` | query: task_id | 删除 |
| 任务 | POST | `/tasks/reorder` | body: child_id, task_ids | 排序 |
| 任务 | POST | `/tasks/submit` | body: task_id | 宝贝提交完成 |
| 任务 | POST | `/tasks/approve` | body: task_id | 家长确认 |
| 任务 | POST | `/tasks/reject` | body: task_id | 家长拒绝 |
| 成长 | GET | `/growth/plant` | query: child_id | 植物阶段与进度 |
| 成长 | PUT | `/growth/plant/name` | body: child_id, plant_name | 植物改名 |
| 成长 | POST | `/growth/plant/reset` | body: child_id | 重置为种子 |
| 成长 | GET | `/growth/ledger` | query: child_id, limit | 成长值流水 |
| 成长 | GET | `/growth/report` | query: child_id | 周报摘要 |
| 成长 | POST | `/games/complete` | body: child_id, game_key | 益智训练奖励 |
| 积分 | GET | `/points/ledger` | query: child_id, limit | 积分流水 |
| 奖励 | GET | `/rewards` | query: child_id | 奖励墙列表 |
| 奖励 | POST | `/rewards` | body: child_id, … | 添加奖励 |
| 奖励 | PUT | `/rewards` | body: reward_id, … | 编辑 / 上下架 |
| 奖励 | DELETE | `/rewards` | query: reward_id | 下架 |
| 奖励 | POST | `/rewards/redeem` | body: reward_id | 宝贝申请兑换 |
| 奖励 | POST | `/redemptions/approve` | body: redemption_id | 家长通过（扣积分） |
| 奖励 | POST | `/redemptions/reject` | body: redemption_id | 家长拒绝 |

## 业务规则摘要

- **新手任务**：添加宝贝时自动创建 3 个系统任务；家长全部确认后 `plant_planted=true`，触发「希望种子」。
- **植物阶段**：按累计成长值 0/50/150/300/500/800 映射种子→大树（见 `app/plant_stages.py`）。
- **成长值**只增不减；**积分**可因兑换奖励减少。
- **益智训练**：默认 +3 积分、+2 成长值，每日益智积分上限 15。

## 数据表

`users`, `families`, `family_members`, `children`, `tasks`, `task_completions`, `rewards`, `reward_redemptions`, `point_ledgers`, `growth_ledgers`, `operation_logs`
