# AP Cowork 后端简历逐点详解 + 面试问答手册

> 面向对象:德勤 IDDC AI 应用开发实习生(后端为主)
> 代码版本:`api/ap_agent` repo,2026-09 核对(代码较 README/架构文档新,含 message_blocks、run_manager 等近期迭代)
> 所有行号基于 `C:\Users\jaysguo\OneDrive - Deloitte (CN)\Desktop\AP_Dev_Hub\api\ap_agent\backend\app\`

---

## ⚠️ 先读:简历与代码的 6 处差异(面试前必须知道)

这些是简历描述与真实代码**不一致**的地方。面试官如果技术深,可能问穿;**主动讲清楚反而加分**——说明你真的写过、真的理解。

| # | 简历说 | 代码实际 | 建议 |
|---|---|---|---|
| 1 | "SSE 七类事件 message/tool/todo/artifact/file-tree/done/error" | **实际 12 种事件名**:run_started / token / thinking / subagent_token / tool_start / tool_end / todo_updated / question_pending / artifact_generated / file_tree_updated / done / agent_error。没有 `message` 事件(拆成 token+thinking),没有单一 `tool`(拆成 tool_start+tool_end) | 简历改成"12 类事件流式推送"或"按事件语义(消息/工具/待办/产出物/文件树/终态/错误)推送";面试说法:概念七类,实际 12 种,颗粒度更细 |
| 2 | "AskUserQuestion 挂起等待,用户回答后继续执行" | **不是同一个 AgentRun 恢复**。① 挂起即终态:本轮 run 立即置 `completed`;问题存**内存字典** `_pending_questions`。② 前端提交回答后**自动发起新一轮 `/agent`**,创建**新 AgentRun**,把回答注入,上下文靠 SDK `--resume`(transcript)恢复 | 面试说清机制:挂起是"本轮结束 + 内存待答 + 前端自动重发",不是服务端恢复 |
| 3 | "三层沙箱 Local/Docker/gVisor 配置驱动" | `sandbox_backend` 配置**定义了但没被读**(仅 config.py:212 定义,grep 无读取);实际 `create_sandbox_executor` **只按平台选择**:Windows→Local,Linux→Docker。Docker 的 runtime 参数 `sandbox_docker_runtime` 默认 **runsc(gVisor)** | 面试说法:平台感知策略选择 Windows=Local / Linux=Docker(容器 runtime 可配 runsc 达 gVisor);若被问"auto 怎么选",明确说当前实现是平台判定 |
| 4 | "4 个预置文件夹 Uploads/My Work/My Skill/Results" | **实际 3 个**:uploads / skills(icon_type=my_skill)/ results。不存在 My Work(PRESET_FOLDER_TYPES 只有 3 项) | 简历改成"3 个预置文件夹"或"预置目录体系" |
| 5 | "多租户隔离 X-Workspace-Id" | 是**手动 filter**,非统一查询过滤器:get_workspace_id 解析 header→get_owned_workspace 校验属主(403)→service 查询显式 WHERE workspace_id/owner_user_id→单资源断言 assert_project_owned 等(404)。全库无 with_loader_criteria/event.listen 租户级过滤 | 可以如实说"三段式手工隔离",并主动指出"File/Folder 列表只按 project_id 过滤,靠 project→workspace 链间接隔离,新增查询要手动记得加" |
| 6 | "三层沙箱 + tools/security.py 做命令安全检查" | 属实,但注意 **pip install 不在黑名单**(代码注释明确不拦开发工具),只在提示词层禁止(Windows/预装镜像);**MultiEdit/NotebookEdit 未过 can_use_tool 路径校验**(只拦 write/edit/read) | 若被问"command 安全校验拦什么",答:黑名单命令(rm -rf/sudo/killall/写系统路径等)+探测命令(which/version)+长度上限 4000;补充"pip 这类开发命令是提示词层禁止" |

> 其它小差异:Workspace 与 User 是**单 owner**(owner_user_id 无 FK,非多对多);Reference 只有 `ref_type="web"` 真正被写入(file/skill 只是枚举);DiskSync **只在读路径触发**(TTL 10s + per-project 锁),上传不触发;前端 token 走 **Authorization header**(AxiosSSE),不是 EventSource query param——`/stream?after_seq=N` 断线重连是后端能力,前端 ChatStore 当前未接线。

---

# 第一部分:简历逐点详解

## 1. 双模式对话引擎

### 1.1 Direct Chat(纯 LLM 流式)

**调用链**(`api/conversations.py`):

```
POST /conversations/{id}/chat
  → direct_chat() :268        鉴权 assert_conversation_owned
  → _direct_chat_sse() :290   核心生成器
```

**逐步细节**:

1. **模型选择** :302 `chat_llm = get_llm_by_model(model) if model else llm`;:304 `effective_model = getattr(chat_llm, "model_name", None)` 随 assistant 消息落库
2. **用户消息提前落库** :306-312 —— `add_message(role="user")` 后**立即 commit**。注释:流式路径豁免请求级事务契约,user 消息必须在流开始前持久化(断线重连回放依赖已提交数据)
3. **上下文取最近 20 条** :317 `list_recent_messages(conversation_id, limit=20)`
   - `conversation_service.py:315-327`:按 `created_at desc` 取 limit 条,再 reverse() 成时间正序
   - **条数常量 20 硬编码在调用处**——面试可主动说"这个 20 是硬编码,如果做产品化应该提成参数或按 token 预算动态截断"
4. **构建消息列表** :319-337 —— 首条固定 SystemMessage("你是一个智能工作台助手…"),user→HumanMessage,assistant **仅在 parent.role=="user" 时**转 AIMessage(防止把孤儿 assistant 消息塞进上下文)
5. **流式推送** :342-355 —— `chat_llm.astream(messages)` 逐 chunk 取 content(list 则拼接);每 token 前 `await request.is_disconnected()` 检查断连;yield `{"event": "token", "data": json.dumps({"text": text})}`
6. **落库时机** :364-389 —— **流结束才落 assistant 消息**(`add_message(role="assistant", content=full_content, parent_message_id=user_msg.guid, model=effective_model, duration_ms=...)`),再 commit,最后 yield `done`(含 message_guid/content/duration_ms)。**逐 token 不落库**
7. **异常三路**:
   - LLM 断流/异常 :356-362 → yield `agent_error` 后 return
   - 客户端断连 :350-351 → `request.is_disconnected()` 提前 return
   - assistant 落库失败 :390-398 → 兜底仍发 `done`(不带 message_guid)

**SSE 封装**:`EventSourceResponse(event_generator(), ping=15)` + 手动 `resp.headers['Content-Type']='text/event-stream'`(:400-401)。**ping=15 秒**由 sse-starlette 发注释分隔帧保活。

### 1.2 Agent Chat(Claude Agent SDK 多轮执行)

**调用链**:

```
POST /conversations/{id}/agent
  → agent_chat() :445          RunActiveError → 409
  → _agent_chat_sse() :476
      handle = run_manager.start(conversation_id)   :487 对话级互斥
      producer() 独立任务 :489-526
          async with async_session_factory() as session :497  自建 DB session
          service.run(conversation_id, content, model, skill_id, metadata) :499
          run_started → handle.run_id 回填 :506
          agent_error → saw_error :508
          handle.publish(event) :510
      handle.task = asyncio.create_task(producer()) :528
      event_generator() :541-548  ← 只做订阅转发,不执行
          run_manager.subscribe_stream(conversation_id) 逐事件 yield
```

**核心设计:执行与 SSE 连接解耦**。producer 是独立 asyncio 任务,SSE 的 event_generator 只是 `run_manager.subscribe_stream` 的**订阅者**——客户端断开只取消订阅,Agent 继续执行并落库(`run_manager.py:198-199` finally 移除订阅者)。显式停止走 `POST /stop`(:649-676 → `run_manager.stop` cancel producer),断线重连走 `GET /stream?after_seq=N`(:555-590)。

**AgentRun 创建**(`claude_agent_sdk_service.py run()`):
- :872-879 每轮 `run()` 新建 `AgentRun(conversation_id, message_id=user_msg.guid, status="running", started_at=now)`——模型默认 pending,但**创建即置 running**
- :887 提前 commit(释放 FK 锁,避免 FileWatcher 独立 session 等待)
- 状态流转:`completed`(正常 :1478 / 提问中断 :1405)、`failed`(:1635)、`cancelled`(独立任务 `_finalize_cancelled_run` :542);终点判定 `is_finished`(agent_run.py:112-115)
- AgentRun 字段丰富(面试可讲度量):input_tokens/output_tokens/total_tool_calls/num_turns/first_token_ms/cache_read_input_tokens/cache_creation_input_tokens/duration_ms(agent_run.py:57-80)

**.memory 准备**::896-908 `get_project_root(settings, project.workspace_id, project.guid)` + `makedirs(workspace_root)` + `makedirs(.memory)`。**只建目录不写文件**——内容由 Agent 依据 system prompt(`claude_agent_sdk.md:40-49` "项目共享记忆"节)自行读写,约定 100 行以内、只记决策结论/里程碑/重要路径。`.memory/` 被各服务排除展示(file_watcher 排除、file_service 目录过滤)。

**调 SDK**:
- :1010 `await client.query(query_content)`(query 前注入语言指令+引用路径 :993-1009)
- :1024 `client.receive_response().__aiter__()` 流式消费
- `_get_or_create_client()` :1672-1716:`ClaudeSDKClient(options=options)` + `await client.connect()`;conversation 级长连接存 `_client_store`(按 client/prompt_hash/model)
- **resume(transcript 恢复)**::952 `should_resume = has_history and conversation_id not in _client_store`;:963-967 `options.resume = _format_session_id(conversation_id)`

**每轮查询的超时保护**(防"死循环/挂起"问题):
- 整体预算 `settings.agent_run_timeout` 默认 **600s**(config.py:194-199)
- :1027-1037 `_wait_left = max(_timeout - (now - _start_time), 1.0)` + `asyncio.wait_for(_merged_aiter.__anext__(), timeout=_wait_left)` —— **每次迭代都带剩余预算**,旧实现只在"消息到达"时检查超时,SDK 子进程挂起会无限悬挂。TimeoutError → raise

**工具调用持久化**:
- **start**:ToolUseBlock 分支 :1134 → 累加 total_tool_calls、写文件白名单、`tc_service.start_tool_call(run_id, tool_name, input_args)` :1184-1188,`pending_tool_ids[block.id] = tc.guid`,发 `tool_start` :1222-1225
- **end**:ToolResultBlock 分支 :1256-1279 → `tc_service.end_tool_call(tc_id, output, error_message)` :1275-1279,发 `tool_end`(output 截 `[:500]`) :1289-1292
- **ToolCall 字段**(tool_call.py:25-64):run_id/tool_name/input_args(JSON)/output(JSON)/started_at/completed_at/error_message
- **防大字段打爆 DB**:input/output 超 `tool_call_max_payload_chars=65536`(config.py:205-209)时 `_truncate_input`/`_truncate_output`(tool_call_service.py:78-158)先摘要已知大字段(Write 的 content、Edit 的 old_string/new_string),再递归截最长字符串值,超限标 `_truncated`;写库失败**降级占位记录,绝不打断主流程**
- **立即 commit**(start/end 各自提交):避免长时间持有 FK 锁

**Reference 与 Message 写入**:
- Reference(web):仅 WebSearch/WebFetch 结束 `_record_web_reference()` :2191-2251 写 `ref_type="web"`,按 run 内 URL 去重,立即 commit(:2243)。**注意:file/skill/document 只是枚举值,无写入方**
- Message:user 消息 :862-869 + 提前 commit :887;assistant 消息**四分叉**:正常结束 :1494-1508 / 提问中断 :1421-1435 / 取消 :556-565(_finalize_cancelled_run)/ 失败 :1651-1663,统一经 `_persist_message_blocks()` :90-116 同步写 MessageBlock

### 1.3 消息块时序化(面试亮点,README 没有)

`harness_message_blocks` 表(`models/message_block.py`,共 **15 张表**不是 README 说的 14 张):

- 以有序 block 流保存一次 run 的输出时序:`thinking`(全文唯一存储地)/ `tool_use`(只存 tool_call_id,从 harness_tool_calls 派生,零冗余)/ `text`(只占时序位,全文是 Message.content 物化投影)/ `turn`(存轮号)
- (message_id, seq) 唯一约束 `uk_msg_seq`(:50)保证时序
- 历史查看**两级加载**:索引 SQL 层 SUBSTRING 出 preview(大字段不出库),单段全文按 (message_id, seq) 主键级命中(API:`GET /messages/{id}/blocks` 块索引 + `GET /messages/{id}/blocks/{seq}` 单段原文,:181-204)

---

## 2. Agent 工具链与子 Agent 委派

### 2.1 工具权限回调 can_use_tool(**所有工具统一走回调,不用 allowed_tools**)

`claude_agent_sdk_service.py:1827-1909`,签名 `async def can_use_tool(tool_name, tool_input, _context)`:

```
① 黑名单 tool_name in _DISALLOWED_TOOLS → PermissionResultDeny        :1834-1838
   _DISALLOWED_TOOLS = ["Task", "Skill", "MCP", "Monitor"] (提示词也声明"不存在")
② mcp__ap_tools__todo_write → Allow                                    :1841-1842  (自定义 MCP,无文件/命令操作)
③ websearch/webfetch/askuserquestion → Allow                           :1845-1846  (无文件系统/命令操作)
④ bash → validate_command(command)                                     :1849-1868
     命中黑名单 → Deny (reason=error)
     剥离 Claude Code 原生参数 dangerouslyDisableSandbox(防绕过沙箱)  :1859-1864
     executor.wrap_command(command) 沙箱化包装 → Allow(updated_input) :1866-1868
⑤ write/edit/read → 路径越界校验 + 绝对路径重写                        :1872-1898
     _is_path_within_workspace(p, workspace_root) 越界 → Deny          :1879-1884
     os.path.isabs(p) → realpath+relpath 重写为 workspace 相对路径     :1886-1897
     → Allow(updated_input) 或 Allow
⑥ glob/grep → 只做路径越界校验(不重写,path 语义不同)                 :1900-1907
⑦ 其它 → Allow                                                        :1909
```

**路径校验核心** `_is_path_within_workspace` :1982-2008:
- 拒绝 `~` 开头(家目录)
- **先 realpath(workspace_root)** 再拼接——注释解释了原因:workspace_root 可能含 symlink 组件(Docker 挂载点),必须在 join 前解析,否则目标文件未创建时 abs_path 保留未解析前缀,合法路径被误判越界
- `real_path == base_real or real_path.startswith(base_real + os.sep)` 前缀判定

**⚠️ 已知缝隙(面试主动说)**:MultiEdit/NotebookEdit **未在 can_use_tool 校验**(路径分支只覆盖 write/edit/read),落到最终 Allow(:1909);只在 :1144 被归因到产出物。

**SDK options 关键项** :1911-1942:
| 项 | 值 | 说明 |
|---|---|---|
| permission_mode | `"acceptEdits"` | 编辑自动接受,非 bypass |
| max_turns | `75` | LLM 决策轮数上限 |
| cwd | `workspace_root` | 工作目录=项目根 |
| setting_sources | `[]` | **多租户隔离:禁止 SDK 加载主机级文件系统配置** |
| allowed_tools | `["Agent","Workflow","TaskOutput"]` | 显式暴露 Agent 工具(permission_mode != bypass 时非编辑类工具必须显式声明) |
| mcp_servers | `{"ap_tools": todo_mcp_server}` | todo_write 工具(替代早期 Write→.todos.json 壳) |
| include_partial_messages | `True` | token 流式输出(打字机) |
| thinking | `{"type": "adaptive"}` | 模型自行决定思考深度 |
| max_thinking_tokens | `anthropic_thinking_budget` | 思考预算下限 |

### 2.2 子 Agent 委派

- **定义外置**:`prompts/subagents.json` 定义 2 个具名子 agent:`pre-review`(税务底稿制作前资料检查)、`post-review`(制作后底稿复核),tools=["Read","Glob","Grep"]——只读检查
- **加载**:`_load_subagent_defs()` :233-251(业务文案外置便于维护)→ `_SUBAGENT_DEFS` 受 `settings.subagents_enabled` 控制(**默认 False**,关闭时为空,主 agent 无委派目标)→ `_build_subagents()` :1721-1741 转 AgentDefinition → 传 `agents=` :1932,并渲染进 system prompt 委派段落 :259-266
- **提示词节** :259-266 "通过 **Workflow** 工具委派以下具名子 agent 执行专项任务,并用 **TaskOutput** 等待结果"
- **工具限制**:子 agent 的 `tools=list(d.get("tools", ["Read","Glob","Grep"]))` 直接透传,**无工具数量上限校验**(:1736)——面试被问安全会追问,可答"这里是透传,子 agent 配置来自受信任的 subagents.json,但作为硬化项应加工具白名单"
- 委派会话主 agent 的 `Workflow`/`TaskOutput` 映射为 SSE `sub_agent`/`sub_agent_output`(:733-734),子 agent 的 token 走 `subagent_token` 事件(:1081)填进正在展示的委派工具块

### 2.3 命令安全校验 tools/security.py

- `validate_command()` :97:黑名单 `_FORBIDDEN_PATTERNS` :34-74(rm -rf / del /f / find -delete / sudo / su / chmod 777 / chown root / dd of=/dev / fork bomb / killall / pkill / kill -9 1 / shutdown / reboot / mkfs / 写 /etc、C:\Windows、ProgramFiles)+ `_PROBE_PATTERNS` :78-92(which/version/echo test 等探测命令)+ **长度上限 4000** :94
- **⚠️ pip install 不在黑名单**:代码注释 :32-33 明确"不拦截开发工具";禁止安装只在提示词层(Windows 沙箱 :302 / 预装镜像 :318),裸镜像允许(:332-333)
- 沙箱包装:`sandbox_wrap_command_bash(command, workspace_root)` :255 注入 bash cd 覆写函数限定在 workspace(注意:Windows 下 SDK 的 Bash 也是走 Git Bash,所以用 bash 语义而非 PowerShell 语义)

---

## 3. 四级工作空间模型

### 3.1 实体与隔离

| 层级 | 模型 | 表 | 主键 |
|---|---|---|---|
| Workspace | workspace.py | harness_workspaces | guid |
| Project | project.py | harness_projects | guid (workspace_id CASCADE) |
| Folder | folder.py | harness_folders | guid (project_id CASCADE, parent_id 自引用) |
| File | file.py | harness_files | guid (workspace_id/project_id CASCADE, folder_id SET NULL) |

- 主键统一 `GUIDMixin.guid String(32) = uuid4().hex`(base.py:34-38)——**32 位无连字符**,不暴露自增规模
- **Workspace-User 是单 owner**:`Workspace.owner_user_id String(64) 无 FK`(workspace.py:39-41),无 user_workspace 关联表,**非多对多**
- `workspace_type="personal"`(seed.py:36);full_name="default" 的开发用工作空间由 seed.py 幂等创建(main.py lifespan :72-74 调用)

**多租户隔离三段式(手动 filter)**:
1. `get_workspace_id`(deps.py:53-90):优先 `X-Workspace-Id` Header,兜底 `workspace_id` Query;随后 `get_owned_workspace` 校验属主,非属主 **403**
2. Service 查询显式 WHERE:`Workspace.owner_user_id == owner_user_id`(workspace_service.py:36,64)、`Project.workspace_id == workspace_id`(project_service.py:44)
3. 单资源归属断言:`_assert_workspace_guid_owned`(deps.py:114-127)、`assert_project_owned`(129-143)、`assert_conversation_owned`(146-165)等——JOIN 到 workspace 层校验,失败统一 **404**(不泄露存在性)

### 3.2 预置文件夹(注意:3 个不是 4 个)

- `PRESET_FOLDER_TYPES`(folder.py:28-32):`{"uploads": "uploads", "my_skill": "skills", "results": "results"}` —— **3 个**
- 创建:`folder_service.create_preset_folders` :176-206,由 `project_service.create` :90 调用,生成顺序即 sort_order

### 3.3 文件夹树

- `get_tree`(folder_service.py:441-475):**两遍 dict 映射**(非递归非队列):
  1. list_by_project 拉全部(顺带触发 DiskSync 对齐)
  2. 建 dict 映射 `folder_map[guid] = node_dict`(:451-464)
  3. 第二遍:parent_id 在 map 中则挂 children,否则归根(:466-473)
- **为什么用 dict 不用 ORM**:注释 :446 明确——避免 SQLAlchemy 关系描述符赋值触发异步懒加载 `MissingGreenlet`
- 唯一约束双层:(project_id, path) DB UniqueConstraint(folder.py:86)+ 业务层预检(create :145-153 / rename :295-304 → 409 而非撞库 500)

---

## 4. 产出物(Artifact)与引用(Reference)

### 4.1 FileWatcher(产出物自动捕获)

`file_watcher.py`,基于 **watchdog**(Observer + FileSystemEventHandler):

- **监听范围**:递归监听整个 workspace_root(`recursive=True` :190)
- **事件**:on_created :51 / on_modified :55 / on_moved :59(且 on_moved **仅当 src 是 SDK 临时文件**——重命名触发 on_moved 而非 on_created,但用户手动重命名也会触发,需靠 src 文件名区分)——非目录事件忽略
- **排除目录** `ARTIFACT_EXCLUDED_DIR_NAMES = {.claude, .memory, temp, skills}`(file_storage.py:30);排除文件:.开头/~、.tmp、.swp、.log、SDK 临时文件模式 `\.tmp\.\d+\.[0-9a-f]+$`(_TMP_FILE_PATTERN :28)
- **入库** `_create_artifact` :447:先建 File(file_source="generated")再建 Artifact(run_id, file_id, artifact_type, title, relative_path)
- **去重**:内存 seen set + DB 终极去重查询(Artifact.run_id+relative_path :499-510)+ _known_files
- **防抖**:无真防抖,靠 `_CONSUME_INTERVAL=0.5`(:109)轮询 + get_nowait 排空 + flush()(:262)在 done SSE 前兜底
- **event_bus 关系**:只 publish 不 subscribe——`_create_artifact` 末尾 `event_bus.publish(run_id, SSEEvent(type="artifact_generated", ...))` :562-579

### 4.2 Artifact 模型与查询

- `harness_artifacts`(artifact.py):run_id / file_id(nullable)/ artifact_type(默认 file,枚举 file|markdown|text|html)/ title / relative_path / meta(JSON)
- 索引:idx_artifact_run / idx_artifact_type
- 查询:`GET /artifacts?run_id=X` → assert_run_owned → list_by_run(run_id+deleted_at 过滤,升序,joinedload(file));另有 list_by_conversation(JOIN AgentRun 按 path 去重保留最新,run_count)
- `ArtifactRead.model_validator` 把 guid 替换为 file_id(schemas/artifact.py:60-65)——未入库文件 preview 时前端拿 file_id 为 null

### 4.3 Reference

- `harness_references`(reference.py):run_id / ref_type / ref_name / ref_path / ref_meta(JSON),索引 idx_reference_run
- 实际写入**只有 `ref_type="web"`**(WebSearch/WebFetch 结束,_record_web_reference :2191-2251);file/skill/document 只是枚举值;file_service.py:780 / folder_service.py:374 仅在文件改名时**级联更新** ref_type=="file" 的 ref_path,不新增

---

## 5. Skill 双轨体系

### 5.1 项目级 Skill(harness_myskills)

- 字段(MySkill):workspace_id / project_id / name / description / md_content / py_content / path
- **LLM 生成流程**:system prompt 拼入 `skill_creation.md`(:372,经 `_load_system_prompt("skill_creation.md")`)——给出目录结构(skills/{name}/SKILL.md + scripts/references/assets)与 SKILL.md 标准格式(描述/触发条件/输入/输出/使用示例/依赖/约束 7 段)
- 生成后物化到项目 `skills/` 目录并同步 harness_myskills

### 5.2 Skill 注册中心(harness_skill_registry)

- **模型字段丰富**(skill_info.py):skill_name(64)/ version(20)/ tags/dependencies/permissions(JSON)/ entry / python_requires / timeout_seconds(默认 300)/ publisher_id / storage_path / checksum_sha256 / download_count
- **三重状态机**(面试素材):
  - `review_status`:pending / approved / rejected
  - `scan_status`:pending / passed / warning / blocked(安全扫描)
  - `visibility`:public / private
- **发布** create :99:按 (skill_name, version) 查重 :110-120,sha256,zip 存 `skill_registry/{name}/{version}/{name}-{version}.zip`,初值 pending/private/pending
- **审核**:approve :191 → approved+public;reject :200 → rejected+reject_reason;版本唯一逻辑键=(skill_name,version)(_get_or_throw :85;模型无 DB unique 约束)
- **安装** install_to_workspace :347:校验 review_status==approved :373 → 校验 workspace/project 归属 → `_parse_skill_zip` 取 SKILL.md/scripts/helper.py/附属文件(**防 zip-slip** :529-547)→ MySkillService.create 或按 name 覆盖(idempotent);同项目原地覆盖 SKILL.md/helper.py(_update_materialized_in_place :580),跨项目先删旧 Folder 再 materialize;写进项目 skills/ 目录并建 Folder/File 记录

---

## 6. 三层沙箱执行

### 6.1 策略选择(注意:不是配置驱动)

`create_sandbox_executor`(sandbox_executor.py:140-162):
- `_IS_WINDOWS = platform.system() == "Windows"` :24
- Windows → `LocalSandboxExecutor`;Linux → `DockerSandboxExecutor`(image/runtime/timeout 来自 settings)
- **⚠️ `sandbox_backend` 配置(config.py:212 默认 "auto")没有任何代码读取**——README 说 auto/local/docker 配置驱动,实际是平台判定。面试说法:"策略是平台感知的:Windows 本地、Linux Docker(runtime 可配 runsc)"

### 6.2 Local Shell(Windows)

- `LocalSandboxExecutor.wrap_command` :70-73 → `sandbox_wrap_command_bash(command, workspace_root)`(tools/security.py:255)注入 bash cd 覆写函数,阻止 Agent 通过 cd 越界 workspace
- 不创建容器,零额外依赖
- 不做 pip 禁令(提示词层)

### 6.3 Docker(容器沙箱)

- `DockerSandboxExecutor`(sandbox_executor.py:79-134):`docker exec -i <container> timeout <t>s sh -c <quoted>`(:130-134)——直接 docker exec + timeout + sh -c,**避免双层 sh -c 嵌套转义混乱**
- 容器名:`ap-cowork-{app_env}-{sha256(workspace_root)[:12]}`(docker_shell_backend.py:280-284)
- 复用 docker_shell_backend 生命周期:模块级 `_containers` 缓存(workspace_root→(container, last_ts) :43);`ensure_container` 复用/reload/start/recover/新建;`_evict_if_needed` :93 上限 `sandbox_max_containers`(默认 **50**)按 LRU 淘汰
- 空闲回收 `_reap_idle_containers` :118:每 `_REAP_INTERVAL=3600` 秒(:40)检查 idle ≥ `sandbox_idle_timeout`(默认 **86400**)→ stop;reaper 由 start_sandbox_reaper :154 启动,app 关闭时 main.py:82/92 stop;atexit `_stop_all_containers` :81
- 强化(`docker run` 参数 :417-421):`cap_drop=["ALL"]` / `no-new-privileges` / `mem_limit=512m` / `cpu_quota=100000`
- bind mount:`volumes={host_workspace_root: {bind: "/workspace", mode: "rw"}}`(:413);HOST_FILES_ROOT→FILES_ROOT 前缀替换(_resolve_host_path :309)
- 与 SDK Bash 衔接:can_use_tool 里 `executor.wrap_command(command)` 包装后替换 tool_input,SDK 子进程执行的就是包装后的命令;DockerShellBackend.execute :586 → `container.exec_run(["sh","-c",wrapped], workdir="/workspace")`,输出截断 100KB,失败自动重建容器

### 6.4 gVisor

- 不是独立一层,是 Docker 的 **runtime 参数**:settings.sandbox_docker_runtime **默认 "runsc"**(config.py:226-229),传给 docker run `--runtime=runsc`
- DockerSandboxExecutor 类默认 runtime="runc"(:96),但工厂传入 settings 值 → **实际默认走 runsc(gVisor)**

---

## 7. 实时交互机制(SSE 七类事件 → 实际 12 种)

### 7.1 事件枚举(真实)

| 事件名 | 产生位置 | payload |
|---|---|---|
| run_started | sdk_service:891 | {run_id, conversation_id} |
| thinking | :1070 / :1105 | {text}(已脱敏路径) |
| token | :1096 / conversations.py:353 | {text} |
| subagent_token | :1081 | {text} |
| tool_start | :1222 | {tool(display), input(脱敏)} |
| tool_end | :1289 | {tool, output[:500]} |
| todo_updated | :1201 / :1519 | {todos: [{content, is_completed}]} |
| question_pending | :1237 | {conversation_id, questions} |
| artifact_generated | FileWatcher 经 event_bus 转发 :1041-1042 | {filename, artifact_id, path} |
| file_tree_updated | :1524 | {project_id} |
| done | :1448 / :1529(Agent);conversations.py:380,393(Direct) | Agent:{run_id, message_id, usage, duration_ms, stats};Direct:{message_guid, content, duration_ms} |
| agent_error | :1668;conversations.py:358 | {message}(友好文案) |

### 7.2 断线重连与事件回放(run_manager.py,面试高光)

**设计**:Agent run 由独立 producer 任务驱动,SSE 连接只是订阅者——断开不中断执行(main.py lifespan 也会 `run_manager.shutdown_all()` 优雅取消)。

**RunManager 核心机制**:
- **对话级互斥**:`start()` :127-135 若已有 running handle → RunActiveError → 409(替代旧的"一个 SSE=一个 run"隐式约束)
- **事件广播**:一个 run 可多订阅者(多标签页),每订阅者独立 asyncio.Queue(subscribers dict :71)
- **事件回放**:环形缓冲 deque + 单调递增 seq;`REPLAY_MAX_EVENTS=10_000` + `REPLAY_MAX_BYTES=8MB` 双上限(:35-36),超限置 replay_truncated=True(前端降级为只实时 + 轮询 run-status)
- **慢客户端保护**:`MAX_SUBSCRIBER_QUEUE=2_000`(:40)订阅队列积压超限 → 丢弃该订阅(发 None 哨兵),客户端走断线重连从回放缓冲恢复
- **断线重连**:`GET /stream?after_seq=N`(:555-590)先回放 seq>N 的缓冲,再转实时;`subscribe_stream`(:153-199)**先注册队列再回放**,按 seq 单调去重保证"不丢不重"
- **结束句柄保留**:`FINISHED_HANDLE_TTL=600` 秒(:43),供断线重连回放/查询终态,超时惰性清除(_purge_finished :249-259)
- **多标签页同步**:所有页面订阅同一 handle,事件广播到每个订阅队列——前端刷新页面后连 /stream 可续看

**事件总线 EventBus**(core/events.py):全局单例,per-task_id asyncio.Queue,`SSEEvent(type, data)` dataclass;注明"单进程内存队列,不支持多 worker 共享,多 worker 需 Redis Pub/Sub/Kafka;unsubscribe 必须调用否则泄漏"——config.py server_workers **强制 =1** 与此相关。

## 8. AskUserQuestion 挂起追问(如实说清"不是同一 run 恢复")

### 8.1 检测与挂起

- ToolUseBlock 分支,`display_name == "ask_user_question"`(sdk_service:1228):
  1. `_pending_questions[conversation_id] = questions`(:1230)——**模块级内存字典** `_pending_questions: dict[str, list[dict]]`(:399),非 DB 字段
  2. yield `question_pending` SSE(:1237-1243)
  3. `awaiting_answer = True`(:1248),`break` 立即中止消息流(:1249)
- 该轮 run **立即终态化**为 `completed`(:1405),`awaiting_answer` 分支提前 return(:1471)——"挂起的 run"其实是"已完成的 run + 内存里的待答问题"

### 8.2 回答提交与"唤醒"

- `POST /answer-question`(:412-422)→ `submit_question_answers`(:2421-2445):
  ```
  ① conversation_id 不在 _pending_questions → return False(:2431-2436)
  ② _question_answers[conversation_id] = answers(:2437)
  ③ _pending_questions.pop(...)(:2440)
  ④ return True
  ```
  **它只存回答并清待答,不启动任何执行**。
- **真正的"继续"是前端自动发新一轮**:useChatStore.js submitAnswers()(:186-219)在成功 POST 后 `if (!appStore.isStreaming && answerText) await sendMessage({text: answerText})`(:216-218)→ 创建**新 AgentRun**
- **回答注入**:新一轮 run() 开头 `previous_answers = _question_answers.pop(conversation_id, None)`(:842-843)拼进 user_content(:844-853)
- **上下文怎么"记得"**:SDK transcript resume——`has_history` 且客户端已 `_cleanup_client`(:1469)→ `should_resume=True`(:952)→ `options.resume = _format_session_id(...)`(:963-967)
- **超时/并发**:挂起无服务端倒计时(因为 run 已终态、会话已释放);整体超时仍由 agent_run_timeout 兜底;`_pending_questions`/`_question_answers` 无独立锁(极小竞态窗口),但对话级互斥由 run_manager.start 保证,提问中断后会话空闲可立即开新一轮

---

## 9. 文件预览与项目虚拟站点

### 9.1 文件预览(需登录、非公开)

- `get_preview_type`(file_preview_service.py:40-63)按 MIME/扩展名路由:image(二进制流)/ markdown / html / pdf / excel(**pandas** 读 Excel 转 CSV,多 sheet 用 `# Sheet:` 前缀分隔 :34)/ docx(**mammoth** 转 HTML,图片 base64 内联)/ csv / text(txt/json/yaml/js/css)/ binary
- 路由 `GET /files/{guid}/preview`(files.py:147-224):按 File.guid + deleted_at IS NULL 查,`_assert_workspace_guid_owned` 校验**文件所属 workspace 归属当前用户**(:163)——**不是公开接口**
- **注意与虚拟站点区分**:预览走 JWT,虚拟站点免登录

### 9.2 项目虚拟站点(公开、免登录)

- **公开机制**:core/auth.py:25 `PUBLIC_PATH_PREFIXES = ("/api/preview/",)` —— /api/preview/* 全部跳过认证中间件
- **入口**:`GET /api/preview/{project_id}`(preview.py:118)/ `GET /api/preview/{project_id}/{path}`(:134);用 `Project.guid` 定位根:`{files_root}/workspace_{ws_guid}/project_{project_guid}`(_site_root :51-53 → file_storage.get_project_root :57-63)
- **path traversal 防护** `safe_join`(file_storage.py:66-89):每个 part `lstrip("/\\")`(防 LLM 传 /uploads 覆盖 base)→ abspath → **realpath 解析符号链接**(防 symlink 绕过)→ 校验在 base 下,越界抛 ValidationError;preview.py _resolve :84-92 把 ValidationError 转 **NotFoundError(404)**——穿越返回 404 而非 403,不泄露路径结构
- **目录回退**:`_find_index` :56-63 先查 index.html;仅当在**站点根级**(abs_path == site_root)才额外回退 entrypoint.html(_INDEX_FILES=("index.html","entrypoint.html") :36)
- **无尾斜杠重定向**::111-115 `307 Temporary Redirect` 补 `/` 并保留 query(如 access_token)
- **Content-Type**:`_file_response` :66-81 优先查 `_EXTRA_MIME_TYPES`(woff2/woff/ttf/otf/eot/map/webmanifest/wasm :39-48),否则 mimetypes.guess_type,兜底 application/octet-stream
- **缓存头**:`Cache-Control: no-store`(实时读盘,文件更新即时生效)+ `X-Content-Type-Options: nosniff`(防 MIME 嗅探)

---

## 10. 认证与数据同步(简历最后一条)

### 10.1 JWT 双令牌

- **过期常量**(config.py):access `token_expire_minutes=60`(:314-319);refresh `refresh_expire_days=30`(:320-325);算法 HS256(:326-329)
- **签发**(security.py):`create_access_token` :69 / `create_refresh_token` :81 → `_create_token` :55-66,payload:`{"sub": user_id, "iss": "ap-cowork", "type": access|refresh, "jti": secrets.token_hex(16), "iat", "exp"}` —— **注意 user_id 存在 `sub` 不是 `user_id` 键**
- **验证**:`_decode_token` :93-116 `jwt.decode(..., issuer=_TOKEN_ISSUER, options={"require": ["sub","exp","type"]})` 后校验 type 与 expected_type;decode_access_token :119 / decode_refresh_token :124 返回 payload["sub"]
- **刷新轮换** `rotate_refresh_token` :129-147:校验通过后把旧 refresh 的 `jti` 写入模块级内存 dict `_revoked_refresh_jtis`(:36),**旧 token 重放即拒**;⚠️ 内存态、进程重启清空,跨重启持久化需 DB/Redis(注释 :33-36 明确当前不做)——与 server_workers=1 配套
- **JWT_SECRET** `resolved_jwt_secret` :331-347:显式配置优先;**生产缺失 fail-fast(RuntimeError)**;dev 自动 `secrets.token_hex(32)`(所以 dev 重启全登出)
- **bcrypt**(auth_service):`_hash_password` :59-61 `bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))`(**cost=12**);`_verify_password` :64-66 checkpw;AAD 建号默认密码 `DEFAULT_PASSWORD="abc@55667788"` :41

### 10.2 AAD 单点登录

- **token 传输**:`POST /api/auth/aad-login`,微软 token 放在 `Authorization: Bearer <aad_token>`(api/auth.py:193)——复用同一 header,内容是微软 token 非项目 JWT;该路径在白名单
- **JWKS**:core/aad.py `decode_aad_token` :30-76 用 `PyJWKClient(settings.resolved_aad_jwks_uri, cache_keys=True)`(:46-50,pyjwt>=2.8 内置,自动缓存);`get_signing_key_from_jwt(token)` :51 从 JWT header 取 kid 匹配
- **校验**:`jwt.decode(token, key, algorithms=["RS256"], audience=settings.aad_client_id, leeway=30, options={require:["sub","exp","aud"]})`(:53-67)——**audience 严格校验了,issuer 没显式传参**(issuer 信任隐含于"用该 tenant JWKS 验签成功");时钟偏移 `_ALLOWED_CLOCK_SKEW_SECONDS=30` :23
- **邮箱提取**:preferred_username → email → name(:69-73),小写 + strip
- **用户映射**(auth_service.aad_login :219-270):按 `User.email`(unique=True, user.py:34-39)匹配,不存在则自动建号(`user_id = email[:64]` 截断 :248、默认密码、display_name 取 @ 前缀);已软删则拒绝;历史 email IS NULL 用户补绑(:263-266)
- **⚠️ 注意"首次登录自动注册"严格说只对 AAD 路径成立**:本地密码登录不自动注册用户(无独立 register 接口,用户需预先存在);"登录即自动建默认工作空间"两个路径都有(`_ensure_workspace` :117-134,login :176 / aad_login :268 都调用)

### 10.3 认证中间件

- core/auth.py `auth_middleware` :41-63:`path.startswith("/api")` 且不在白名单且不以 `/api/preview/` 开头 → 校验
- 白名单:`PUBLIC_PATHS = {"/api/auth/login", "/api/auth/aad-login", "/api/auth/refresh"}`(:22);前缀白名单 `("/api/preview/",)`(:25);非 /api/* 一律放行
- **token 来源**(security.py `extract_token` :150-157):Authorization "Bearer " header 优先,兜底 query `access_token`(SSE/图片/iframe 无法带 header)
- **校验失败**:401 + body `{"error":{"code":"unauthorized",...}}` + `WWW-Authenticate: Bearer`(:28-38)
- user_id 写入 `request.state.user_id`(:61);`deps.get_current_user`(deps.py:34-46)直接 getattr 复用,不再信任 X-User-Id header
- **中间件只做认证不做授权**:管理员判定在 `deps.assert_admin`(deps.py:228-247):`admin_user_ids` 白名单(config.py:304-307)或 DB `role=="admin"`,非 admin 403;仅 reset_password 调用

### 10.4 磁盘-数据库同步(disk_sync_service)

- **触发:只在读路径**——folder_service.list_by_project :98、file_service.list_by_folder :104 / list_all_by_project :122(上传不触发,启动不触发)
- **TTL 节流**:`SYNC_TTL_SECONDS=10.0`(:37-38)新鲜度判断 + per-project asyncio.Lock(:43-47)拿锁后复查 TTL(:110)
- **扫描**:`_walk_disk` :50-87 在 asyncio.to_thread 里单次 os.walk,`dirs[:]` 剪枝排除目录(EXCLUDED_DIR_NAMES={.claude,.memory,.trash,temp} file_storage.py:23),跳过 EXCLUDED_FILE_NAMES={.todos.json}(:27)
- **两次同步**:
  - `_sync_folders` :159-238:登记磁盘新增目录、修复 parent_id、硬删 DB 有但磁盘无的**非预置**"幻影文件夹"(preset_roots 保护)
  - `_sync_files` :240-323:磁盘新文件登记为 `file_source="generated"`;DB 有磁盘无的孤儿文件**硬删前先软删关联 Artifact**(:303-316);已存在记录只补 folder_id 不覆盖元数据
- **冲突处理**:DB 为记录源、磁盘为驱动增删;IntegrityError 回滚重试一次(:114-119);`_ensure_folder_chain` :325-360 防御性补中间目录链;统一一次 flush() 提交(:157)
- **⚠️ skills 不排除在同步之外**(它在文件树里;skills 只进 ARTIFACT_EXCLUDED_DIR_NAMES,仅产出物展示排除)

---

# 第二部分:面试问答库

## A. 高频深度题(按简历点)

**Q1 为什么 Agent 模式要把执行和 SSE 连接解耦?**
答:因为 SSE 连接是脆弱的(用户关页面/网络抖动),而 Agent 任务可能跑几分钟。解耦后:① 客户端断开只取消订阅,Agent 继续执行并正常落库;② 断线重连走 GET /stream?after_seq=N 从回放缓冲补发;③ 多标签页都能订阅同一 run 的事件流;④ 显式停止走 /stop 取消 producer 任务,取消时走既有 CancelledError 落库路径。核心代码:_agent_chat_sse(:476-552)里 producer 是 asyncio.create_task,event_generator 只做 run_manager.subscribe_stream 转发。

**Q2 同一对话并发提交怎么阻止?**
答:run_manager.start(:127-135)显式检查——已有 status=="running" 的 handle 抛 RunActiveError,agent_chat 捕获转 409(:469-473)。这替代了旧的隐式约束"一个 SSE 连接=一个 run"。每个 run 可多订阅者广播,断开仅取消订阅。

**Q3 跑死循环/挂起靠什么超时?为什么既有消息到达检查还要 wait_for?**
答:整体 agent_run_timeout=600s(config.py:194-199)。主循环每个迭代算 `_wait_left = max(_timeout-(now-_start_time), 1.0)`,然后 `asyncio.wait_for(_merged_aiter.__anext__(), timeout=_wait_left)`(:1027-1037)。旧实现只在"消息到达"时检查超时,SDK 子进程挂起后 run 会无限悬挂;改成每次迭代带剩余预算的 wait_for,配合 _merge_sdk_and_events(:664-714)合并 event_bus,保证 artifact_generated 事件不被 async for 阻塞。

**Q4 AskUserQuestion 到底是同 run 挂起还是新开 run?状态存哪?**
答:新开 run(如实答)。提问中断时本轮 run 立即 completed(:1405);问题存内存字典 _pending_questions(:399),不是 DB 字段;前端 POST /answer-question 后 submit_question_answers 只存回答+清 pending(:2421-2445),随后前端 sendMessage 发起新一轮 /agent(useChatStore.js:216-218);新一轮 run() pop 出回答注入 user_content(:842-853),上下文靠 SDK --resume transcript 恢复(:963-967)。无服务端挂起超时(因为 run 已终态、会话已释放)。

**Q5 工具调用怎么持久化并防止超大输出打爆 DB?Reference 何时写入?**
答:start_tool_call 写 ToolCall(run_id/tool_name/input_args/started_at),end_tool_call 更新 output/error_message/completed_at,两者立即 commit(避免长时间持 FK 锁让 FileWatcher 独立 session 等)。防大:input/output 超 65536 字符(tool_call_max_payload_chars config.py:205-209)时 _truncate_input/_truncate_output 先摘要已知大字段(Write 的 content、Edit 的 old_string/new_string)再递归截最长字符串值,超限标 _truncated;写库失败降级占位记录但绝不打断主流程。Reference 仅 WebSearch/WebFetch 结束经 _record_web_reference(:2191-2251)写 ref_type="web",按 URL 去重,立即 commit。

**Q6 多租户隔离怎么做?有没有统一过滤?越权风险?**
答:手动三段式——① get_workspace_id(deps.py:53-90)取 X-Workspace-Id(header 优先/query 兜底),get_owned_workspace 校验属主(403);② Service 查询显式 WHERE workspace_id/owner_user_id;③ 单资源断言 assert_project_owned 等(404 不泄露存在性)。全库无 with_loader_criteria/do_orm_execute 级租户过滤器。风险:File/Folder 列表只按 project_id 过滤(file_service.py:105-113),隔离依赖 project→workspace 链,新增查询必须手动补过滤,忘漏即越权——这是将来可以强化的点。

**Q7 safe_join 怎么防 path traversal 和 symlink 绕过?**
答:file_storage.safe_join(:66-89):每 part lstrip("/\\") 防绝对路径覆盖 base(针对 LLM 传 /uploads);abspath 后 realpath 解析符号链接;校验 real_path 在 base_real 之下,越界抛 ValidationError。preview.py _resolve(:84-92)把 ValidationError 转 NotFoundError(404),不返回 403、不泄露路径结构。fléé注意两个调用点:文件读写的 safe_join 与 can_use_tool 的 _is_path_within_workspace(:1982-2008)是等价的双保险。

**Q8 文件上传安全链路有哪些防线?**
答:① 扩展名双层:黑名单先拦(blocked_file_extensions: .exe/.sh/.bat/.cmd/.com/.scr/.msi/.dll/.ps1)+白名单放行(allowed_file_extensions 40+ 种);② 大小 max_upload_size_mb=50(52,428,800 字节);③ 重名 overwrite=false → 409,前端确认后 overwrite=true 覆盖并软删旧 Artifact(zip 端点不暴露 overwrite,zip 冲突恒 409);④ zip 防线:testzip 完整性、跳过 __*/.* 目录(.env 例外)、解压总量 max_zip_extract_size_mb=500、文件数 max_zip_file_count=2000、逐文件扩展名/大小校验、单文件失败隔离继续。

**Q9 产出物是怎么自动捕获的?会不会漏或重复?**
答:watchdog Observer 递归监听 workspace_root,on_created/on_modified/on_moved(后者仅当 src 是 SDK 临时文件,区分用户手动重命名)。排除 .claude/.memory/temp/skills 目录和 .tmp/.swp/.log/SDK 临时文件模式。入库 _create_artifact:447 先建 File(file_source="generated")再建 Artifact。去重:内存 seen set + DB (run_id, relative_path) 真实查询 + _known_files。防抖:无真防抖,靠 _CONSUME_INTERVAL=0.5s 轮询排空 + done SSE 前 flush 兜底。漏检由快照兜底补建(基线上新增文件)。

**Q10 Skill 市场发布到安装的完整流程?状态机有哪些?**
答:发布:按 (skill_name, version) 查重 → sha256 → zip 存 skill_registry/{name}/{version}/ → 初值 review_status=pending + scan_status=pending + visibility=private。审核:approve→approved+public;reject→rejected+reject_reason。安装:校验 review_status==approved → 校验 workspace/project 归属 → _parse_skill_zip 防 zip-slip 取 SKILL.md/scripts/helper.py → MySkillService.create 或按 name 覆盖;同项目原地覆盖 SKILL.md,跨项目先删旧 Folder 再 materialize 到项目 skills/ 目录。三重状态机:review(pending/approved/rejected)+ scan(pending/passed/warning/blocked)+ visibility(public/private)。

**Q11 沙箱三层怎么选?命令安全校验拦什么?**
答(如实):策略是平台感知——Windows→Local(注入 bash cd 覆写函数限定 workspace,零依赖);Linux→Docker(容器名 ap-cowork-{env}-{sha256(workspace_root)[:12]},cap_drop ALL/no-new-privileges/mem 512m/cpu 限制,bind mount /workspace,空闲回收 1h 检查/idle 24h/LRU 50 容器上限);runtime 参数可配 runsc(gVisor,默认值)。命令校验 validate_command:黑名单(rm -rf、sudo、chmod 777、dd、fork bomb、killall、写 /etc 等)+ 探测命令(which/version)+ 长度 4000;pip install 不在黑名单(注释不拦开发工具),靠提示词层禁止。已知缝隙:MultiEdit/NotebookEdit 未过 can_use_tool 路径校验;sandbox_backend 配置项已定义但未读(按平台判定)。

**Q12 SSE 事件有哪些?怎么保证不丢不重?**
答:实际 12 种事件名(run_started/token/thinking/subagent_token/tool_start/tool_end/todo_updated/question_pending/artifact_generated/file_tree_updated/done/agent_error),简历归纳为七类概念。不丢不重:RunHandle 单调递增 seq + 环形缓冲回放(1 万条/8MB 双上限)+ subscribe_stream 先注册队列再回放,按 seq 单调去重;慢客户端订阅队列积压超 2000 丢弃该订阅(发结束哨兵)走断线重连。EventBus 是单进程 asyncio.Queue 实现,多 worker 需 Redis(server_workers 强制 1)。

## B. 常被追问的"为什么"题

**Q13 为什么表主键用 GUID 而不是自增?**
答:① 不暴露数据规模(防 ID 遍历枚举);② 分布式/多实例下无需协调;③ 前端与文件系统路径都用 guid,便于软删除与外部引用;代价是索引略大、无自增局部性(写性能略降),32 位 hex(128bit UUID 去掉连字符)作为 String(32) 存储是 IO 与可读性的折中。

**Q14 Direct 模式为什么只取最近 20 条上下文?**
答:控制 token 成本与延迟,20 条硬编码在 conversations.py:317(说明这是早期产品选择)。构建时用 parent_message_id 配对 user↔assistant,assistant 消息仅当其父是 user 才进上下文,防止孤儿消息污染。Agent 模式没有该截断:走 SDK transcript resume 全量恢复(由 SDK 内部管理窗口)。

**Q15 为什么 .memory 只建目录不写内容?**
答:后端职责是"提供产物物化与隔离",记忆内容属于 Agent 行为——由 system prompt 明确规定格式(.memory/project_context.md,100 行以内,记决策/里程碑/重要路径)与维护时机(开始读、重要节点更新)。这样平台与模型解耦,换模型/换提示词不影响平台代码。

**Q16 EventBus 和 run_manager 是什么关系?为什么有两个?**
答:EventBus(core/events.py)是通用 per-run_id asyncio.Queue 发布/订阅,FileWatcher 用它 publish artifact_generated(只 publish 不 subscribe),SDK run 里 _merge_sdk_and_events 合并消费;run_manager 是 run 生命周期管理(互斥/广播/回放/停止/shutdown),SSE 端点直接用 run_manager.subscribe_stream。run_manager 内部每订阅者独立队列,且带回放缓冲,比 EventBus 重但功能完整——artifact 事件经 EventBus 汇入 _merge,再经 run_manager.publish 广播。

**Q17 断线重连 /stream 怎么实现?限制是什么?**
答:GET /stream?after_seq=N,handler 拿 handle 后 subscribe_stream(conversation_id, after_seq):先回放缓冲中 seq>N 的事件再转实时;run 已结束且 handle 在保留期(600s)内时回放全部含终态后关闭。限制:单进程内存态(多 worker 需外置 Redis);回放缓冲超限(1 万条/8MB)置 replay_truncated,前端降级;前端 ChatStore 当前只用了 /agent,未接 /stream(如需可说这是后端已具备的接口能力)。

**Q18 文件预览和项目虚拟站点有什么区别?**
答:两个不同机制。预览 /files/{guid}/preview 需 JWT,校验文件所属 workspace 归属当前用户;虚拟站点 /api/preview/{project_id}/* 完全公开(白名单前缀),project_id 即站点,任何人生成网页即可访问。两者都走 safe_join 防穿越,虚拟站点支持目录回退 index.html/entrypoint.html(entrypoint 只在根级)与 307 补斜杠,Content-Type 扩展名映射。

---

# 第三部分:建议的简历微调(与代码对齐后更抗面试)

1. ~~"SSE 七类事件 message/tool/todo/artifact/file-tree/done/error"~~ → **"SSE 流式事件协议(token/thinking/tool_start/tool_end/todo/question/artifact/file_tree/done 等 12 类事件,支持断线重连与多端订阅)"**
2. ~~"4 个预置文件夹(Uploads/My Work/My Skill/Results)"~~ → **"项目创建自动生成 uploads/skills/results 预置目录"**
3. ~~"三层沙箱 Local Shell/Docker/gVisor 独立配置"~~ → **"平台感知沙箱策略(Windows 本地拦截/Linux Docker 隔离,容器 runtime 支持 runsc/gVisor 强化)"**
4. "AskUserQuestion 挂起等待用户回答,回答后继续执行" → 可保留,但面试按"新 run + resume"讲
5. 可补充亮点(README 没有的):**消息块时序化(MessageBlock 两级加载)、run_manager 事件回放与断线重连、ToolCall 超 64KB 截断、Skill 三重状态机、EventBus 慢消费者保护**

---

# 附:核心文件速查表

| 文件 | 内容 |
|---|---|
| app/services/claude_agent_sdk_service.py(2450 行) | Agent 执行核心:run/流解析/can_use_tool/子agent/AskUserQuestion/落库 |
| app/services/run_manager.py(263 行) | run 生命周期:互斥/广播/回放/停止/shutdown |
| app/services/conversation_service.py | 消息 CRUD/上下文读取/消息块懒加载 |
| app/api/conversations.py(723 行) | 路由:chat/agent/stream/run-status/stop/answer-question |
| app/core/events.py | SSEEvent 结构 + EventBus(单进程队列) |
| app/services/tool_call_service.py | ToolCall 持久化 + 64KB 截断 |
| app/services/file_watcher.py | watchdog 监听 → Artifact 落库 + event_bus publish |
| app/services/sandbox_executor.py | 平台感知沙箱策略选择 |
| app/services/docker_shell_backend.py | 容器生命周期(缓存/LRU/空闲回收/强化参数) |
| app/services/myskill_service.py / skill_registry_service.py | Skill 双轨 |
| app/services/disk_sync_service.py | 读路径 TTL 同步 |
| app/services/file_storage.py | 路径安全 safe_join + 排除规则常量 |
| app/core/security.py + core/auth.py + core/aad.py | JWT/bcrypt/中间件/AAD |
| app/core/config.py | 全部常量(60min/30d/50MB/500MB/2000/75/600s/runsc 等) |
| app/models/*.py | **15 张表**(比 README 多 harness_message_blocks) |
