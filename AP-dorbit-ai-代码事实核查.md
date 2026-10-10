# AP-dorbit-ai 代码事实核查清单（供实习生简历改写）

> 核查范围：`C:\AP-dorbit-ai`（只读，未修改任何文件）
> 核查方法：AST 解析计数 + 逐文件阅读 + 设计文档交叉比对
> 约定：路径均为相对 `C:\AP-dorbit-ai\` 的路径；`原文摘录` 为代码/文档原始片段。
> **凡代码无法证实的，一律标注「无法确认」。**

---

## 一、仓库与代码规模总览

- 本目录是**三个互不隶属的子项目 + 一份文档集**，不是单一 Monorepo；`AP_Hub\ap_agent` 与 `AP_Hub\ap_agent_ui` 各自是独立 git 仓库 —— 证据：[docs/事实更正与工作规则.md:259] 「`C:\AP-dorbit-ai\docs\` 不在任何 git 仓库中（`AP_Hub\ap_agent` 与 `ap_agent_ui` 各自是独立仓库）」
- 后端 Python 文件数与行数（精确统计，排除 `__pycache__`）：**76 个 .py 文件 / 16,724 行**（`backend/app` 下）—— 证据：[AP_Hub/ap_agent/backend/app] 目录递归统计
- 后端分层规模：`api` 13 文件/2,368 行 · `services` 20 文件/9,851 行 · `core` 10 文件/1,395 行 · `models` 17 文件/1,327 行 · `schemas` 10 文件/673 行 · `tools` 2 文件/385 行 —— 证据：[AP_Hub/ap_agent/backend/app] 目录递归统计
- 后端最大单文件是 Agent 引擎 —— 证据：[AP_Hub/ap_agent/backend/app/services/claude_agent_sdk_service.py:1-2685] 「Claude Agent SDK 对话 Agent 服务。」（**2,685 行 / 133,899 字节**）
- 后端其余大文件：`myskill_service.py` 1,161 行 · `file_service.py` 839 行 · `api/conversations.py` 824 行 · `skill_registry_service.py` 767 行 · `docker_shell_backend.py` 623 行 · `file_watcher.py` 602 行 —— 证据：[AP_Hub/ap_agent/backend/app/services] 与 [AP_Hub/ap_agent/backend/app/api] 逐文件行数
- 前端技术栈：**Vue 3.5.12 + Vite 5.1.4 + Element Plus 2.11.3 + Pinia + ECharts + Monaco/CodeMirror + BPMN.js + UnoCSS/SCSS** —— 证据：[AP_Hub/ap_agent_ui/README.md:5-14] 「- **前端框架**: Vue 3 (Composition API), TypeScript；- **构建工具**: Vite；- **UI 组件库**: Element Plus」
- 前端 `package.json` 实测版本 —— 证据：[AP_Hub/ap_agent_ui/package.json] `vue: 3.5.12`、`vite: 5.1.4`、`element-plus: 2.11.3`
- ⚠️ **前端工程名暴露其开源母体** —— 证据：[AP_Hub/ap_agent_ui/package.json] `"name": "yudao-ui-admin-vue3"`，`"version": "2.4.1-snapshot"`。即前端是在开源项目 **芋道 yudao-ui-admin-vue3** 基础上二次开发的，含大量与 Agent 无关的遗留模块（BPM 设计器、商城 `store/modules/mall/kefu.ts`、支付图标、验证码组件等）——证据：[AP_Hub/ap_agent_ui/src/store/modules/mall/kefu.ts]、[AP_Hub/ap_agent_ui/src/assets/svgs/pay/icon/] 等
- 前端 AP-Agent 业务视图（自有开发部分）规模：`src/views/ap-agent/` 下 **51 个 .vue + 14 个 .js + 1 个 .css + 1 个 .ts + 3 个 .md** —— 证据：[AP_Hub/ap_agent_ui/src/views/ap-agent] 目录递归统计
- 后端 REST 路由文件共 **12 个模块**（`api/` 下 12 个非 `__init__` 文件）—— 证据：[AP_Hub/ap_agent/backend/app/api] 目录列表：artifacts / auth / conversations / files / folders / health / preview / projects / references / skill_registry / skills / workspaces
- 路由注册方式为 `create_app()` 工厂 + `include_router`，业务路由统一 `/api` 前缀，health 无前缀 —— 证据：[AP_Hub/ap_agent/backend/app/main.py:197-210] 「app.include_router(health_router) / app.include_router(auth_router, prefix="/api") …」

---

## 二、后端框架与 REST 接口计数

- 后端框架是 **FastAPI + SQLAlchemy 2.x 异步 ORM + MySQL(aiomysql)** —— 证据：[AP_Hub/ap_agent/backend/app/core/database.py:6] 「数据库后端固定为 MySQL（aiomysql 驱动）。」
- **REST 接口总数 = 71（精确，AST 口径）**。统计口径：对 `backend/app` 下全部 76 个 .py 做 Python `ast.parse`，遍历每个 `FunctionDef/AsyncFunctionDef` 的 `decorator_list`，统计装饰器名为 `router.<method>` 的调用节点；**此口径天然排除文档字符串里的示例**（如 `get_db` 的用法示例）。方法分布：**GET 36 / POST 22 / PUT 6 / DELETE 7 / PATCH 0** —— 证据：AST 全量统计结果
- 按模块拆分的 71 个端点 —— 证据：AST 全量统计结果
  `conversations.py` 19 · `skill_registry.py` 12 · `files.py` 7 · `folders.py` 6 · `skills.py` 6 · `auth.py` 5 · `projects.py` 5 · `workspaces.py` 5 · `health.py` 2 · `preview.py` 2 · `artifacts.py` 1 · `references.py` 1
- ⚠️ **「71」这个数字存在一个极易误数的陷阱，必须说明**：若用正则 `@router\.` 直接匹配，会得到 **72** 行命中，多出的一行是 `core/database.py:93` 的 `@router.get("/")` —— 该行位于 `get_db()` 的 **docstring 用法示例**中，不是真实路由 —— 证据：[AP_Hub/ap_agent/backend/app/core/database.py:92-95] 「    用法：\n        @router.get("/")\n        async def list_items(db: AsyncSession = Depends(get_db)):」
- 因此 **71 可复现，且是正确数字**；72 是正则误统计的结果 —— 证据：同上
- 71 个端点全部真实注册（12 个模块全部被 `main.py` include，无遗漏）—— 证据：[AP_Hub/ap_agent/backend/app/main.py:34-45] 与 [AP_Hub/ap_agent/backend/app/main.py:197-210]
- 另有 `Health` 端点带 `/health` 与 `/health/ready` 两个探针 —— 证据：[AP_Hub/ap_agent/backend/app/api/health.py:19,32] 「@router.get("/health")」「@router.get("/health/ready")」
- OpenAPI 安全方案为自定义 Bearer JWT，并显式列出 6 个公开操作 —— 证据：[AP_Hub/ap_agent/backend/app/main.py:239-253] 「schema["components"]["securitySchemes"]["BearerAuth"] = {…"bearerFormat": "JWT"…}」「public_ops = {("/api/auth/login","post"), ("/api/auth/aad-login","post"), ("/api/auth/refresh","post"), ("/api/preview/{project_id}","get"), ("/api/preview/{project_id}/{file_path:path}","get"), ("/health","get")}」

---

## 三、Claude Agent SDK 接入方式

- 接入方式为 **`ClaudeSDKClient`（connect + query + receive_response）长连接**，而非无状态 `query()` —— 证据：[AP_Hub/ap_agent/backend/app/services/claude_agent_sdk_service.py:6] 「- 使用 ClaudeSDKClient（connect + query + receive_response）实现多轮持续对话」
- 客户端创建与连接 —— 证据：[claude_agent_sdk_service.py:1914-1916] 「client = ClaudeSDKClient(options=options)」`await client.connect()`
- 发送本轮输入 —— 证据：[claude_agent_sdk_service.py:1173] 「await client.query(query_content)」
- 接收流式响应 —— 证据：[claude_agent_sdk_service.py:1191-1193] 「_merged_aiter = _merge_sdk_and_events(client.receive_response().__aiter__(), _event_queue).__aiter__()」
- 客户端按 conversation 缓存（`conversation_id → (client, prompt_hash, model)`），system prompt 或模型变化时重建 —— 证据：[claude_agent_sdk_service.py:487] 「# conversation_id → (ClaudeSDKClient, prompt_hash, model)」；[claude_agent_sdk_service.py:1897-1911] 「if old_hash == prompt_hash: … return client / else: … await _cleanup_client_locked(conversation_id)」
- **不使用 hooks**（明确的设计选择，直接解析流式消息）—— 证据：[claude_agent_sdk_service.py:7] 「- 直接解析流式消息（ToolUseBlock / ToolResultBlock），不依赖 hooks」
- 全仓 hooks 相关检索无 `HookMatcher` / `hooks=` 命中 —— 证据：对 `backend/app` 检索 `HookMatcher|hooks=` **零命中**
- **使用了 in-process MCP server**：自定义 `todo_write` 工具，server 名 `ap_tools` —— 证据：[claude_agent_sdk_service.py:202] 「from claude_agent_sdk import create_sdk_mcp_server, tool as _sdk_tool」；[claude_agent_sdk_service.py:233-237] 「_todo_mcp_server = create_sdk_mcp_server(name="ap_tools", version="1.0.0", tools=[_todo_write_handler])」；[claude_agent_sdk_service.py:2157] 「mcp_servers={"ap_tools": _get_todo_mcp_server()}」
- MCP 工具在 Agent 侧的名字为 `mcp__ap_tools__todo_write`，在 run 循环里被拦截处理 —— 证据：[claude_agent_sdk_service.py:1348] 「if tool_name == "mcp__ap_tools__todo_write":」
- `todo_write` 的 JSON Schema 与 handler —— 证据：[claude_agent_sdk_service.py:204-231] 「@_sdk_tool("todo_write", …)」「async def _todo_write_handler(args): … return {"content": [{"type": "text", "text": "todos updated"}]}」
- **使用了 subagent（具名子 agent，SDK 原生 `AgentDefinition`）** —— 证据：[claude_agent_sdk_service.py:1948-1958] 「from claude_agent_sdk import AgentDefinition / return {d["name"]: AgentDefinition(description=…, prompt=…, tools=…, model="inherit", permissionMode="default") for d in _SUBAGENT_DEFS}」
- 子 agent 定义外置在 `prompts/subagents.json`，由配置开关 `subagents_enabled` 控制（默认关闭 → 空 dict）—— 证据：[claude_agent_sdk_service.py:353-355] 「# 子 agent 总开关（settings.subagents_enabled，默认关闭）：关闭时 defs 为空，」「_SUBAGENT_DEFS = _load_subagent_defs() if get_settings().subagents_enabled else []」；定义文件 [AP_Hub/ap_agent/backend/app/prompts/subagents.json]
- **Skill 通过 system prompt 注入，而非 SDK 的 Skill 能力**：`_DISALLOWED_TOOLS` 里明确禁用了 SDK 原生 `Skill` 工具 —— 证据：[claude_agent_sdk_service.py:884-886] 「_DISALLOWED_TOOLS: list[str] = ["Task", "Skill", "MCP", "Monitor",]」；技能内容拼接见 [claude_agent_sdk_service.py:2605] 「return default_prompt + skill_header + skill.md_content」
- `ClaudeAgentOptions` 完整参数清单（含 streaming / thinking / buffer）—— 证据：[claude_agent_sdk_service.py:2135-2176]：
  `system_prompt` · `disallowed_tools` · `permission_mode="acceptEdits"` · `can_use_tool` · `max_turns=_MAX_AGENT_TURNS` · `cwd` · `model` · `env` · `stderr` · `allowed_tools=["Agent","Workflow","TaskOutput"]` · `mcp_servers` · `setting_sources=[]` · `agents` · `include_partial_messages=True` · `thinking={"type":"adaptive"}` · `max_thinking_tokens` · `max_buffer_size`
- 流式打字机效果开关 —— 证据：[claude_agent_sdk_service.py:2163-2164] 「# 启用流式 token 输出（打字机效果）」「include_partial_messages=True,」
- 扩展思考（adaptive）—— 证据：[claude_agent_sdk_service.py:2170-2171] 「thinking={"type": "adaptive"},」「max_thinking_tokens=self.settings.anthropic_thinking_budget,」
- 多租户隔离：禁用 SDK 读取主机级配置 —— 证据：[claude_agent_sdk_service.py:2016-2017] 「"CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1",」「"CLAUDE_CONFIG_DIR": sdk_config_dir,」；[claude_agent_sdk_service.py:2158-2159] 「# 多租户隔离：禁止 SDK 加载主机级文件系统配置」「setting_sources=[],」
- **SDK 使用 session resume 恢复多轮上下文**，session id 由 conversation GUID 转 UUID 格式得到 —— 证据：[claude_agent_sdk_service.py:258-264] 「def _format_session_id(guid: str) -> str: … return str(_uuid.UUID(guid))」；[claude_agent_sdk_service.py:1125-1126] 「if should_resume: options.resume = _format_session_id(conversation_id)」
- Windows 下为 SDK CLI 子进程强制 ProactorEventLoop —— 证据：[AP_Hub/ap_agent/backend/app/main.py:20-22] 「# Windows 下 claude_agent_sdk 创建 CLI 子进程需要 ProactorEventLoop」「asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())」
- SDK CLI 子进程 stderr 回调 + 致命错误快速失败 —— 证据：[claude_agent_sdk_service.py:2149] 「stderr=_make_stderr_callback(conversation_id, event_queue),」；[claude_agent_sdk_service.py:100] 「def _make_stderr_callback(conversation_id: str, event_queue: Any):」
- Agent 最大轮数 = **100** —— 证据：[claude_agent_sdk_service.py:484] 「_MAX_AGENT_TURNS = 100」
- 工具名映射表（SDK PascalCase → 前端 snake_case），共 13 条映射 —— 证据：[claude_agent_sdk_service.py:866-880] 「_TOOL_NAME_MAP: dict[str, str] = {"Read": "read_file", "Write": "write_file", "Edit": "edit_file", "Glob": "glob", "Grep": "grep", "WebSearch": "web_search", "WebFetch": "web_fetch", "Bash": "bash", "AskUserQuestion": "ask_user_question", "Agent": "sub_agent", "Workflow": "sub_agent", "TaskOutput": "sub_agent_output", "write_todos": "write_todos",}」
- 系统提示词文件 —— 证据：[AP_Hub/ap_agent/backend/app/prompts/claude_agent_sdk.md]（7,446 字节）、[AP_Hub/ap_agent/backend/app/prompts/skill_creation.md]、[AP_Hub/ap_agent/backend/app/prompts/subagents.json]

---

## 四、RunManager：长任务生命周期与状态机

- RunManager 的核心设计目标是**把 Agent 执行与 SSE 连接解耦**：执行由独立 producer 任务驱动，SSE 连接只是订阅者，断开仅取消订阅 —— 证据：[AP_Hub/ap_agent/backend/app/services/run_manager.py:1-4] 「Agent Run 管理器：Agent 执行与 SSE 连接解耦。核心思想：Agent run 由独立的 producer 任务驱动（跑完正常落库），SSE 连接只是事件流的"订阅者"——断开仅取消订阅，不影响执行。」
- 状态机共有 **4 个状态**：`running` / `completed` / `failed` / `cancelled` —— 证据：[run_manager.py:61] 「status: str = "running"  # running / completed / failed / cancelled」
- 状态迁移入口：`start()` 建 `running`；`finish(status)` 落终态；`stop()` 取消 —— 证据：[run_manager.py:127-135] `def start(...)`；[run_manager.py:137-149] `def finish(self, conversation_id: str, status: str)`；[run_manager.py:203-228] `async def stop(...)`
- producer/consumer 解耦的落地方式：producer 是 `asyncio.create_task` 创建的独立任务，**自建 DB session**（生命周期长于 HTTP 请求）—— 证据：[AP_Hub/ap_agent/backend/app/api/conversations.py:589-594] 「async def producer(): … 必须自建 DB session：请求级 session 在 HTTP 响应结束后关闭，而 producer 的生命周期长于请求。」；[conversations.py:628-630] 「handle.task = asyncio.create_task(producer(), name=f"agent-run-{conversation_id[:8]}")」
- producer 把 service 事件逐条 `handle.publish(event)` 广播，consumer 侧独立订阅 —— 证据：[conversations.py:599-610] 「async for event in service.run(...): … handle.publish(event)」
- producer 结束后的终态判定（区分 failed / completed / cancelled）—— 证据：[conversations.py:611-626] 「run_manager.finish(conversation_id, "failed" if saw_error else "completed")」「except asyncio.CancelledError: … run_manager.finish(conversation_id, "cancelled")」
- 有「首调度前被 cancel」的兜底回调，避免 handle 永久停在 running —— 证据：[conversations.py:632-639] 「def _on_producer_done(task): … if task.cancelled() and handle.status == "running": run_manager.finish(conversation_id, "cancelled")」
- 并发 run 冲突处理：**对话级互斥**，同一 conversation 只允许一个活跃 run —— 证据：[run_manager.py:7-8] 「- conversation 级互斥：同一对话同时只允许一个活跃 run」；[run_manager.py:130-132] 「existing = self._handles.get(conversation_id) / if existing is not None and existing.status == "running": raise RunActiveError(existing.run_id, conversation_id)」
- 冲突异常类型 —— 证据：[run_manager.py:46-52] 「class RunActiveError(Exception): … super().__init__(f"conversation {conversation_id} already has an active run")」
- ⚠️ **重要更正：409 的代码路径实际不可达，真实返回是 500，不是 409。** 三处证据：
  1. `RunActiveError` **不继承** `AppException` 或 `HTTPException` —— 证据：[run_manager.py:46] 「class RunActiveError(Exception):」（直接继承 `Exception`）
  2. 唯一把 `RunActiveError` 转 409 的 `try/except` 包住的是 `_agent_chat_sse(...)` 调用 —— 证据：[conversations.py:552-566] 「try: return _agent_chat_sse(...)」「except RunActiveError as exc: raise HTTPException(status_code=status.HTTP_409_CONFLICT, …)」
  3. 但真正抛异常的 `run_manager.start()` 在 `_agent_chat_sse` **内部**、且位于该函数自己的 `try` **之外** —— 证据：[conversations.py:587] 「handle = run_manager.start(conversation_id)  # 活跃 run → RunActiveError」（该行上方 582-586 行是一个独立的 `if` + `raise`，下方 589 行才进入 `async def producer` 的 `try`）
  ⇒ `RunActiveError` 会一路冒泡到全局 `@app.exception_handler(Exception)`，返回 **500** —— 证据：[AP_Hub/ap_agent/backend/app/core/exceptions.py:122-142] 「@app.exception_handler(Exception) … return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, …)」
  ⇒ 代码注释仍写「已有活跃 run 时返回 409」—— 证据：[conversations.py:549] 「对话已有活跃 run 时返回 409（防止 SDK session resume 冲突）。」（注释与实现不符）
- 另有 direct chat 与 agent 两条路径的对称互斥，这两处的 409 **是可达的**（直接 `raise HTTPException`）—— 证据：[conversations.py:582-586] 「if conversation_id in _direct_chat_active: raise HTTPException(status_code=status.HTTP_409_CONFLICT, …)」；[conversations.py:349-358]
- 已结束 handle 保留 600 秒供断线重连回放，之后惰性清除 —— 证据：[run_manager.py:42-43] 「FINISHED_HANDLE_TTL = 600.0」；[run_manager.py:249-259] 「def _purge_finished(self) -> None: …」
- 进程关闭时优雅取消所有活跃 run（15s 超时 + 2s 落库缓冲）—— 证据：[run_manager.py:230-245] 「async def shutdown_all(self, timeout: float = 15.0) … await asyncio.sleep(min(2.0, timeout))」
- 启动时清扫上次进程遗留的 pending/running run（超时窗口 + 300s 缓冲）—— 证据：[main.py:99-126] 「window = settings.agent_run_timeout + 300」「UPDATE harness_agent_runs SET status = 'failed' … WHERE status IN ('pending', 'running')」
- ⚠️ 架构限制（诚实边界）：所有 run 状态在**单进程内存**中，不支持多 worker —— 证据：[run_manager.py:15-17] 「设计约束（与 app.core.events.EventBus 一致）：- 单进程内存态，不支持多 worker 共享（多 worker 需外置 Redis）」
- 全局报告对此有独立印证 —— 证据：[AP_Hub/AP_Dev_Hub全景分析报告.md:253] 「但 EventBus、SDK Client、锁、AskUserQuestion 状态、Agent 客户端池和容器缓存主要位于进程内，因此当前架构依赖单 worker。」

---

## 五、SSE 事件：精确事件名全集与断点回放

- **SSE 事件类型全集 = 13 种（精确）**。统计口径：对 `backend/app` 全部 .py 做 AST 扫描，枚举所有 `SSEEvent(type=<字符串常量>)` 调用 —— 证据：AST 全量统计结果，13 种事件名及定义位置如下：

| # | 事件名 | 定义位置（文件:行） |
|---|---|---|
| 1 | `run_started` | [claude_agent_sdk_service.py:1040] |
| 2 | `token` | [claude_agent_sdk_service.py:1271] |
| 3 | `thinking` | [claude_agent_sdk_service.py:1245]、[:1280] |
| 4 | `subagent_token` | [claude_agent_sdk_service.py:1255] |
| 5 | `tool_start` | [claude_agent_sdk_service.py:1403] |
| 6 | `tool_end` | [claude_agent_sdk_service.py:1470] |
| 7 | `todo_updated` | [claude_agent_sdk_service.py:1382]、[:1701] |
| 8 | `question_pending` | [claude_agent_sdk_service.py:1418] |
| 9 | `file_tree_updated` | [claude_agent_sdk_service.py:1706] |
| 10 | `done` | [claude_agent_sdk_service.py:1630]、[:1711] |
| 11 | `agent_error` | [claude_agent_sdk_service.py:1863]、[api/conversations.py:624] |
| 12 | `artifact_generated` | [services/file_watcher.py:564] |
| 13 | `run_fatal` | [claude_agent_sdk_service.py:127] |

- 全仓 `SSEEvent(` 调用点共 17 处，全部落在上述 13 种类型内（无动态拼接类型名）—— 证据：对 `backend/app` 检索 `SSEEvent\(` 得 17 处命中，逐一归属如上表
- ⚠️ **设计文档的「10 种事件」与代码的 13 种不一致**：文档称前端认识 10 种 —— 证据：[docs/03-设计文档.md:639] 「**零新增事件类型。** 前端 `useChatStore.js` 认识 10 种事件，SDK 引擎发出的事件**全部落在其中**，不需要任何映射层：」；文档列出的 10 种见 [docs/03-设计文档.md:643-648]（`thinking`/`token`/`tool_start`/`tool_end`/`question_pending`/`file_tree_updated`/`artifact_generated`/`todo_updated`/`done`/`agent_error`）。**差值 3 种 = `run_started`、`subagent_token`、`run_fatal`**，文档未提及。—— 结论：**「13 类 SSE 事件」在代码层面成立，「10 种」是文档旧口径**。
- SSE 帧格式：`event: <type>` + `data: <JSON>`，并把 `seq` 注入 data —— 证据：[conversations.py:677-686] 「async for seq, event in run_manager.subscribe_stream(conversation_id, after_seq=after_seq): data = dict(event.data); data["seq"] = seq; yield {"event": event.type, "data": json.dumps(data, ensure_ascii=False)}」
- 心跳 15 秒 —— 证据：[conversations.py:688] 「resp = EventSourceResponse(event_generator(), ping=15)」
- **断点回放 `after_seq` 的实现位置**：HTTP 层参数定义 —— 证据：[conversations.py:658-660] 「after_seq: int = Query(default=0, ge=0, description="重连续传游标：只接收 seq 大于该值的事件")」
- 回放核心实现（先回放缓冲、再转实时、`seq` 单调去重）—— 证据：[run_manager.py:153-199] 「async def subscribe_stream(self, conversation_id: str, after_seq: int = 0) … for seq, event, _size in list(handle.replay): if seq > last_seq: … yield seq, event」「# 先注册队列再回放：回放期间新发布的事件会同时进入队列和缓冲，下方按 seq 单调去重，保证不丢不重」
- 注册时 run 已结束则补第二轮回放（防止快照与状态检查之间漏事件）—— 证据：[run_manager.py:178-186] 「if handle.status != "running": … # 再补一轮回放…」
- 订阅端点不存在活跃 run 时返回 404 —— 证据：[conversations.py:670-675] 「if handle is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, …)」
- 前端已实现按 `after_seq` 手动增量续传（不依赖 `Last-Event-ID`）—— 证据：[AP_Hub/ap_agent_ui/src/views/ap-agent/composables/sseClient.js:6] 「* 2. 手动控制重连 —— 按 after_seq 增量续传，不依赖 Last-Event-ID 头」；[:110-129] 解析帧内 `seq:` 字段并回调 `meta = { id, seq }`
- **环形缓冲上限常量（精确）**：事件数 **10,000**、字节 **8 MiB** —— 证据：[run_manager.py:35-36] 「REPLAY_MAX_EVENTS = 10_000」「REPLAY_MAX_BYTES = 8 * 1024 * 1024  # 8MB」
- 降级逻辑：超限从最旧端淘汰并置 `replay_truncated = True`；单事件即超预算时清空缓冲、全部走实时 —— 证据：[run_manager.py:90-95] 「while len(self.replay) > REPLAY_MAX_EVENTS or self.replay_bytes > REPLAY_MAX_BYTES: … self.replay_truncated = True; _, _, old_size = self.replay.popleft()」；[run_manager.py:91-92] 「if not self.replay: break  # 单个事件即超预算：缓冲清空，全部走实时」
- 前端可通过 run-status 读到降级标记 —— 证据：[conversations.py:738] 「"replay_truncated": handle.replay_truncated,」
- **慢消费者队列上限常量（精确）= 2000** —— 证据：[run_manager.py:38-40] 「# 单个订阅者队列积压上限：慢客户端（SSE 排水不及）超限时丢弃该订阅」「# （发结束哨兵），客户端走断线重连路径以回放缓冲恢复——防止无界堆积」「MAX_SUBSCRIBER_QUEUE = 2_000」
- 处置逻辑：`qsize() >= 2000` 时投 `None` 哨兵并移除该订阅（表现为连接断开 → 重连 → 回放恢复）—— 证据：[run_manager.py:96-101] 「for sub_id, queue in list(self.subscribers.items()): if queue.qsize() >= MAX_SUBSCRIBER_QUEUE: queue.put_nowait(None); self.subscribers.pop(sub_id, None) else: queue.put_nowait(entry)」
- 事件大小按 `len(event.type) + len(json.dumps(data))` 估算，序列化失败回退 `repr` —— 证据：[run_manager.py:81-86] 「try: size = len(event.type) + len(json.dumps(event.data, ensure_ascii=False, default=str)) except Exception: size = len(repr(event.data))」
- ⚠️ 另有一个**旧的、未被 RunManager 替代的** `EventBus`，其队列**无上限**，且注释自陈「队列无上限，避免慢消费者阻塞生产者」—— 证据：[AP_Hub/ap_agent/backend/app/core/events.py:9] 「- 队列无上限，避免慢消费者阻塞生产者」。它仍在使用中（FileWatcher / stderr 回调经它注入事件）—— 证据：[claude_agent_sdk_service.py:1113] 「_event_queue = await event_bus.subscribe(run.guid)」。**写简历时不要把「慢消费者上限 2000」说成覆盖全链路。**

---

## 六、工具权限：can_use_tool 回调与安全规则

- 回调实现位置：`_build_options` 内的闭包 `can_use_tool` —— 证据：[claude_agent_sdk_service.py:2051] 「async def can_use_tool(tool_name: str, tool_input: dict, _context: Any) -> Any:」
- 设计取舍：**刻意不使用 `allowed_tools` 做白名单**（因为会绕过回调直接放行），全部工具统一走回调 —— 证据：[claude_agent_sdk_service.py:2054-2055] 「不再使用 allowed_tools（会绕过回调直接放行），所有工具调用统一经过此回调处理。」
- 例外：为让主 agent 能委派子 agent，单独放行 3 个 Agent 类工具 —— 证据：[claude_agent_sdk_service.py:2155] 「allowed_tools=["Agent", "Workflow", "TaskOutput"],」；理由见 [:2150-2154]
- **允许/拒绝规则（按代码顺序）**：
  1. 命中 `_DISALLOWED_TOOLS` 黑名单 → **拒绝** —— 证据：[claude_agent_sdk_service.py:2058-2062] 「if tool_name in self._DISALLOWED_TOOLS: … return PermissionResultDeny(message=f"Tool {tool_name} is not available")」
  2. `mcp__ap_tools__todo_write` → **直接允许**（无文件系统/命令操作）—— 证据：[:2065-2066] 「if tool_name == "mcp__ap_tools__todo_write": return PermissionResultAllow()」
  3. `websearch` / `webfetch` / `askuserquestion`（**大小写不敏感**）→ **直接允许** —— 证据：[:2069-2070] 「if tool_name.lower() in ("websearch", "webfetch", "askuserquestion"): return PermissionResultAllow()」
  4. `bash` → 走命令安全校验，通过后**剥离 `dangerouslyDisableSandbox` 并改写为沙箱包装命令** —— 证据：[:2073-2093]
  5. `write` / `edit` / `read` → 路径越界校验，绝对路径**重写为 workspace 内相对路径** —— 证据：[:2096-2122]
  6. `glob` / `grep` 及其余工具 → 仅路径越界校验（因 path 字段语义不同，不重写）—— 证据：[:2124-2131] 「# Glob/Grep: 仅路径越界校验（不重写，因为 glob/grep 的 path 字段语义不同）」；兜底 [:2133] 「return PermissionResultAllow()」
- 黑名单 `_DISALLOWED_TOOLS` = 4 项：`Task` / `Skill` / `MCP` / `Monitor` —— 证据：[claude_agent_sdk_service.py:884-886] 「_DISALLOWED_TOOLS: list[str] = ["Task", "Skill", "MCP", "Monitor",]」
- **危险命令拦截清单（精确 30 条正则，分 4 类）**—— 证据：[AP_Hub/ap_agent/backend/app/tools/security.py:34-74] `_FORBIDDEN_PATTERNS: list[tuple[str, str]]`：
  - 递归强制删除 5 条（[:36-39]）`rm -rf` 变体、`rm --recursive --force` 正反序
  - 强制删除 3 条（[:40-43]）`del /f|/s|/q`、`rmdir /s|/q`、`find / … -delete`、`find / … -exec rm`
  - 写系统路径 4 条（[:45-48]）`> /etc/`、`>> /etc/`、`> C:\Windows`、`> C:\Program Files`
  - 原有规则 7 条（[:50-55]）`cd /`、`dir /s`、`Get-ChildItem -Recurse`、`gci -r`、`ls -R /`、`os.walk(`
  - 权限提升 4 条（[:57-60]）`sudo`、`su `、`chmod 777`、`chown … root`
  - 设备写入 1 条（[:62]）`dd … of=/dev/`
  - fork bomb 2 条（[:64-65]）
  - 进程级破坏 5 条（[:67-71]）`killall`、`pkill`、`kill -9 1`、`shutdown`、`reboot`
  - 磁盘格式化 1 条（[:73]）`mkfs`
- 另有一类**环境探测拦截**（`_PROBE_PATTERNS`，7 条，非安全目的，为省 Agent 轮次）—— 证据：[security.py:78-92] 「_PROBE_PATTERNS: list[tuple[str, str]] = …」；拦截原因文案见 [:130-135] 「Environment probe blocked: …」
- 命令长度上限 4000 字符 —— 证据：[security.py:94] 「_MAX_COMMAND_LENGTH = 4000」
- 校验入口（大小写不敏感正则）—— 证据：[security.py:115-116] 「for pattern, description in _FORBIDDEN_PATTERNS: if re.search(pattern, command, re.IGNORECASE):」
- 安全设计的定位声明（黑名单只拦真正危险操作，不拦 pip/python/curl）—— 证据：[security.py:32-33] 「# 注意：agent 需要 pip install、python、cd、curl 等能力执行 skill 任务，因此只拦截真正危险的操作（删除文件、写入系统路径等），不拦截开发工具。」
- ⚠️ 该黑名单被全局报告判为**纯文本黑名单，存在绕过风险** —— 证据：[AP_Hub/AP_Dev_Hub全景分析报告.md:369] 「Local Shell 主要依赖文本黑名单，应专项测试管道、重定向、命令替换、编码、PowerShell、CMD、Python/Node/Java 间接执行、符号链接、后台进程、子进程、工作区外路径和内网访问。黑名单只能作为辅助控制，不能替代容器隔离。」
- **路径校验 `realpath` 的顺序与原因（关键细节）**：必须**先** `realpath(workspace_root)` 得到 `base_real`，**再**用 `base_real` 去 `join` 相对路径，最后 `realpath` 完整路径 —— 原因写在 docstring 里：目标文件尚未创建时 `abspath` 会保留未解析前缀，与解析后的 base 前缀不匹配，合法路径会被误判越界 —— 证据：[claude_agent_sdk_service.py:2216-2242] 「注意：workspace_root 可能包含 symlink 组件（如 Docker 挂载点），必须在 os.path.join 之前先用 realpath 解析，否则当目标文件尚未创建时，abs_path 会保留未解析的前缀，与解析后的 base_real 前缀不匹配，导致合法路径被误判为越界（PermissionResultDeny）。」；判定式 [:2242] 「return real_path == base_real or real_path.startswith(base_real + os.sep)」
- 拒绝 `~` 开头路径 —— 证据：[claude_agent_sdk_service.py:2226-2227] 「if path.startswith("~"): return False」
- 绝对路径重写实现（防止穿透到宿主机根目录）—— 证据：[claude_agent_sdk_service.py:2109-2115] 「# 绝对路径重写为 workspace 内相对路径，防止穿透到宿主机根目录」「if os.path.isabs(p): resolved = os.path.realpath(p); base = os.path.realpath(workspace_root); rel = os.path.relpath(resolved, base); clean_input[key] = rel」
- 路径参数键名表（read/write/edit → `file_path`；glob/grep → `path`）—— 证据：[claude_agent_sdk_service.py:2191-2197] 与 [:2208-2212]
- 第二道防线：`SafeShellBackend` 在 write/awrite 入口独立校验路径，防止绕过上层回调直接写外部文件 —— 证据：[security.py:338-355] 「def _validate_file_path(self, file_path: str) -> None: """校验文件路径在 workspace 内，防止绕过上层回调直接写入外部文件。"""」；[:357-365] write/awrite 调用它
- `SafeShellBackend` 以**虚拟子类**方式注册（为避免 MRO 绕过 `__getattr__` 代理）—— 证据：[security.py:376-377] 「# 注册为 SandboxBackendProtocol 的虚拟子类，通过 isinstance 检查」「SandboxBackendProtocol.register(SafeShellBackend)」；理由见 [:7-11] 与 [:291-293]
- Shell 层 `cd` 越界拦截：注入 shell 函数覆写 `cd`/`Set-Location`（bash 与 PowerShell 两套实现）—— 证据：[security.py:201-242] `sandbox_wrap_command`（PowerShell 分支，[:219-240]）与 `sandbox_wrap_command_bash`（[:255-278]）；bash 版拦截文案 [:273] 「echo "cd: '$target' is outside workspace" >&2」
- Windows 多行 `python -c` 修正 —— 证据：[security.py:143-195] `_normalize_windows_python_c`
- 入口处串联「校验 → 预处理 → 沙箱包裹 → 执行」—— 证据：[security.py:313-320] `execute()`；[:329-336] `aexecute()`

---

## 七、Docker 沙箱：容器参数与真实性

- 沙箱采用**平台感知双策略**：Windows → `LocalSandboxExecutor`（仅 shell 层 cd 拦截，不建容器）；Linux → `DockerSandboxExecutor`（命令通过 `docker exec` 在隔离容器内执行）—— 证据：[AP_Hub/ap_agent/backend/app/services/sandbox_executor.py:3-5] 「- Windows → LocalSandboxExecutor：注入 Shell 路径拦截函数（sandbox_wrap_command）」「- Linux   → DockerSandboxExecutor：命令通过 docker exec 在隔离容器中执行」
- 工厂选择逻辑 —— 证据：[sandbox_executor.py:149-162] 「if _IS_WINDOWS: … return LocalSandboxExecutor(workspace_root) else: … return DockerSandboxExecutor(workspace_root, image=settings.sandbox_docker_image, runtime=settings.sandbox_docker_runtime, timeout=settings.sandbox_docker_timeout)」
- **容器创建参数（精确到行）** —— 证据：[AP_Hub/ap_agent/backend/app/services/docker_shell_backend.py:405-423]：
  - `command=["tail", "-f", "/dev/null"]`（[:407]，常驻容器）
  - `detach=True`、`remove=True`、`stdin_open=True`（[:409-411]）
  - `runtime=runtime`（[:412]）← gVisor 运行时的传入口
  - `volumes={host_workspace_root: {"bind": "/workspace", "mode": "rw"}}`（[:413]）
  - `working_dir="/workspace"`（[:414]）
  - **`cap_drop=["ALL"]`**（[:417]）—— 证据原文：「# 安全加固：丢弃所有 Linux capabilities + 禁止权限提升」「cap_drop=["ALL"],」
  - **`security_opt=["no-new-privileges"]`**（[:418]）
  - **`mem_limit="512m"`**（[:420]）
  - **`cpu_quota=100000`**（[:421]）（= 1 CPU）
  - `user = f"{os.getuid()}:{os.getgid()}"`（[:403-404]，以非 root 运行；Windows 无 getuid 则退回默认用户）
- ⚠️ **未设置的参数（无法确认/不存在）**：代码中**没有** `read_only`、**没有** `network_mode` / `network_disabled`、**没有** `pids_limit`、**没有** seccomp/AppArmor profile —— 证据：对 `AP_Hub/ap_agent` 全量检索 `read_only|readonly|network_mode|network_disabled` **仅在文档/README 出现，代码零命中**。因此「read-only 根文件系统」「网络隔离」在该实现中**不成立**。
- 因此 fork bomb 的防护实际落在 `cpu_quota` + `mem_limit` + 命令黑名单（`_FORBIDDEN_PATTERNS` 含 fork bomb 两条）上 —— 证据：[docker_shell_backend.py:419] 「# 资源限制：防止 fork bomb / 内存耗尽」；[security.py:64-65]
- **gVisor / runsc 的真实状态：是配置项，不是硬编码实现** —— 证据：
  - 配置默认值 —— [AP_Hub/ap_agent/backend/app/core/config.py:236-239] 「sandbox_docker_runtime: str = Field(default="runsc", description="Docker 容器运行时：runsc（gVisor，默认）/ runc",)」
  - 环境变量模板 —— [AP_Hub/ap_agent/.env.example:76-77] 「# 容器运行时:runsc(gVisor,默认,Linux only)/ runc(Windows/macOS 必须用 runc)」「SANDBOX_DOCKER_RUNTIME=runsc」
  - compose 透传 —— [AP_Hub/ap_agent/docker-compose.yml:67] 「- SANDBOX_DOCKER_RUNTIME=${SANDBOX_DOCKER_RUNTIME:-runsc}」
  - ⚠️ **但函数签名与工厂传参的默认值是 `runc`**，与配置默认值不一致 —— 证据：[docker_shell_backend.py:327] 「runtime: str = "runc",」；[docker_shell_backend.py:462] 「runtime: str = "runc",」；[sandbox_executor.py:96] 「runtime: str = "runc",」。实际生效值取决于 `settings.sandbox_docker_runtime`（默认 runsc）是否被环境变量覆盖，**代码本身无法证明生产上跑的是 runsc**。
  - ⚠️ **`runsc` 在本机环境不可能生效**：当前开发环境是 Windows，`create_sandbox_executor` 会走 `LocalSandboxExecutor` 分支，**根本不创建容器** —— 证据：[sandbox_executor.py:149-151]。故「gVisor 沙箱」在本次核查的代码与平台上**无法运行验证**。
- **沙箱代码是真实可运行的实现（不是占位/桩）**，理由（多重证据）：
  - 有容器复用与恢复、挂载校验、非 root 用户、symlink 兜底 —— [docker_shell_backend.py:309-456]
  - 有 bind mount 生效性验证（容器内 `ls /workspace` 与宿主 `os.listdir` 比对）—— [docker_shell_backend.py:426-450] 「# 验证挂载是否生效：在容器内 ls /workspace，与宿主机 os.listdir 对比」
  - 有独立的容器生命周期回收器（空闲超时 + LRU）—— [docker_shell_backend.py:118] `async def _reap_idle_containers()`、[:154] `def start_sandbox_reaper()`、[:93] `def _evict_if_needed()`；在应用启动/关闭时挂接 —— [main.py:82-83] 「from app.services.docker_shell_backend import start_sandbox_reaper」「start_sandbox_reaper()」、[main.py:92-95]
  - 有专用沙箱镜像（预装 pandas/numpy/matplotlib/python-docx/python-pptx/reportlab 等 18 个包）—— 证据：[AP_Hub/ap_agent/sandbox/Dockerfile:5-28] 「FROM python:3.11-slim」「RUN pip install --no-cache-dir … pandas>=2.0 … matplotlib>=3.7 … python-docx>=1.1 …」
  - 依赖真实 docker SDK（非 mock）—— [docker_shell_backend.py:513-514] 「import docker as _docker_mod」「self._docker_client = _docker_mod.from_env()」
  - 但 ⚠️ **本次核查未实际启动 Docker 容器执行命令**（只读核查 + Windows 平台），因此「实际跑通」**无法确认**。
- ⚠️ 容器空闲回收超时默认 **86400 秒（1 天）**、最大容器数 **50** —— 证据：[config.py:240-251] 「sandbox_idle_timeout: int = Field(default=86400, …)」「sandbox_max_containers: int = Field(default=50, …)」
- ⚠️ 全局安全报告指出后端直挂 Docker socket 是 P0 风险 —— 证据：[AP_Hub/AP_Dev_Hub全景分析报告.md:351-353] 「#### P0-3：Docker socket 直挂」「后端能够访问宿主 Docker 守护进程。建议移除直挂，改用受限 Sandbox Broker、独立沙箱节点或 rootless Docker，并限制网络、挂载、镜像、能力和资源。」

---

## 八、产出物（Artifact）捕获链路

- 文件监听基于 **watchdog** 递归 Observer —— 证据：[AP_Hub/ap_agent/backend/app/services/file_watcher.py:21-22] 「from watchdog.events import FileSystemEventHandler」「from watchdog.observers import Observer」；[:2-4] 「基于 watchdog 递归监听项目工作空间中所有文件的创建和修改事件，自动创建 Artifact 记录并通过 EventBus 推送 SSE 事件到前端。」
- 监听三类事件：`on_created` / `on_modified` / `on_moved` —— 证据：[file_watcher.py:51-68]。`on_moved` 专门处理 SDK Write 的**原子写**（临时文件 → 重命名），并用正则区分 SDK 临时文件与用户手动重命名 —— 证据：[:59-68] 「# SDK Write 工具使用原子写入（临时文件 → 重命名为目标文件），重命名触发 on_moved 而非 on_created，必须单独处理。」；临时文件模式 [:28] 「_TMP_FILE_PATTERN = re.compile(r"\.tmp\.\d+\.[0-9a-f]+$")」
- 排除规则：隐藏文件、`~` 开头、`.tmp`/`.swp`、`.log`，以及 4 个排除目录 —— 证据：[file_watcher.py:70-90]；排除目录常量定义在 [AP_Hub/ap_agent/backend/app/services/file_storage.py] `ARTIFACT_EXCLUDED_DIR_NAMES`，被文档引为 `{".claude", ".memory", "temp", "skills"}` —— 证据：[docs/03-设计文档.md] 「`ARTIFACT_EXCLUDED_DIR_NAMES = {".claude", ".memory", "temp", "skills"}`」
- **产出物归因（溯源）机制是本链路的亮点，分两条路径**：
  1. **白名单归因**：Agent 通过 `Write` / `Edit` / `MultiEdit` / `NotebookEdit` 写入的路径进入 `agent_written_paths` 集合，FileWatcher 只对白名单内路径建产出物 —— 证据：[claude_agent_sdk_service.py:1317-1330] 「# 收集 agent 通过工具写入的文件路径到白名单，供 FileWatcher 归因过滤」「if tool_name in ("Write", "Edit", "MultiEdit", "NotebookEdit"):」；过滤点 [file_watcher.py:482-485] 「# 白名单过滤：仅归因 agent 通过工具写入的文件，跳过用户上传 / 并发 run 的写入」「if self._agent_written_paths is not None and rel_path_norm not in self._agent_written_paths: return False」
  2. **Bash 差集归因**：因 Bash 写入不走 `file_path` 参数，改为执行前后 `mtime_ns` 快照对比，检出「新增文件 + 被覆盖文件」并补建产出物 —— 证据：[claude_agent_sdk_service.py:1080-1082] 「# Bash 工具执行前的工作空间快照（tool_use_id → {rel_path: mtime_ns}）」「_bash_snapshots: dict[str, dict[str, int]] = {}」；快照采集 [:1335-1342]；差集与补建 [:1487-1503] 「_new_files = _post_keys - _pre_keys / _modified_files = {k for k in (_pre_keys & _post_keys) if _bash_pre[k] != _bash_post[k]} / await fw.create_artifacts_for(_bash_diff)」
- 产出物落库：查重后复用/新建 `File` 记录，再建 `Artifact`（关联 `run_id` + `file_id`）—— 证据：[file_watcher.py:496-545]。含「终极去重」查询（防 consume loop 与 create_artifacts_for 竞态）—— [:497-510] 「# 终极去重：查询当前 run 是否已为此路径创建过 Artifact，防止 _consume_loop 与 create_artifacts_for / flush 竞态导致重复」
- 产出物事件载荷字段 —— 证据：[file_watcher.py:561-579] 「SSEEvent(type="artifact_generated", data={"filename":…, "path":…, "artifact_id": file_record.guid, "artifact_type": artifact_type, "run_id": self._run_id, "file_size": file_size,})」
- 产出物类型推断 —— 证据：[file_watcher.py:591-599] 「def _infer_type(filename: str) -> str: … if name.endswith((".md",".markdown")): return "markdown" … if name.endswith((".html",".htm")): return "html"」
- **磁盘文件与数据库元数据的同步实现在独立服务**：`disk_sync_service.py`，采用「读时同步 + TTL 节流 + 每项目锁」策略 —— 证据：[AP_Hub/ap_agent/backend/app/services/disk_sync_service.py:1-10] 「磁盘同步服务。… 为什么需要读时同步：Agent 运行时会直接往磁盘写文件（绕过 API）…」；[:38] 「"""同一项目两次磁盘同步的最小间隔（秒）。TTL 内的读取请求直接使用 DB 数据。"""」；[:44] 「"""per-project 同步锁，保证同一项目同一时刻只有一个同步在执行。"""」
- 同步实现：单次 walk 同时登记文件夹与文件；文件夹阶段修复 parent_id、清理幻影目录；文件阶段登记新文件、软删已消失文件 —— 证据：[disk_sync_service.py:137-138] 「"""核心同步：单次 walk 同时登记文件夹与文件，最后统一提交。"""」；[:159-167] `_sync_folders`；[:240-247] `_sync_files`；[:302] 「# 同步软删关联 Artifact，避免对话流产出物卡片点击下载 404」
- 产出物另外可通过 API 查询（对话级 / 执行级）—— 证据：[AP_Hub/ap_agent/backend/app/api/artifacts.py:22-23] 「@router.get("", response_model=list[ArtifactRead])」「async def list_artifacts(」；[AP_Hub/ap_agent/backend/app/api/conversations.py:220-221] 「@router.get("/{conversation_id}/artifacts", …)」
- ⚠️ 设计文档对产出物的定位是**「按时间归并、无版本表」**，与代码一致（`harness_artifacts` 无版本表）—— 证据：[docs/03-设计文档.md] 「产物版本表 / 版本历史表 | **不需要**：按时间归到既有 `harness_artifacts`」

---

## 九、技能系统

- 技能包**格式确认为 zip + 必须包含 `SKILL.md`** —— 证据：[AP_Hub/ap_agent/backend/app/services/myskill_service.py:379-380] 「if not md_entries: raise ValidationError("Skill zip must contain SKILL.md")」；市场侧同规则 [AP_Hub/ap_agent/backend/app/services/skill_registry_service.py:540] 「message="SKILL.md not found in the Skill package; cannot install",」
- 技能包结构（`{skill-name}/SKILL.md`，兼容直接含 `SKILL.md`）—— 证据：[myskill_service.py:149-151] 「压缩包按 ``{skill-name}/SKILL.md`` 结构解析，也兼容直接包含 ``SKILL.md`` 的压缩包。Skill 的所有文件会落到项目 ``skills/``…」
- `SKILL.md` 内容长度上限 60,000 字符 —— 证据：[myskill_service.py:420] 「raise ValidationError("SKILL.md exceeds 60000 characters")」；模型约束 [AP_Hub/ap_agent/backend/app/models/my_skill.py:50] 「Text, nullable=False, comment="SKILL.md 内容（作为 system_prompt）"」
- SKILL.md 的 `name` / `description` 从 YAML front matter 解析（正则实现，无外部依赖）—— 证据：[myskill_service.py:456] 「"""解析 SKILL.md 中的 name/description front matter。"""」；[skill_registry_service.py:597] 「"""从 SKILL.md 的 YAML front matter 提取 name / description（正则解析，无外部依赖）。"""」
- **技能包安全校验（zip 层面，逐条）** —— 证据：[myskill_service.py:288-340]：
  - `zf.testzip()` 完整性校验 —— [:290-291] 「if zf.testzip() is not None: raise ValidationError("Skill zip file is corrupted")」
  - **拒绝符号链接** —— [:306-309] 「if self._is_zip_symlink(info): raise ValidationError(f"Skill zip contains unsupported symbolic link: {normalized}")」；判定实现 [:364-368] 「mode = (info.external_attr >> 16) & 0o170000; return mode == stat.S_IFLNK」
  - **拒绝路径穿越（Zip Slip）** —— [:342-362] `_normalize_zip_entry`：「"""规范化 zip 条目并拒绝路径穿越。"""」，拒绝空/NUL 开头/绝对路径/`~` 开头/含 `.`、`..` 段/首段含 `:`（盘符）
  - **拒绝重复文件（大小写不敏感）** —— [:312-317] 「seen_key = normalized.casefold(); if seen_key in seen_paths: raise ValidationError(f"Skill zip contains duplicate file: {normalized}")」
  - **解压总大小上限**（zip 炸弹防护，累计 `file_size` 比对 `max_zip_extract_size_mb`）—— [:319-324]
  - **文件数上限** —— [:332-336] 「if len(entries) > self.settings.max_zip_file_count: raise ValidationError(…)」
  - 逐条扩展名白名单校验 + 单文件大小校验（对声明大小和实际读取字节各校验一次）—— [:326-329] 「validate_file_extension(normalized, self.settings); validate_file_size(info.file_size, self.settings); file_content = zf.read(info); validate_file_size(len(file_content), self.settings)」
  - 跳过 `__MACOSX` 元数据；拒绝 Skill 根目录之外的文件 —— [:304-305]、[:388-395] 「raise ValidationError(f"Skill zip contains file outside its root directory: {path}")」
- **双轨技能体系（确认为两套独立模型/服务/接口）**：
  1. **项目级技能** = `harness_myskills` 表 + `myskill_service.py` + `/api/skills` 接口 —— 证据：[AP_Hub/ap_agent/backend/app/models/my_skill.py:29] 「__tablename__ = "harness_myskills"」；[AP_Hub/ap_agent/backend/app/api/skills.py]（6 个端点）
  2. **注册中心（技能集市）** = `harness_skill_registry` 表 + `skill_registry_service.py` + `/api/skill-registry` 接口 —— 证据：[AP_Hub/ap_agent/backend/app/models/skill_info.py:8] 「__tablename__ = "harness_skill_registry"」；[AP_Hub/ap_agent/backend/app/api/skill_registry.py]（12 个端点）
  - 文档亦确认「两层」决策 —— 证据：[docs/事实更正与工作规则.md:81] 「| D4 | 技能集市 | **两层**：既有 `harness_skill_registry` + 项目级 `harness_myskills` |」
- **审核（review）状态机**：`pending` / `approved` / `rejected` —— 证据：[skill_info.py:67-69] 「review_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", comment="审核状态：pending / approved / rejected")」
- 另有独立的安全扫描状态字段：`pending` / `passed` / `warning` / `blocked` + 报告地址 —— 证据：[skill_info.py:61-66] 「scan_status: … comment="安全扫描状态：pending / passed / warning / blocked"」「scan_report_url: … comment="安全扫描报告地址"」
  - ⚠️ **但代码中未找到写入 `scan_status` 的实际扫描实现**（无 AV/SAST 调用）—— 该字段目前是**声明占位**。此项**无法确认**有真实扫描能力。
- 技能包校验和：`checksum_sha256`，上传时计算 —— 证据：[skill_registry_service.py:82-83] 「def _compute_sha256(self, data: bytes) -> str: return hashlib.sha256(data).hexdigest()」；[:123] 「checksum = self._compute_sha256(zip_content)」；落库 [:155] 「checksum_sha256=checksum,」
- 版本管理：`skill_name` + `version` 组合，可查全部版本 —— 证据：[skill_info.py:13-18]；[skill_registry_service.py:306] 「async def get_skill_versions(self, skill_name: str) -> list[SkillInfo]:」
- **审核/安装/启停/状态管理的接口与文件** —— 证据：[AP_Hub/ap_agent/backend/app/api/skill_registry.py] 12 个端点：
  - 创建（提审）POST `""` —— [:26]
  - 上传文档 POST `/{name}/{version}/doc` —— [:49]
  - **审核通过** POST `/{name}/{version}/approve` —— [:61]
  - **审核驳回** POST `/{name}/{version}/reject` —— [:75]
  - **安装到工作空间** POST `/{name}/{version}/install` —— [:90]
  - 浏览（仅已审核）GET `""` —— [:110]
  - 管理端列表 GET `/admin/list` —— [:133]
  - 我的发布 GET `/mine` —— [:164]
  - 按名查全部版本 GET `/{name}` —— [:193]
  - 详情 GET `/{name}/{version}` —— [:202]
  - 下载 GET `/{name}/{version}/download` —— [:214]
  - 删除 DELETE `/{name}/{version}` —— [:228]
- 审核状态迁移实现（含 reviewer 记录）—— 证据：[skill_registry_service.py:191-197] 「async def approve(…): skill.review_status = "approved" … logger.info(f"Skill approved: {skill_name} v{version}, reviewer={reviewer_id}")」；[:200-208] `reject` 同理写 `rejected` + reason
- **安装有硬门禁：未审核通过不允许安装** —— 证据：[skill_registry_service.py:408-411] 「if skill_info.review_status != "approved": raise … message=f"Skill {skill_name} v{version} is not approved and cannot be installed",」
- 安装时把 zip 物化到项目 `skills/` 目录（含 `SKILL.md`、`scripts/helper.py`、附属文件），并支持同项目原地覆盖 —— 证据：[skill_registry_service.py:394] 「3. 解压技能 zip，提取 SKILL.md（md_content）、scripts/helper.py（py_content）及附属文件」；[:445-446] 「# 同项目：原地覆盖 SKILL.md / helper.py，避免重建触发唯一约束」；[:615-631] `_update_materialized_in_place`
- 项目级技能上传接口（本地 zip 安装）—— 证据：[AP_Hub/ap_agent/backend/app/api/skills.py:62] 「@router.post(」→ `install_local_skill`
- 技能资产目录结构（含 `references/` 与 `scripts/`）在真实数据中可见 —— 证据：[AP_Hub/ap_agent/backend/data/files/workspace_289f479c…/skills/web-research-summary/SKILL.md]（2,866 字节）、同目录 `references/report_template.md`、`scripts/build_report.py`、`scripts/fetch_batch.py`
- ⚠️ **设计文档中规划的「六阶段 POC 技能包」（`poc-interview` 等 6 个）在代码中不存在** —— 证据：对 `AP_Hub/ap_agent/backend/app` 检索 `poc-interview|poc-business-process|poc-user-story|poc-prototype|poc-database|poc-lowcode` **零命中**；`data/poc_skills/` 目录不存在。即：**文档已设计、代码未实现**。

---

## 十、认证：JWT 双令牌与 AAD SSO

- **JWT 双令牌确认为 access + refresh，且 refresh 采用轮换（rotation）+ 旧 token 作废** —— 证据：[AP_Hub/ap_agent/backend/app/core/security.py:3-5] 「无状态访问令牌 + 刷新令牌（轮换）：- Access token：有效期短（settings.token_expire_minutes），登录/刷新时签发」「- Refresh token：有效期长（settings.refresh_expire_days），每次刷新时轮换签发」
- 令牌签发含唯一 `jti`，用于轮换追踪 —— 证据：[security.py:55-66] 「def _create_token(…): payload = {"sub": user_id, "iss": _TOKEN_ISSUER, "type": token_type, "jti": secrets.token_hex(16), "iat": now, "exp": now + ttl}」
- access / refresh 有效期来自配置 —— 证据：[security.py:69-90] `create_access_token`（minutes）/ `create_refresh_token`（days）
- 校验含 issuer 与必需声明 `sub/exp/type` —— 证据：[security.py:100-106] 「jwt.decode(token, settings.resolved_jwt_secret, algorithms=[settings.jwt_algorithm], issuer=_TOKEN_ISSUER, options={"require": ["sub", "exp", "type"]},)」
- 令牌类型严格区分（access 不能当 refresh 用）—— 证据：[security.py:112-113] 「if payload.get("type") != expected_type: raise TokenError(TOKEN_INVALID, "无效的登录凭证")」
- **轮换把旧 refresh token 的 jti 加入作废集合，重放即拒绝** —— 证据：[security.py:129-147] 「def rotate_refresh_token(…): … if jti and jti in _revoked_refresh_jtis: … raise TokenError(TOKEN_INVALID, "登录凭证已被刷新或作废，请重新登录") … _revoked_refresh_jtis[jti] = payload["exp"]」
- ⚠️ 作废集合是**单实例内存态，重启后清空**（代码自陈的限制）—— 证据：[security.py:33-36] 「# 已轮换作废的 refresh token jti：jti → exp（秒级时间戳，用于惰性清理）。单实例内存态，重启后清空：轮换保护的主要目标是已泄露的旧 token 在被再次使用时立即失效；跨重启持久化需要 DB/Redis 支撑，暂无必要。」
- 作废记录惰性清理防膨胀 —— 证据：[security.py:39-43] `_prune_revoked_jtis`
- token 提取支持两种通道：`Authorization: Bearer` 优先，兜底 `?access_token=`（供 SSE/img/iframe）—— 证据：[security.py:150-157] 「"""从请求中提取 token：优先 Authorization Bearer，兜底 access_token 查询参数。"""」
- **权限校验依赖（认证中间件）**：所有 `/api/*` 强制校验，白名单 3 个精确路径 + 1 个前缀 —— 证据：[AP_Hub/ap_agent/backend/app/core/auth.py:22-25] 「PUBLIC_PATHS = frozenset({"/api/auth/login", "/api/auth/aad-login", "/api/auth/refresh"})」「PUBLIC_PATH_PREFIXES = ("/api/preview/",)」
- 中间件校验并把 `user_id` 写入 `request.state` 供依赖复用 —— 证据：[auth.py:41-63] 「async def auth_middleware(request: Request, call_next): … request.state.user_id = user_id」
- ⚠️ 中间件注册顺序有明确注释（保证 401 也带 CORS 头）—— 证据：[main.py:153-156] 「# 认证中间件：/api/* 请求强制校验 JWT（白名单 /api/auth/login 除外）」「# 必须先注册（Starlette 后注册的中间件更外层），使 CORS 位于其外层，保证 401 响应也能带上 CORS 头」「app.middleware("http")(auth_middleware)」
- 当前用户依赖 —— 证据：[AP_Hub/ap_agent/backend/app/deps.py:34] 「async def get_current_user(request: Request) -> str:」
- **资源归属校验（多租户隔离）** —— 证据：[deps.py:146] 「async def assert_conversation_owned(」；被所有 conversation 端点调用，如 [conversations.py:669] 「await assert_conversation_owned(db, conversation_id, current_user)」
- **管理员校验依赖** —— 证据：[deps.py:228-234] 「async def assert_admin(…): … if user_id in settings.admin_user_ids:」；白名单配置 [AP_hub/ap_agent/backend/app/core/config.py:314] 「admin_user_ids: List[str] = Field(」
- 管理员重置密码接口 —— 证据：[AP_hub/ap_agent/backend/app/api/auth.py:257-271] 「async def reset_password(…): await assert_admin(db, current_user, settings)」
- **AAD（Azure AD）SSO 集成位置确认** —— 证据：
  - 校验实现文件：[AP_hub/ap_agent/backend/app/core/aad.py:1-11] 「AAD（Azure Active Directory）Token 校验。参考 aad.txt 的 Java 实现（nimbus-jose-jwt + HttpsJwks）：- 从 Microsoft 公钥端点拉取 JWKS 并缓存… - 校验 RS256 签名、audience… - 校验过期时间，允许 30s 时钟偏移… - 要求 sub 声明存在」
  - JWKS 客户端（PyJWT 内置，无新依赖）—— [aad.py:46-51] 「jwks_client = PyJWKClient(settings.resolved_aad_jwks_uri, cache_keys=True, headers={"User-Agent": "ap-cowork-backend"})」
  - 严格校验选项 —— [aad.py:53-67] 「algorithms=["RS256"], audience=settings.aad_client_id, options={"verify_signature": True, "verify_exp": True, "verify_nbf": True, "verify_iat": True, "verify_aud": True, "require": ["sub","exp","aud"],}, leeway=_ALLOWED_CLOCK_SKEW_SECONDS」（30 秒，[:23]）
  - 邮箱提取优先级 —— [aad.py:69-76] 「payload.get("preferred_username") or payload.get("email") or payload.get("name")」
  - 登录端点 —— [auth.py:176-216] `aad_login`：从 `Authorization: Bearer <aad_token>` 取微软 token → 校验 → 按邮箱查/建用户 → 签发本项目 JWT
  - JWKS 同步拉取放线程池避免阻塞事件循环 —— [auth.py:199-200] 「# JWKS 公钥拉取为同步 HTTP 调用，放入线程池避免阻塞事件循环」「email = await run_in_threadpool(decode_aad_token, aad_token, settings)」
  - 前端 AAD 登录页 —— [AP_Hub/ap_agent_ui/src/views/Login/AADLogin.vue]；路由 `/login` 与 `/aadLogin` 均指向它 —— 证据：[AP_Hub/ap_agent_ui/src/router/modules/remaining.ts:123-142]
- 登录接口签发双令牌并返回过期时间 —— 证据：[auth.py:130-139] 「_token_pair(user_id)」返回 `(access, refresh, expires_at, refresh_expires_at)`
- 刷新接口走轮换 —— 证据：[auth.py:224-243] 「user_id = rotate_refresh_token(payload.refresh_token, settings)」
- `GET /api/auth/me` 当前用户 —— 证据：[auth.py:246-249]
- ⚠️ 全局安全报告指出认证侧 4 项待整改（与代码自陈一致）—— 证据：[AP_Hub/AP_Dev_Hub全景分析报告.md:361-365] 「- `ADMIN_USER_IDS` 为空时可能默认允许所有登录用户调用管理操作；- AAD 自动创建账户使用统一默认密码；- JWT secret 缺失时进程内随机生成；- 通过 URL query 传递 access token 可能造成历史、日志和 Referer 泄露；」
- ⚠️ 未实现的能力（**无法确认存在**）：**没有任何 OAuth2 授权码流 / SSO 回调 / 登出（logout）端点** —— 证据：[AP_hub/ap_agent/backend/app/api/auth.py] 全部 5 个端点中无 logout/revoke/oauth。前端虽有 `src/api/login/oauth2/` 与 `SSOLogin.vue` 等文件，但那是 **yudao 母体框架遗留**，指向 Java 主后端，**不属于 Python Agent 后端**。

---

## 十一、数据模型（ORM 清单与表数量）

- SQLAlchemy 模型共 **15 个表类**（另有 `base.py` 提供 `Base` / `GUIDMixin` / `TimestampMixin`）—— 证据：逐文件 `__tablename__` 提取，清单如下表
- 完整表清单与定义位置：

| # | ORM 类 | 表名 | 定义位置 |
|---|---|---|---|
| 1 | `Workspace` | `harness_workspaces` | [models/workspace.py:25,28] |
| 2 | `Project` | `harness_projects` | [models/project.py:27,30] |
| 3 | `Folder` | `harness_folders` | [models/folder.py:35,38] |
| 4 | `File` | `harness_files` | [models/file.py:29,32] |
| 5 | `FileVersion` | `harness_file_versions` | [models/file_version.py:34,37] |
| 6 | `MySkill` | `harness_myskills` | [models/my_skill.py:26,29] |
| 7 | `SkillInfo` | `harness_skill_registry` | [models/skill_info.py:7,8] |
| 8 | `User` | `harness_users` | [models/user.py:13,16] |
| 9 | `Conversation` | `harness_conversations` | [models/conversation.py:28,31] |
| 10 | `Message` | `harness_messages` | [models/message.py:25,28] |
| 11 | `MessageBlock` | `harness_message_blocks` | [models/message_block.py:21,24] |
| 12 | `AgentRun` | `harness_agent_runs` | [models/agent_run.py:28,31] |
| 13 | `ToolCall` | `harness_tool_calls` | [models/tool_call.py:25,28] |
| 14 | `Artifact` | `harness_artifacts` | [models/artifact.py:28,31] |
| 15 | `Reference` | `harness_references` | [models/reference.py:13,20] |

- 全部模型在包 `__init__` 中导出并注册 —— 证据：[AP_hub/ap_agent/backend/app/models/__init__.py:7-22] 与 `__all__` [:24-43]
- 建表时额外导入触发 metadata 注册（含 try-except 容错）—— 证据：[AP_hub/ap_agent/backend/app/core/database.py:257-275]
- 开发环境自动建表 + 轻量幂等迁移（补列/改列类型/补唯一索引），生产走 Alembic —— 证据：[database.py:246-280] 「async def init_db() … await conn.run_sync(Base.metadata.create_all) … await _apply_dev_migrations()」；[main.py:67-70] 「# 开发环境自动建表；生产环境走 Alembic 迁移」「if settings.is_development: … await init_db()」
- 幂等补列/改列实现 —— 证据：[database.py:108-175] `_ensure_column` / `_ensure_column_type`
- ⚠️ **已确认的表名漂移事实**：设计文档与全局报告均称 **15 张表**，与代码一致 —— 证据：[docs/事实更正与工作规则.md:169] 「| `models/` | 1046 | **15 张表** |」、[docs/03-设计文档.md:231] 「│  │ 15 张表       │ …」、[docs/03-设计文档-明细.md:1101] 「含既有 13 个路由模块、20 个服务、17 个模型、15 张表、整个前端」。**17 = 15 个表文件 + `__init__.py` + `base.py`**，口径自洽。
- ⚠️ **但 `04.数据库设计.yaml` 与 ORM 严重不一致（重要发现）**：
  - 该 YAML 声明 **`TableCount: 13`**，且 13 张表全部以 `harness_` 为前缀 —— 证据：[04.数据库设计.yaml:1-3] 「RootName: DataModels」「CTVER: '43543432'」「TableCount: 13」
  - YAML 中的 `harness_teams`（团队）、`harness_team_members`（团队成员）、`harness_containers`（容器）、`harness_socket_sessions`（Socket会话）**在 ORM 中完全不存在** —— 证据：对 `AP_hub/ap_agent/backend/app` 检索 `harness_teams|harness_containers|harness_socket_sessions|Team` **零命中**
  - 反之 ORM 中的 `harness_users`、`harness_folders`、`harness_artifacts`、`harness_references`、`harness_skill_registry` **不在该 YAML 的 13 张表内**
  - ⇒ 该 YAML 是**过期的/另一来源的数据模型快照**，不能作为当前后端数据模型的证据引用。
- 前端存在团队管理 UI 但后端无对应实现（cross-check 上述结论）—— 证据：[AP_hub/ap_agent_ui/src/views/ap-agent/components/team/TeamManagement.vue]、[TeamMemberPanel.vue]、[stores/useTeamStore.js] 均存在，而 Python 后端无 team 相关模型/接口
- 数据库引擎配置（MySQL + 连接池 + 驱动层超时探测 + 可选 TLS）—— 证据：[database.py:29-59] 「_engine_kwargs: dict = {"echo": False, "pool_pre_ping": True, "pool_size": …}」「_connect_args: dict = {"connect_timeout": 10}」「if _settings.mysql_ssl: …」
- 事务契约（请求边界统一提交）—— 证据：[database.py:83-105] 「事务契约（请求边界统一提交）：- JSON 路由：Service/路由层不调用 commit()…」「yield session; await session.commit()」

---

## 十二、六阶段 AI 研发流水线（`ap-poc-agent` 原型）

- **六个阶段的确切名称与顺序** —— 证据：[ap-poc-agent/js/store.js:12-19] 「const STEPS = [」：

| 序 | key | 名称 | 页面 | 说明 |
|---|---|---|---|---|
| 1 | `interview` | AI访谈助手 | `ai-interview.html` | 需求调研访谈，提取业务对象与规则 |
| 2 | `bpm` | 业务流程分析 | `bpm-analysis.html` | 基于访谈结果梳理业务流程地图 |
| 3 | `story` | 业务需求分析 | `req-analysis.html` | 将流程拆解为业务需求与活动 |
| 4 | `ui` | 原型设计助手 | `ui-design.html` | 基于业务需求生成 UI 原型 |
| 5 | `db` | 数据库设计 | `db-design.html` | 根据原型与需求设计数据模型 |
| 6 | `lowcode` | AI低代码POC | `lowcode.html` | 生成低代码应用与数据库表 |

  原文摘录（store.js:12-19）：`{ key: 'interview', name: 'AI访谈助手', url: 'ai-interview.html', icon: 'fa-comments', desc: '需求调研访谈，提取业务对象与规则' },` … `{ key: 'lowcode', name: 'AI低代码POC', url: 'lowcode.html', icon: 'fa-cubes', desc: '生成低代码应用与数据库表' }`
  注释确认「顺序即引导顺序」—— [store.js:11] 「// 6 个 POC 步骤的定义（顺序即引导顺序）」
- **阶段间产出物串联契约的实现位置（三函数齐全）**：
  - `getPrevOutput` —— 证据：[store.js:177-184] 「/** 获取上一步产出物 —— Agent 协同的关键：作为当前步的输入上下文 */」「function getPrevOutput(projectId, step) { … const idx = STEPS.findIndex(s => s.key === step); if (idx <= 0) return null; const prev = STEPS[idx - 1]; return getStepOutput(projectId, prev.key); }」
  - `saveStepOutput` —— 证据：[store.js:166-175] 「function saveStepOutput(projectId, step, output) { … write(outputKey(projectId, step), {step, content: output, updatedAt: Date.now()}); // 有产出即标记完成 / updateStepStatus(projectId, step, STATUS.COMPLETED); }」
  - `getAllPrevOutputs` —— 证据：[store.js:186-197] 「/** 获取此前所有已完成步骤的产出（完整链路上下文） */」「function getAllPrevOutputs(projectId, step) { … for (let i = 0; i < idx; i++) { const out = getStepOutput(projectId, STEPS[i].key); if (out) result.push({ step: STEPS[i].key, name: STEPS[i].name, ...out }); } return result; }」
  - 三函数均在模块末尾导出 —— 证据：[store.js:305-306] 「getPrevOutput,」「getAllPrevOutputs,」
- 阶段状态机 3 态 —— 证据：[store.js:21] 「const STATUS = { NOT_STARTED: 'not_started', IN_PROGRESS: 'in_progress', COMPLETED: 'completed' };」
- 进度统计 —— 证据：[store.js:286-290] `getProjectProgress` 按 COMPLETED 计数算百分比
- **增量修改三函数（实现位置 + 作用范围）**：
  - `detectIntent` —— 证据：[ap-poc-agent/js/chat.js:54-60] 「// 识别修改意图：add / remove / rename / update / null」「function detectIntent(text) { if (REMOVE_RE.test(text)) return 'remove'; if (ADD_VERBS.some(v => text.includes(v))) return 'add'; if (RENAME_VERBS.some(v => text.includes(v))) return 'rename'; if (UPDATE_RE.test(text)) return 'update'; return null; }」
    ⇒ **意图分类共 4 类 + null 兜底：`add` / `remove` / `rename` / `update`**，纯正则/关键词匹配
    - 关键词资产：`ADD_VERBS` 12 个、`REMOVE_RE`、`RENAME_VERBS` 8 个、`UPDATE_RE`、`GENERIC_WORDS` —— 证据：[chat.js:47-51]
  - `locateItem` —— 证据：[chat.js:92-101] 「// 在列表中定位目标项：序号 → 名称包含 → 引用词「」→ 上一次修改的目标 → 首项」「function locateItem(list, text, nameGetter, lastTarget) { const idx = parseIndex(text, list.length); if (idx != null) return idx; for (let i = 0; i < list.length; i++) { const n = nameGetter(list[i]); if (n && n !== '待补充' && text.includes(n)) return i; } if (lastTarget != null && lastTarget >= 0 && lastTarget < list.length) return lastTarget; return 0; }」
    - 序号解析（支持中文数字与「最后一个」）—— [chat.js:63-72] `parseIndex`，中文数字表 [chat.js:46] `CN_NUMS`
  - `tryPatch` —— 证据：[chat.js:270-283] 「/* 尝试对现有产物做局部修改；成功返回 { artifact, reply, target }，否则 null */」「function tryPatch(step, baseArtifact, text, intent, lastTarget, historyLen) { const handler = Patcher[step]; if (!handler || !baseArtifact) return null; const draft = clone(baseArtifact); const result = handler(draft, text, intent, lastTarget); if (!result) return null; … }」
    - 作用范围 = `Patcher` 对象里按 step 注册的 6 个局部修改器（`bpm` / `story` / `ui` / `db` / `lowcode` / `interview`）—— 证据：[chat.js:106-268] `const Patcher = { bpm(a,text,intent,lastTarget){…}, story(…){…}, … }`
    - 调用点（先试局部 patch，失败才走全量生成）—— 证据：[chat.js:476-483] 「const intent = detectIntent(text); … ? tryPatch(props.step, artifact.value, text, intent, lastTarget, userTurns)」
- **真实产出物文件与阶段对应** —— 证据：[AP_hub/ap-poc-agent/assets] 目录 + 前端页面引用：
  - `访谈总结.png`（56,504 B）→ 阶段 ① AI访谈助手
  - `访谈提纲.pdf`（327,348 B）→ 阶段 ①
  - `业务流程地图.png`（3,686,325 B）→ 阶段 ② 业务流程分析
  - `用户故事地图.png`（3,081,802 B）→ 阶段 ③ 业务需求分析
  - `数据库设计图.png`（113,004 B）→ 阶段 ⑤ 数据库设计
  - `DSL文件.dmj`（27,539 B）→ 阶段 ⑤ 数据库设计（可导入设计器的数据模型文件）
  - `codegen.zip`（92,956 B）→ 阶段 ⑥ AI低代码POC
  - `portal-bg.png`（852,017 B）→ 门户装饰背景，**不属于任何阶段产出物**
- **`DSL文件.dmj` 的表数量与内容（精确）**：是一个 JSON 格式的「勤栈数据模型设计器」导出文件，`TableCount: 6`，模型名 `RBAC数据模型`，引擎 `MYSQL` —— 证据：[ap-poc-agent/assets/DSL文件.dmj:2-4] 「"RootName": "DataModels", "CTVER": "43543338", "TableCount": 6,」；[:9,13] 「"Name": "RBAC数据模型"」「"DefDbEngine": "MYSQL"」
  - 6 张表（含 1 张非数据表）：`使用说明`（TEXT 类型说明文档，0 字段）、`system_menu`（菜单权限表，25 字段）、`system_role`（角色信息表，15）、`system_role_menu`（角色和菜单关联表，9）、`system_user_role`（用户和角色关联表，9）、`system_users`（用户信息表，24）
  - ⇒ 扣除 `使用说明` 后，**真实业务表 5 张**，是标准 RBAC 五表模型。
  - 表内可见 DSL 枚举：`DataType` 1/2、`KeyFieldType` 1（主键）/3（外键，带 `RelateTable`+`RelateField`）—— 证据：[DSL文件.dmj:45-48] 「"DataType": 2, "KeyFieldType": 1, "DefaultValue": "{auto_increment}", "Not_Nullable": true」
- **`codegen.zip` 里实际生成的技术栈与文件结构（已解压查看，未执行任何脚本）**：
  - 顶层 3 个目录：`dorbit-module-system/`、`dorbit-ui-admin-vue2/`、`sql/` —— 证据：解压清单
  - 文件总数 **78**；扩展名分布：`.java` 46 · `.vue` 10 · `.xml` 9 · `.js` 5 · `.sql` 5 · `.yaml` 3
  - **技术栈 = Java Spring Boot（Maven 多模块）+ MyBatis-Plus（XML mapper）+ Vue 2 后台 + MySQL DDL**
    - Spring Boot 应用入口 —— 解压路径 `dorbit-module-system/dorbit-module-system-biz/src/main/java/com/deloitte/dorbit/module/system/SystemServerApplication.java`
    - 配置 `application.yaml` 实测：`server.port: 48089`、`spring.application.name: dorbit-system-server`、Nacos 注册/配置中心、Druid 数据源、Redis 缓存 —— 证据：`application.yaml` 内容
    - 分层结构完整：`controller/admin/{menu,role,rolemenu,userrole,users}` + `vo/` · `dal/dataobject/` + `dal/mysql/` + `resources/mapper/*.xml` · `service/` + `ServiceImpl` · `enums/*ErrorCodeConstants`
    - Vue 2 前端：`dorbit-ui-admin-vue2/src/api/system/{menu,role,rolemenu,userrole,users}/index.js` + `src/views/system/*/{index.vue,*Form.vue}`
    - SQL：`sql/{Menu,Role,RoleMenu,UserRole,Users}-sql.sql` 共 5 个建表脚本
  - ⇒ 生成的**正是 `DSL文件.dmj` 那 5 张 RBAC 业务表**的标准 CRUD 代码骨架（非完整可运行应用）。
  - ⚠️ 该 zip 由外部代码生成器产生，**`ap-poc-agent` 仓库内没有任何生成它的代码**（该原型只做展示）——证据：[ap-poc-agent/js] 仅 3 个 js 文件，无生成逻辑
- **页面数量（精确）**：`ap-poc-agent` 根目录共 **10 个 .html** —— 证据：目录列表。区分如下：
  - **主流程页面 6 个**（与 `STEPS` 一一对应）：`ai-interview.html`(229 行) · `bpm-analysis.html`(228) · `req-analysis.html`(320) · `ui-design.html`(385) · `db-design.html`(260) · `lowcode.html`(347)
  - **其它页面 4 个**：`index.html`(270 行，门户「勤栈AI+ 门户」) · `projects.html`(164 行，「我的项目」列表) · `project.html`(510 行，「项目工作台」) · `AI-chat.html`(5,860 行，「AI Chat - Deloitte AI 协同软件开发」)
  - ⇒ 主流程 6 + 其它 4 = 10。若简历写「10 个交互页面」**成立**，但需注意其中 6 个才是六阶段主流程。
  - 另有 `.trae-html-share-packages/` 下 13 个 html 分享包 zip（每个约 6.6 MB），是打包产物，**不应计入页面数** —— 证据：[ap-poc-agent/.trae-html-share-packages] 目录
- **行业模板数量与名称（`templates.js`，精确 3 套）** —— 证据：[ap-poc-agent/js/templates.js:2-3] 「AP POC Agent - 行业模板」「每个模板预填 6 步产出物，创建项目时由 PocStore 注入」：
  1. `crm` — **CRM 客户关系管理** —— 证据：[templates.js:13-14] 「id: 'crm',」「name: 'CRM 客户关系管理',」
  2. `expense` — **费控共享运营** —— 证据：[templates.js:82-83] 「id: 'expense',」「name: '费控共享运营',」
  3. `asset` — **固定资产管理** —— 证据：[templates.js:151-152] 「id: 'asset',」「name: '固定资产管理',」
  - 每个模板预填 6 个阶段的产出物（`outputs` 按 step key 组织），含 L1/L2 流程、阶段/活动/故事、KPI 与菜单、ER 表与字段、列表行数据
  - ⇒ 简历若写「3 套行业模板」**成立**，且名称可如上引用。
- **纯前端原型 vs 真实后端的界线（证明行号）**：
  - ✅ **数据全部存 localStorage** —— 证据：[store.js:2] 「AP POC Agent - Store (localStorage)」；[:24-40] 「function read(key, fallback) { … localStorage.getItem(key) … }」「function write(key, value) { … localStorage.setItem(key, JSON.stringify(value)) … }」
  - ✅ **LLM 是本地 mock，无任何网络调用** —— 证据：[chat.js:295-296] 「/* ---------- 模拟产物生成器：输出结构化 payload ---------- */」「const MockAI = {」；mock 生成器共 6 个方法（`bpm`/`story`/`ui`/`db`/`lowcode`/`interview`）[chat.js:298-377]
  - ✅ **回复文本是关键词路由的模板字符串，不是模型输出** —— 证据：[chat.js:379-389] 「/* ---------- 关键词路由，生成回复文本 ---------- */」「function buildReply(step, text, prevOutputs) { … const map = { interview: '已记录本次访谈内容。…', bpm: `…`, … }」
  - ✅ **全仓零 `fetch` / `XMLHttpRequest` / `axios`** —— 证据：对 `ap-poc-agent` 检索 `fetch\(|XMLHttpRequest|axios` **零命中**；命中的 `https://` 只有 CDN（Tailwind、Vue 3.4.21 global build、Font Awesome）与 favicon —— 证据：各 html 第 7-10 行
  - ✅ 因此 `ap-poc-agent` 是**纯前端原型**：数据在浏览器 localStorage，LLM 为本地 mock，**无真实后端**。
  - ✅ 对照：真实后端在 `AP_Hub/ap_agent`（FastAPI + 真实 Claude Agent SDK + MySQL + SSE）—— 证据：本报告第二、三、四节全部条目
- ⚠️ `AI-chat.html` 是 5,860 行的单文件页面（引用 `js/store.js` + `js/templates.js`），与 6 个主流程页面**不是同一套交互**，疑为另一版原型 —— 证据：[AI-chat.html] 脚本引用列表；**其定位本次未深入核查，无法确认**。

---

## 十三、设计文档中的领域模型规模与「0 新增数据表」

- 领域模型规模为 **5 套本体、合计 61 个实体 / 380 个属性** —— 证据：[docs/03-设计文档.md:659] 「| 3.2 | 五套本体（**含提问顺序**） | `[APP]data\poc_skills\poc-interview\references\ontology-*.yaml` | `【移植】` | `[INTERVIEW]data\owl\*.ttl`（5 份，2,779 行，**61 实体 / 380 属性**） |」
- 同样的数字在多处出现，口径一致 —— 证据：
  - [docs/03-设计文档-明细.md:854] 「这套知识以**本体**形式存在，共五套，合计 **61 个实体、380 个属性**：」
  - [docs/03-设计文档-明细.md:108] 「│  本体（61 实体/380 属性） │」
  - [docs/03-设计文档.md:238] 「│   [INTERVIEW]  访谈方法论 · 本体数据（61 实体 / 380 属性）                 │」
  - [docs/事实更正与工作规则.md:32] 「本体（5 份 TTL，**61 实体 / 380 属性**）**转 JSON 存库**」
- **五套本体的逐份规模（明细）** —— 证据：[docs/03-设计文档.md:489-494] 与 [docs/03-设计文档-明细.md:685-690]：
  | 本体 | 实体 | 属性 | 用途 |
  |---|---|---|---|
  | `ontology-general.yaml` | 15 | 87 | 通用需求访谈（**当前在用**） |
  | `ontology-agent_database_design.yaml` | 16 | 103 | 数据库设计专用 |
  | `ontology-finance_shared.yaml` | 11 | 67 | 财务共享行业 |
  | `ontology-procurement.yaml` | 9 | 58 | 采购行业 |
  | `ontology-ma_implementation.yaml` | 10 | 65 | 并购实施行业 |
  | **合计** | **61** | **380** | |
  - 校验：15+16+11+9+10 = **61** ✅；87+103+67+58+65 = **380** ✅（数字自洽）
- 「0 新增数据表」的确切出处与原文 —— 证据：[docs/03-设计文档.md] 「### 数据结论」表：「| 新增表 | **0 张** |」「| 新增列 | **0 处** |」「| 改动既有表 | **无** |」
- 同段还列出**被取消的旧设计表** —— 证据：[docs/03-设计文档.md] 「| 产物版本表 / 版本历史表 | **不需要**：按时间归到既有 `harness_artifacts` |」「| 本体框架 / 类别 / 实体 / 属性表（4 张） | **不需要**：本体是技能包文件资产 |」「| 实体实例表 | **不需要**：实例是产物 YAML |」
- 「不入库」的理由（本体画布本来就读 YAML 文件）—— 证据：[docs/03-设计文档.md:681-682] 「| 本体定义（61 实体 / 380 属性） | 技能包 `references/ontology-*.yaml` | 静态定义；模型按需 `Read`，不进提示词 |」「| 实体实例 | 产物 `results/01-访谈/实体实例.yaml` | **本体画布本来就是读 YAML 文件渲染**，不是读接口 |」
- ⚠️ **但上述全部是设计文档内容，代码中不存在对应实现** —— 证据：对 `AP_hub/ap_agent/backend/app` 检索 `poc-interview|ontology-|poc_skills|instance-spec` **零命中**；无 `data/poc_skills/` 目录。⇒ **「61 实体 / 380 属性」「0 新增数据表」是设计规划，不是已交付代码的成果。**
- 设计文档同时声明「未做任何代码改动」—— 证据：[docs/事实更正与工作规则.md:263] 「**未做任何代码改动。**」；[:264-265] 「- `AP_Hub\ap_agent` — HEAD `c676f4c`，工作区**干净**」「- `AP_Hub\ap_agent_ui` — HEAD `fe69a37`，仅有 `pnpm_rebuild.log` / `vite_dev.log` 两个**未跟踪**文件」
- ⚠️ **该文件自陈文档**行数与代码实测不符**（见下一节的冲突清单）：
  - 文档称 `api/` **13 模块 64 端点** —— [docs/事实更正与工作规则.md:170]；实测 **12 个路由模块 / 71 个端点**（另有 1 个 `health` 在 12 个内；`api/` 目录 13 个文件含 `__init__.py`）
  - 文档称 `run_manager.py` 224 行 —— [docs/事实更正与工作规则.md:162]；实测 **263 行**
  - 文档称 `claude_agent_sdk_service.py` 2,429 行 —— [docs/事实更正与工作规则.md:168]；实测 **2,685 行**
  - 文档称 `models/` 1,046 行 —— [docs/事实更正与工作规则.md:169]；实测 **1,327 行**
  - 文档称 `file_watcher.py` 535 行 —— [docs/事实更正与工作规则.md:165]；实测 **602 行**
  - 文档称 `core/database.py` 243 行 —— [docs/事实更正与工作规则.md:161]；实测 **280 行**
  - 文档称 `main.py` 227 行、L197-210 挂 12 个路由 —— [docs/事实更正与工作规则.md:171]；实测 **269 行**，L197-210 挂 **12 个** router（11 个业务 + health，✅ 此项一致）
  ⇒ **说明该「事实更正」文档本身也基于较早的代码快照**，引用其行数时需以本核查实测为准。
- 全局报告对本仓库的定位判断（可作简历的「诚实边界」参考）—— 证据：[AP_Hub/AP_Dev_Hub全景分析报告.md:66] 「| `api/ap_agent` | Python Agent 后端 | Python | FastAPI、SQLAlchemy Async、MySQL、PyJWT、Claude Agent SDK、Docker/gVisor | `main.py`、`config.py` | Agent 执行、SSE、工具调用、文件、Skill、产出物、引用、沙箱 | 核心服务 |」；[:451] 「本报告基于静态代码、配置、仓库和文档分析；此前未执行依赖安装、前端构建、Maven 构建、Python 运行、自动化测试或运行时攻击验证。」

---

## 十四、无法确认 / 与简历现有说法冲突的地方

> 逐条核实简历里可能出现的宣称。判定：**成立 / 不成立 / 需修正为 X / 无法确认**。

### 14.1 「支撑 71 个 REST 接口」

- **结论：成立。** 71 是可复现的精确数字 —— 证据：AST 统计 `backend/app` 全部 `@router.<method>` 装饰器 = 71（GET 36 / POST 22 / PUT 6 / DELETE 7）
- **但必须补口径说明**，否则面试官若用正则数会得到 72 而与你对不上：
  - 正则 `@router\.` 命中 **72** 行，多出的一行是 [core/database.py:93] 的 docstring 用法示例，非真实路由。
  - 若把 `main.py` 里未 include 的 router 也算进去会再次出错；本项目的 71 恰好等于「12 模块全部 include」的结果。
- ⚠️ **与本机文档冲突**：`事实更正与工作规则.md:170` 写的是「13 模块 64 端点」。**以 71 为准**（文档基于旧快照）。
- 建议表述：「71 个 REST 端点（FastAPI，12 个路由模块，AST 精确统计；GET/POST/PUT/DELETE = 36/22/6/7）」

### 14.2 「13 类 SSE 事件」

- **结论：成立。** 13 种事件名可从代码逐行数出 —— 证据：`run_started` · `token` · `thinking` · `subagent_token` · `tool_start` · `tool_end` · `todo_updated` · `question_pending` · `file_tree_updated` · `done` · `agent_error` · `artifact_generated` · `run_fatal`（各定义行号见第五节表）
- ⚠️ **与本机设计文档冲突**：`03-设计文档.md:639-648` 写的是「前端认识 **10 种**事件」。差值 3 种 = `run_started` / `subagent_token` / `run_fatal`。
- 建议表述：「13 类 SSE 事件类型（含 `run_started`、`subagent_token`、`run_fatal`）」。若沿用文档的「10 种」会与代码不符。

### 14.3 「交付 10 个交互页面」

- **结论：数字成立，但需限定。** `ap-poc-agent` 根目录确有 **10 个 .html** —— 证据：目录列表
- **必须区分的口径**：其中 **只有 6 个是六阶段主流程页面**（`ai-interview` / `bpm-analysis` / `req-analysis` / `ui-design` / `db-design` / `lowcode`），另 4 个是门户与项目管理层（`index` / `projects` / `project` / `AI-chat`）。
- ⚠️ `AI-chat.html` 单文件 5,860 行，与主流程不是同一套交互，**定位无法确认**；`.trae-html-share-packages/` 下 13 个 zip 是打包产物，**不应计入页面数**。
- 建议表述：「6 个六阶段主流程页面 + 4 个门户/项目管理页面（共 10 个 HTML 页面）」——更准确且防追问。

### 14.4 「3 套行业模板」

- **结论：成立。** 精确 3 套，名称可引用 —— 证据：[templates.js:13-14] `crm` / CRM 客户关系管理；[:82-83] `expense` / 费控共享运营；[:151-152] `asset` / 固定资产管理
- 建议表述：「3 套行业模板（CRM 客户关系管理、费控共享运营、固定资产管理），每套预填 6 个阶段产出物」

### 14.5 「RunManager 并发冲突返回 409」

- **结论：不成立（这是本次核查最重要的发现）。** 互斥逻辑存在，但 **HTTP 状态码实际是 500，不是 409**。
- 三重证据链：
  1. `RunActiveError` 直接继承 `Exception`，**不是** `AppException`/`HTTPException` —— [run_manager.py:46]
  2. 转 409 的 `except RunActiveError` 包住的是 `_agent_chat_sse(...)` 调用 —— [conversations.py:552-566]
  3. 但抛异常的 `run_manager.start()` 在 `_agent_chat_sse` 内部、且在该函数自身 `try` 之外 —— [conversations.py:587]（下方 589 行才进 `producer` 的 `try`）
  ⇒ 异常冒泡到 `@app.exception_handler(Exception)` → **500** —— [core/exceptions.py:122-142]
- 代码注释仍写 409 —— [conversations.py:549]「对话已有活跃 run 时返回 409」，**注释与实现不符**。
- 唯一的可达 409 是 direct chat 与 agent 之间那条对称互斥 —— [conversations.py:582-586]、[:349-358]。
- **建议表述**：「用 RunManager 做对话级互斥，同一对话并发提交时抛 `RunActiveError` 拒绝重复执行（注：当前该异常的 HTTP 映射存在缺陷，会落到全局 500 处理器，而非注释所述的 409）」。**不要写「返回 409」**；若写了，被追问代码就会露馅。

### 14.6 「Docker 沙箱有 cap_drop / no-new-privileges / 内存限制 / read-only / 网络隔离 / gVisor」

- **cap_drop=["ALL"]：成立** —— [docker_shell_backend.py:417]
- **no-new-privileges：成立** —— [docker_shell_backend.py:418] `security_opt=["no-new-privileges"]`
- **内存限制：成立** —— [docker_shell_backend.py:420] `mem_limit="512m"`（另有 `cpu_quota=100000`，[:421]）
- **read-only：不成立。** 代码中**没有** `read_only` 参数 —— 全仓 `read_only|readonly` 在 `AP_hub/ap_agent` 代码中**零命中**。**不要写 read-only 根文件系统。**
- **网络隔离：不成立。** 代码中**没有** `network_mode` / `network_disabled` —— 同样零命中。容器使用默认 bridge 网络，**可访问网络**。当前只有命令黑名单里的 `>\s*/etc/` 等间接约束，**没有网络层隔离**。
- **gVisor/runsc：需修正为「可配置项」。** 配置默认值是 `runsc` —— [config.py:236-239]，`.env.example` 与 compose 亦如此 —— [.env.example:76-77]、[docker-compose.yml:67]。但：
  - 函数签名与工厂的默认值是 `runc` —— [docker_shell_backend.py:327]、[:462]、[sandbox_executor.py:96]
  - **实际生效值取决于环境变量**，代码无法证明生产上跑 runsc
  - **当前 Windows 环境根本不建容器** —— [sandbox_executor.py:149-151] 走 `LocalSandboxExecutor`
  - ⇒ 「基于 gVisor 的沙箱」**无法确认已实际启用/跑通**
- **「有实际可运行的沙箱代码」：成立**（非占位）。证据：容器生命周期/回收器/LRU/挂载校验/专用沙箱镜像/真实 docker SDK —— 见第七节
  - ⚠️ 但**本次核查未实际启动容器执行命令**，「实际跑通」**无法确认**。
- 建议表述：「实现 Docker 容器沙箱（`cap_drop=ALL`、`no-new-privileges`、内存 512m、CPU 配额、非 root 用户、bind mount 至 `/workspace`），运行时可通过 `SANDBOX_DOCKER_RUNTIME` 配置为 gVisor `runsc`」，**不要写 read-only / 网络隔离 / 已在生产跑 gVisor。**

### 14.7 「危险命令拦截」

- **结论：成立，但需标注性质。** 30 条正则黑名单 + 7 条探测拦截 —— [security.py:34-92]
- ⚠️ **这是文本黑名单，不是强隔离**，全局安全报告明确判为存在绕过风险 —— [AP_hub/AP_Dev_Hub全景分析报告.md:369]
- 建议表述：「实现 30 条危险命令正则拦截（递归删除 / 系统路径写入 / 提权 / fork bomb / 关机重启用 / 磁盘格式化）与工作空间 cd 越界拦截」，**不要暗示它等价于安全沙箱**。

### 14.8 「技能包安全校验 / 技能审核」

- **zip 层安全校验：成立且相当完整** —— 拒绝 symlink [myskill_service.py:306-309]、拒绝路径穿越（Zip Slip）[:342-362]、拒绝重复文件 [:312-317]、解压总量上限 [:319-324]、文件数上限 [:332-336]、扩展名与单文件大小 [:326-329]
- **审核状态机：成立** —— `pending`/`approved`/`rejected` [skill_info.py:67-69]；approve/reject 端点为 [skill_registry.py:61,75]；**未审核禁止安装** [skill_registry_service.py:408-411]
- **双轨体系：成立** —— 项目级 `harness_myskills` + 注册中心 `harness_skill_registry`（见第九节）
- ⚠️ **「安全扫描」不成立**：`scan_status`（pending/passed/warning/blocked）与 `scan_report_url` 字段**只是声明占位**，代码中**没有**任何实际扫描实现（无 AV/SAST 调用）—— [skill_info.py:61-66]。**不要写「技能包安全扫描」。**
- 建议表述：「技能包 zip 安全校验（Zip Slip / 符号链接 / 重复项 / 解压炸弹 / 文件数上限）+ SH-256 校验和 + 审核状态机（pending/approved/rejected，未审核禁止安装）」

### 14.9 「JWT 双令牌 + AAD SSO」

- **成立。** access + refresh，refresh 轮换且旧 jti 作废 —— [security.py:3-5]、[:129-147]；AAD 走 PyJWT `PyJWKClient` 校验 RS256/aud/exp/nbf/iat + 30s 时钟偏移 —— [aad.py:1-11]、[:46-67]；登录端点 [auth.py:176-216]
- ⚠️ **两个必须知道的限制**：
  1. refresh 作废集合是**单进程内存态，重启即清空**（代码自陈）—— [security.py:33-36]
  2. **没有 logout / token revoke 端点** —— [api/auth.py] 5 个端点中无 logout
  3. 全局安全报告另指出：JWT secret 缺失时进程内随机生成、`ADMIN_USER_IDS` 为空时可能放开管理操作、AAD 自动建号用统一默认密码、URL query 传 token 有泄露面 —— [AP_Dev_Hub全景分析报告.md:361-365]
- 建议表述：「JWT 双令牌（access + refresh 轮换与旧 token 作废）+ Microsoft AAD SSO（JWKS/RS256/audience 校验）」，**不要提 logout/黑名单持久化**。

### 14.10 「15 张数据表 / 17 个模型」

- **结论：成立。** ORM 实测 **15 个表类**，`models/` 目录 **17 个文件**（15 表 + `__init__.py` + `base.py`）—— 证据：第十一节表
- ⚠️ **不要引用 `04.数据库设计.yaml` 的 `TableCount: 13`**：该文件描述的 13 张表与 ORM 严重不一致（YAML 有 `harness_teams` / `harness_team_members` / `harness_containers` / `harness_socket_sessions` 而 ORM 全无；ORM 的 `harness_users` / `harness_folders` / `harness_artifacts` / `harness_references` / `harness_skill_registry` 不在 YAML 内）。它是**过期快照**。
- ⚠️ **后端无团队（team）实现**：前端有 `TeamManagement.vue` / `useTeamStore.js`，但 Python 后端 `harness_teams|Team` **零命中**。**不要写「团队协作后端」。**

### 14.11 「六阶段 POC 流水线已实现 / 61 实体 380 属性已落地 / 0 新增数据表」——最高风险项

- **结论：作为「已交付代码」不成立；作为「设计方案」成立。** 这是简历中最容易被戳穿的一类宣称。
- 证据链：
  1. 设计文档**自陈「未做任何代码改动」** —— [docs/事实更正与工作规则.md:263]
  2. 六阶段技能包（`poc-interview` 等）在 Python 后端**零命中**，`data/poc_skills/` 目录**不存在**
  3. 「61 实体 / 380 属性」只出现在 [docs/03-设计文档.md:659]、[docs/03-设计文档-明细.md:854]、[docs/事实更正与工作规则.md:32]，**无任何代码或本体 YAML 文件**
  4. 「0 新增数据表」是 [docs/03-设计文档.md] 的**设计结论**，且 ORM 确实未新增表（因为整个六阶段功能都没实现）
- ⇒ **建议表述（必须做这个切分）**：
  - 可写：「参与六阶段 AI 研发流水线（访谈→业务流程→业务需求→原型→数据库→低代码）的**方案设计与技术选型**，产出设计文档，明确复用既有 Claude Agent SDK / RunManager / FileWatcher 机制、本体与实体实例改由技能包文件与产物 YAML 承载（**0 新增数据表**）、前端零改动」
  - 可写：「实现**交互原型**（`ap-poc-agent`，纯前端，Vue 3 CDN + Tailwind，数据存 localStorage，LLM 为本地 mock，含 6 阶段串联契约与增量修改意图识别）」
  - **不可写**：「已实现六阶段流水线」「已落地 61 实体 380 属性本体」「六阶段技能包已上线」——这些在代码中不存在。

### 14.12 「Claude Agent SDK 子 Agent / 多租户隔离」

- **子 Agent：成立但默认关闭。** `AgentDefinition` 构建逻辑存在 —— [claude_agent_sdk_service.py:1948-1958]；但由 `subagents_enabled` 开关控制，**默认关闭时返回空 dict** —— [:353-355]
- **多租户隔离：成立。** `setting_sources=[]` + `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` —— [claude_agent_sdk_service.py:2016-2017]、[:2158-2159]
- 建议表述：「接入 Claude Agent SDK（`ClaudeSDKClient` 长连接、`can_use_tool` 权限回调、in-process MCP 自定义工具、`AgentDefinition` 具名子 Agent、session resume、adaptive thinking），并通过 `setting_sources=[]` 实施多租户隔离」

### 14.13 「技能包格式为 SKILL.md」

- **结论：成立。** zip + 必须含 `SKILL.md` —— [myskill_service.py:379-380]、[skill_registry_service.py:540]；内容上限 60,000 字符 —— [myskill_service.py:420]；front matter 解析 name/description —— [:456]

### 14.14 其他「无法确认」项（诚实标注）

| 项 | 结论 | 依据 |
|---|---|---|
| Docker 沙箱「实际跑通」 | **无法确认** | 只读核查 + 当前 Windows 平台不建容器 [sandbox_executor.py:149-151]；未实际启动容器；全局报告亦声明未做运行时验证 [AP_Dev_Hub全景分析报告.md:451] |
| gVisor 在生产启用 | **无法确认** | 仅是配置默认值 [config.py:237]；函数默认值是 `runc` [docker_shell_backend.py:327] |
| 技能包「安全扫描」能力 | **不成立（占位字段）** | [skill_info.py:61-66] 有字段无实现 |
| 团队协作后端 | **不成立** | 后端 `harness_teams|Team` 零命中 |
| 对话分享后端 | **不成立（Python 侧）** | 文档自陈「**Python 后端零 share 端点**」[事实更正与工作规则.md:26]；分享能力在 Java 主后端 |
| 知识库功能 | **不成立（只有接口约定）** | 文档要求「只写接口，不写具体功能」[事实更正与工作规则.md:18]；「所有端点返回 `{"enabled": false, "reason": "NOT_IMPLEMENTED", ...}`」[:33] |
| ⑥ 低代码代码生成「有实现」 | **需修正为「原型阶段有静态产物，后端无实现」** | `codegen.zip` 是外部生成器的产物（78 文件 Spring Boot + Vue2）；`ap-poc-agent` 内无生成代码；文档自陈 ⑥ 无源可移植 [事实更正与工作规则.md:70] |
| `AI-chat.html` 的定位 | **无法确认** | 5,860 行单文件，与六阶段主流程交互不同，本次未深入核查 |
| 多 worker / 横向扩展 | **不成立** | EventBus / RunManager / 客户端池均为进程内态 [run_manager.py:15-17]、[AP_Dev_Hub全景分析报告.md:253] |
| 前端 UI「自主开发」占比 | **需注意开源母体** | `package.json` 的 `name: yudao-ui-admin-vue3`；大量遗留模块（BPM 设计器、商城、支付、验证码）非本项目产出 |
| 后端「Docker socket 直挂」风险评估 | **成立（P0 风险）** | [AP_Dev_Hub全景分析报告.md:351-353] |

---

## 十五、可直接引用的「证据强度分级」速查

| 事实 | 强度 | 代表证据 |
|---|---|---|
| REST 端点 = 71 | ★★★ AST 精确 | AST 全量统计（12 模块） |
| SSE 事件 = 13 种 | ★★★ AST 精确 | [claude_agent_sdk_service.py]、[file_watcher.py:564] |
| 回放上限 10000 事件 / 8 MiB | ★★★ 常量直读 | [run_manager.py:35-36] |
| 慢消费者上限 2000 | ★★★ 常量直读 | [run_manager.py:40] |
| RunManager 4 态状态机 | ★★★ 注释+代码 | [run_manager.py:61] |
| **并发冲突返回 500 而非 409** | ★★★ 类型+控制流 | [run_manager.py:46] + [conversations.py:587] + [exceptions.py:122] |
| 危险命令正则 30 条 | ★★★ 可数 | [security.py:34-74] |
| Docker 容器安全参数 | ★★★ 行级 | [docker_shell_backend.py:417-421] |
| gVisor 仅配置项 | ★★★ | [config.py:237] vs [docker_shell_backend.py:327] |
| JWT 双令牌 + 轮换 | ★★★ | [security.py:3-5]、[:129-147] |
| AAD SSO 校验 | ★★★ | [aad.py:46-67]、[auth.py:176-216] |
| ORM 15 表 / models 17 文件 | ★★★ 逐文件 | 第十一节表 |
| `04.数据库设计.yaml` 与 ORM 不一致 | ★★★ 双向集合差 | YAML TableCount=13 vs ORM 15 表 |
| 六阶段名称与顺序 | ★★★ 常量数组 | [store.js:12-19] |
| `getPrevOutput`/`saveStepOutput`/`getAllPrevOutputs` | ★★★ 函数体 | [store.js:166-197] |
| `detectIntent` 4 类意图 | ★★★ 函数体 | [chat.js:54-60] |
| 3 套行业模板 | ★★★ 可数 | [templates.js:13,82,151] |
| 10 个 html（6 主流程 + 4 其它） | ★★★ 目录+行数 | 目录列表 |
| `DSL文件.dmj` 6 表（5 业务表） | ★★★ JSON 直读 | [DSL文件.dmj:2-4] |
| `codegen.zip` 78 文件 Java+Vue2 | ★★★ 解压核对 | 解压清单（TEMP） |
| 纯前端原型（localStorage + mock LLM + 零 fetch） | ★★★ 检索零命中 | [store.js:2]、[chat.js:296]、全仓 zero fetch |
| 61 实体 / 380 属性 / 0 新增表 = 仅文档 | ★★★ 代码零命中 | [03-设计文档.md:659] 等 |
| Docker 沙箱「实际跑通」 | ☆ 无法确认 | 未实际启动容器 |
| `AI-chat.html` 定位 | ☆ 无法确认 | 未深入核查 |

---

*核查完成。全部结论基于 `C:\AP-dorbit-ai` 下源码与文档的只读检查；未修改任何文件；`codegen.zip` 仅在 `$env:TEMP` 下解压查看目录清单，未执行其中任何脚本。*
