# E报销助手_f24016137 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking. 用户已选择在当前会话直接开发，已执行；验收范围详见 docs/verification.md。

**Goal:** 交付可本机演示的课程网站，依次完成有效制度查询、制度维护及授权查询本人单据。

**Architecture:** Flask 应用工厂组合身份、制度和单据模块；SQLite 持久化演示数据。服务端实施登录、角色、CSRF、授权和归属验证，HTML 模板与少量 JavaScript 提供蓝白界面。

**Tech Stack:** Python 3.12、Flask、SQLite、unittest、HTML/CSS/JavaScript。当前本机 Python 3.12.10 和 Flask 已可用。

**Spec:** `docs/superpowers/specs/2026-10-09-reimbursement-assistant-design.md`

## Global Constraints

- 制作可在本机浏览器演示的课程作业网站。
- 制度由行政专员乔姐维护，单据等业务事实由财务专员周敏核对。
- 所有制度、金额、人员及单据均为虚构教学数据，页面持续显示教学演示标识。
- 失效日期当天起不再有效。
- 同一制度系列最多存在一个覆盖某日的启用版本。
- 后端以登录会话中的用户身份过滤单据，不接受客户端指定查询对象。
- 周敏修改单据状态必须填写核对说明；记录核对人和时间。
- 默认仅监听本机，密钥持久化于本地忽略文件中，数据库及本地密钥不提交版本库。
- 第一阶段通过检查后继续第二阶段，最终交付两期功能；不接入真实财务数据，不部署公网。

## Review Focus

1. 中文查询中的空白和无匹配词：安全显示空结果，不推测制度；任务 2 验证。
2. 制度结束日期与新版本开始日期相同：允许接续，不允许实际日期重叠；任务 2 验证。
3. 客户端伪造角色、员工编号或单据编号：不能扩大权限；任务 1、4 验证。
4. 撤销授权后仍有旧页面或旧会话：再次请求必须拒绝；任务 4 验证。
5. 金额小数、负数和无效状态：金额用整数分精确处理，拒绝无效更新；任务 4 验证。

## 文件职责与接口

| 文件 | 职责 |
|---|---|
| `app/__init__.py` | `create_app(config: dict | None = None) -> Flask`，注册模块与错误处理 |
| `app/db.py`、`app/schema.sql` | `get_db() -> sqlite3.Connection`、`init_db() -> None`、数据约束与连接关闭 |
| `app/seed.py` | `seed_demo(today: date) -> None`，仅初始化空库；CLI 显式重置 |
| `app/auth.py` | 登录退出、`login_required(view)`、`role_required(role: str)`、`check_csrf() -> None` |
| `app/policies.py` | `find_policies(query: str, today: date) -> list`、`save_policy(data: dict, actor_id: int, policy_id: int | None = None) -> int` 和制度路由 |
| `app/claims.py` | 授权路由、`list_own_claims(user_id: int) -> list`、`get_own_claim(user_id: int, claim_id: int) -> Row | None`、`verify_claim(claim_id: int, actor_id: int, status: str, note: str) -> None` |
| `app/templates/` | 共用布局、制度查询详情、登录、两个后台、授权与本人单据页 |
| `app/static/style.css`、`app/static/app.js` | 响应式布局、交互反馈，不在客户端裁定权限 |
| `run.py`、`requirements.txt`、`.gitignore` | 本机启动、依赖声明、忽略数据库密钥缓存 |
| `tests/` | 临时数据库、独立测试客户端、业务与权限验收 |
| `README.md` | 启动、演示账号、重置和演示步骤 |

角色内部值固定为 `employee`、`admin`、`finance`。测试使用临时数据库和固定测试密钥；真实运行使用本地持久化密钥。金额字段为 `amount_cents`；制度字段采用 `series_key`、`effective_date`、`expiry_date`、`enabled`。日期使用 ISO 格式。

### Task 1：身份、数据库与可运行基础

**Files:** 创建 `app/__init__.py`、`app/db.py`、`app/schema.sql`、`app/seed.py`、`app/auth.py`、`run.py`、`requirements.txt`、`.gitignore`、`tests/support.py`、`tests/test_auth.py` 和基础登录模板。

**Interfaces:** 产生应用工厂、数据库连接、登录用户 `g.user`、角色装饰器和 CSRF 校验；后续任务均复用。会话只保存用户主键，每次请求从数据库读取真实角色。

- [x] 写测试：`test_login_and_logout` 断言正确凭据登录、错误密码拒绝、退出后受保护页面不可访问；`test_forged_role_ignored` 断言员工即使伪造会话角色也不能进入管理端；`test_missing_csrf_rejected` 断言修改请求返回 400。
- [x] 运行 `python -m unittest tests.test_auth -v`，确认实现前失败。
- [x] 实现上述接口及用户表，密码使用 Werkzeug 哈希，GET 请求不得修改数据；初始化会话密钥，Cookie 设 HttpOnly 和 SameSite=Lax，开发默认禁用调试模式。
- [x] 建立员工、另一员工、乔姐、周敏四个演示账号，生成有效、未生效、已失效及停用制度，以及两位员工的演示单据；日期相对于首次初始化当天生成。
- [x] 重跑测试，应全部通过；`test_restart_preserves_data` 断言创建第二个应用实例不会覆盖已更改数据。

### Task 2：有效制度查询与乔姐维护（第一期）

**Files:** 创建 `app/policies.py`、制度查询详情和管理模板、`tests/test_policies.py`；修改模块注册。

**Interfaces:** 消费任务 1 的数据库、`g.user`、身份和 CSRF 接口；产生制度查询与维护函数及 `/`、`/policies/<id>`、`/admin/policies`、新增和编辑路由。

- [x] 写测试 `test_effective_boundaries`：生效当日可查、失效当日不可查；`test_hidden_versions_not_public`：未生效、停用与过期详情也不得公开读取；`test_query_no_match`：空白查询可列出有效制度，无匹配显示无依据；`test_admin_only`：员工和财务不能直接提交制度修改。
- [x] 写 `test_series_overlap`：旧版本 `[2026-10-01,2026-10-09)` 与新版本 `[2026-10-09,∞)` 可共存，新版本从 `2026-10-08` 开始则拒绝；编辑自身版本不能误判冲突。`test_invalid_dates` 拒绝非法日期和结束不晚于开始。
- [x] 运行 `python -m unittest tests.test_policies -v`，确认实现前失败。
- [x] 实现有效性过滤和关键词匹配；标题、分类、关键词、正文参与匹配，用户输入参数绑定，结果仅展示数据库原文和版本信息。查询输入去首尾空白，支持预置常见报销词，不生成制度内容。
- [x] 实现乔姐维护及启停，所有字段由后端验证，启用版本写入前验证日期交集；无期限失效按无穷处理。保存失败重新显示字段及中文原因。
- [x] 重跑测试全部通过，检查有效制度页和乔姐维护流程；此检查完成才开始第二期。

### Task 3：第一期网页体验

**Files:** 创建 `app/templates/base.html`、`app/static/style.css`、`app/static/app.js`，完善登录及制度模板，创建 `tests/test_pages.py`。

**Interfaces:** 消费制度结果、当前用户和 CSRF 令牌；产生统一导航、演示标识、表单错误反馈和响应式页面，不增加独立业务 API。

- [x] 写 `test_public_pages_escape_html`：制度中 `<script>` 内容以文本显示；`test_teaching_banner`：公开页、登录页及管理页均包含教学演示标识。
- [x] 运行 `python -m unittest tests.test_pages -v`，确认新断言在实现前失败。
- [x] 实现蓝白页面：清晰品牌名称、制度搜索及分类卡片、来源详情、角色导航、乔姐表单、空结果和保存提示；用模板自动转义，避免 `innerHTML` 拼接用户文本。
- [x] 运行页面测试全部通过，并在浏览器检查桌面和窄屏布局、键盘表单提交、无匹配提示和长正文。

### Task 4：授权查询本人单据与周敏核对（第二期）

**Files:** 创建 `app/claims.py`、授权和个人单据模板、周敏后台模板、`tests/test_claims.py`；修改模块注册和导航。

**Interfaces:** 消费身份、角色、数据库和 CSRF 接口；产生 `/consent` 的同意及撤销操作、`/claims`、`/claims/<id>`、`/finance/claims` 与核对操作。每次查询在后端检查最新授权状态。

- [x] 写 `test_consent_required_and_revocation`：登录未同意拒绝查询，同意后成功，撤销后旧客户端再次请求也被拒绝；`test_only_own_claims`：两位员工各自仅可见本人数据，伪造查询参数无效，他人详情返回 404。
- [x] 写 `test_finance_only_verification`：员工、乔姐及未登录用户无法改状态；`test_verification_note_required`：空说明拒绝，成功核对记录周敏和时间。状态允许值固定为待核对、审批中、待付款、已付款、已退回。
- [x] 写 `test_amount_and_invalid_status`：12345 分显示 123.45 元，拒绝无效状态；若页面提供金额编辑则负数或超过两位小数拒绝；未核对记录显式显示“待周敏核对”。
- [x] 运行 `python -m unittest tests.test_claims -v`，确认实现前失败。
- [x] 实现授权保存与撤销、基于用户主键的归属 SQL 查询、周敏核对事务。员工不提供身份选择器，不接受客户端身份作为授权对象；无归属单据不泄露详情。
- [x] 实现员工与周敏页面及状态标签。员工可浏览本人未核对记录，但状态与说明标识为待核对信息，不能呈现为已确认结论。
- [x] 运行单据测试全部通过，再运行 `python -m unittest discover -v` 检查两期功能无回归。

### Task 5：交付验证与课程说明

**Files:** 创建 `README.md`、`docs/demo-guide.md`、`docs/verification.md`；更新依赖和计划勾选状态。

**Interfaces:** 消费上述完整网站和测试结果，产出可重复本地启动方式、课堂演示路线和如实记录的验收证据。

- [x] 运行全部单元测试并记录实际通过数量；每个测试使用临时数据库，不破坏演示库。
- [x] 启动本机服务，浏览器完成员工制度查询、乔姐更新、员工授权、本人单据查看、周敏核对、员工刷新及撤销授权的连续流程。
- [x] 检查窄屏、中文长内容、无结果、表单错误与持久化。浏览器能力不可用时明确注明未视觉验证，不用页面 HTTP 成功代替视觉结论。
- [x] 写启动说明：安装依赖、运行 `python run.py`、访问本地地址、四个演示账号、显式重置命令和数据存储位置；说明此版本使用关键词检索，数据全部虚构。
- [x] 写演示路线和验证记录，至少分别记录制度有效性、乔姐权限、周敏权限、本人归属、授权撤销、CSRF 六项实际结果；只记录完成的检查。
- [x] 确认数据库、密钥、缓存未进入待交付文件。按任务记录提交点；当前仓库 `.git` 只读，未获相应文件权限时保留完整文件及验证记录，不宣称已提交。

## 计划自查

- 第一、二期功能均有实现任务及验收归属。
- 角色权限与单据归属分别测试，授权不作为扩大权限的依据。
- 日期边界、冲突、自身编辑、空查询、HTML 转义、会话角色伪造及撤销后的旧请求均已覆盖。
- 公共接口与后续任务名称一致，金额存储使用整数分。
- 页面实际检查和自动测试分别记录；交付不声称公网部署或真实业务接入。
- 用户已审阅本计划并选择直接执行；实现和验收记录已保存。
