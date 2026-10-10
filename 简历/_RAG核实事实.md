# RAG 项目（github.com/baotang3/RAG）源码核实清单 v2

克隆位置：`$env:TEMP\RAG-repo`（--depth 1，最新提交 1eaea86，提交日期 2026-07-31）
所有路径相对仓库根目录 `backend/app/...`。

## 规模

| 项 | 数值 | 证据 |
|---|---|---|
| 后端 Python 文件 | 46 | `Get-ChildItem -Recurse backend -Filter *.py` |
| 后端 Python 总行数 | 4,594 | 同上，`Get-Content | Measure-Object -Line` |
| REST 接口 | 37 + `/health` | knowledge 5 + document 9 + chat 6 + agent 5 + shortcut 7 + llm_provider 5 = 37；`main.py:41` `/health` |
| MCP 路由 | 2（`GET /mcp/sse`、`POST /mcp/message`） | `mcp/server.py:129,148` |
| 数据表 | 7 | chunks / conversations / messages / documents / knowledge_bases / llm_configs / shortcuts |
| 前端组件 / 页面 | 8 个组件 + 9 个页面（共 17 个 .vue） | `frontend/src/components`、`frontend/src/views` |

## 解析与分块

- 解析格式 6 种：`pdf/docx/csv/txt/md/doc` —— `core/document_parser.py:34` `PARSERS` 字典；`ALLOWED_EXTENSIONS` 见 `config.py:46`。
- 单文件上限 100 MB —— `config.py:45` `MAX_UPLOAD_SIZE_MB = 100`。
- 编码回退：chardet 探测 + 逐个尝试候选编码，列表含 `gb18030 / gbk / big5 / cp936` —— `core/document_parser.py:248-273`。
- 分块策略 10 种 —— `core/chunker.py:14` `ChunkMethod = Literal["naive","general","book","paper","resume","table","qa","intelligent","parent_child","recursive"]`；工厂分派 `chunker.py:764-794`。
- parent_child：子块 512 / overlap 64，父块 1536 / overlap 0 —— `chunker.py:156-163`。
- 检索用子块，命中后回取父块作为上下文 —— `core/retriever.py:96-99`。
- 表格分块：CSV 每行独立成块 + 每块注入表头 —— `chunker.py:415-437`（`row_with_context = f"表格数据（列：{', '.join(headers)}）\n{line}"`，`:425`）。
- 智能分块：`min_chunk_size=50` + `_merge_small_sections` 自动合并过小章节 —— `chunker.py:193-196`、`chunker.py:156-175`（文档版）。

### 分块优化前后（`docs/chunking-optimization-results.md`）

智能分块（`intelligent.md`）：

| 指标 | 前 | 后 | 变化 | 行号 |
|---|---|---|---|---|
| 分块数 | 20 | 11 | −45% | :98-104 |
| 过小分块（<50 tokens） | 12 | 5 | −58% | :103 |
| 最小块 | 8 tokens | 31 tokens | +287% | :101 |
| 平均块长 | ~150 tokens | ~270 tokens | +80% | :102 |

表格分块（`table.csv`）：分块数 2 → 30（+1400%），平均 ~590 → ~65 tokens，消除切断数据行（:80-86）。

## 向量与检索

- BGE-M3 单次前向同时产出稠密 + 稀疏 —— `core/embedder.py:75-87`（`return_dense=True, return_sparse=True`，dense 形状 `(n, 1024)`）。
- 默认 `BAAI/bge-m3`（`config.py:49`）、`BAAI/bge-reranker-v2-m3`（`config.py:57`）、`EMBEDDING_DEVICE = "cpu"`（`config.py:50`）。
- 混合检索 RRF：dense 与 sparse 各取 `top_k * 2` 候选，RRF 常数 `k = 60`，融合后取 top_k —— `core/vector_store.py:167-215`。
- 稀疏检索是 BM25 风格的 token 重叠打分 —— `vector_store.py:126-152`。
- 重排：Cross-Encoder 把召回 20 精排到 5 —— `config.py:60-61`（`RETRIEVAL_TOP_K=20`、`RERANK_TOP_N=5`）；`core/reranker.py:53-83`；重排模型不可用时降级为保序返回（`reranker.py:69-70`）。
- 三级降级 Milvus Server（`MILVUS_HOST` 非本地时）→ Milvus Lite（文件）→ NumPy 内存库 —— `vector_store.py:264-286`。
- 检索管线顺序：embed（dense+sparse）→ hybrid_search → Cross-Encoder rerank → 回取父块 → 置信度 —— `core/retriever.py:41-124`。
- 置信度：`0.6 × 最高分 + 0.4 × 平均分`，阈值 0.3，标签 very_low/low/medium/high —— `core/confidence.py`、`config.py:62`。

### 混合检索实测（`docs/hybrid-search-summary.md`）

问题：`table.csv` 中确实存在「智能吸顶灯」，测试问答查不出（:5）。

根因：只用稠密向量，"智能吸顶灯"与"门窗传感器"等语义意外相近，缺关键词精确匹配（:7-11）。

查询「智能吸顶灯」：

| 方式 | Top-1 | 分数 |
|---|---|---|
| Dense only | 智能吸顶灯 ✓ | 0.8336 |
| Sparse only | 智能吸顶灯 ✓ | 0.2658 |
| Hybrid (RRF) | 智能吸顶灯 ✓ | 0.0328 |

查询「照明设备」（:96-104）：

| 排名 | Dense | Sparse | Hybrid |
|---|---|---|---|
| 1 | 智能灯带 | 智能筒灯 | 智能筒灯 ✓ |
| 2 | 智能筒灯 | 智能吸顶灯 | 智能灯带 ✓ |
| 3 | 智能吸顶灯 | 智能灯带 | 智能吸顶灯 ✓ |

→ 单路 Top-3 各漏 1 条，混合检索 Top-3 收齐。

**代价（必须主动说）**：检索时间 +30~50%，存储 +10~20% —— `docs/hybrid-search-summary.md:128-132`。

## 问答链路与可观测

- 检索增强问答 API：`POST /api/v1/chat`（流式 SSE 或非流式）—— `api/v1/chat.py:28`。
- 多轮：取最近 6 条历史消息进上下文 —— `chat.py:49-55`。
- 流式 SSE 事件：`metadata` / `text_chunk` / `done`，结束后 `complete`，异常 `error`；结构化 Agent 走 `agent_result` —— `chat.py:148,149,165,186,189`、`core/agent_router.py:150-179`。
- 意图识别 5 类：`text / chart / report / webpage / data_table`，非法值默认回落 text —— `agents/base_agent.py:29-43`。
- 4 个结构化 Agent：chart（ECharts 配置）/ report（HTML 报表）/ data_table / webpage，失败回落文本模式 —— `core/agent_router.py:21-26,93-110`。
- 答案落库：assistant 消息带 `model_used`、`confidence`、`retrieval_chunk_ids`（JSON）—— `chat.py:169-180`。
- 调试接口 `POST /api/v1/kb/{kb_id}/test-chat` —— `api/v1/document.py:555`：
  - 查询长度 > 50 字符触发 LLM 改写 —— `document.py:585-601`（`if len(request.query) > 50`，`:585`）。
  - `metrics` 7 项：`retrieval_time_ms / rerank_time_ms / generation_time_ms / total_time_ms / input_tokens / output_tokens / total_tokens` —— `document.py:704-712`。
  - `debug_data` 字段（含 metrics 计）：`rewritten_query / retrieval_results / reranked_results / selected_chunks / context_length / prompt_template / answer / confidence / confidence_label / sources / metrics` = 11 个 + 初始声明（`document.py:570-580`）。**简历别写死"12 个"**，写"链路中间态字段"或直接省去。
  - Top-5 命中 chunk 的 `chunk_id` 一并返回（`:620-630`），可复盘。

## Agent 路由与 LLM 接入

- LLM 统一走 LiteLLM（`core/llm_manager.py:6,100`），`litellm.drop_params = True`（`llm_manager.py:15`）。
- provider 前缀映射 10 项 —— `llm_manager.py:19-32`。
- **注意**：`llm_manager.py:72` 有 `api_key = config.api_key_encrypted  # TODO: decrypt` —— API Key 实际未加密存储。**不要声称实现了密钥加密**。

## MCP

- JSON-RPC over SSE，协议版本 `2024-11-05` —— `mcp/server.py:51`。
- 支持 `initialize` / `notifications/initialized` / `tools/list` / `tools/call` —— `mcp/server.py:31-40`。
- 2 个工具：`list_knowledge_bases`、`rag_chat`（rag_chat 支持 kb_id、history、top_k、enable_agent 参数）—— `mcp/tools.py:116-168`。

## 部署

- `docker-compose.yml` 编排 7 个服务：`postgres:16-alpine`、`redis:7-alpine`、`etcd:v3.5.16`、`minio`、`milvusdb/milvus:v2.4.17`、`backend`、`frontend`。
- 另有 `docker-compose.lite.yml`（本地轻量）；`install.bat` / `start.bat` 一键脚本；前端 `nginx.conf` 反代。
- 默认本地开发：SQLite + Milvus Lite（`config.py:31,38`）。

## 验证脚本（不是单元测试）

仓库根只有 3 个打印式验证脚本：`test_bge_m3_hybrid.py`、`test_hybrid_search.py`、`test-chunking-optimization.sh`。**无 pytest、无断言、无覆盖率**。

## 简历里必须守住的三个边界

1. 没有单元测试框架 → 只能写"3 个验证脚本"，不能写覆盖率。
2. Milvus 路径实际只跑稠密：`vector_store.py:388` 注释「Milvus Lite doesn't support sparse vectors well”，稀疏 + RRF 只在 NumPy 兜底层生效 → 被问"生产用哪条路径"要如实说。
3. `test-chat` 的 `rerank_score` 是复制 `hybrid_score` 的（`document.py:632-645`），`sparse_score`/`rerank_score` 默认 None，`rerank_time_ms` 不代表真实重排耗时 → 不能拿它当重排耗时指标。
