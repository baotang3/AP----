# -*- coding: utf-8 -*-
"""简历「实习经历 + 项目经历」重建器（参数化压缩版）。

用法：
  python build_resume.py <dst.docx> [--scale 精简系数]

先把原始 dict 合并成整段文本，再按 chunk 规则压缩到目标字数，最后拆成
(加粗标签, 正文) 并写回原文档格式。
"""
import copy
import re
import sys

from docx import Document

SRC = r"C:\AP项目文档\简历\郭佳欣_AI应用开发简历_终版.docx"

INTERN_TITLE = "勤栈AI+（D.Orbiter）AI 协同软件开发平台：Agent 工作台 + 六阶段 AI 研发流水线"

# (标签, 正文块列表) —— 正文块会先合并，再整体压缩
INTERN = [
    ("Agent 工作台后端：",
     "基于 FastAPI + Claude Agent SDK 搭建，用 ClaudeSDKClient 长连接接入文件分析、代码执行与"
     "产出物生成；对话运行与 Agent 执行解耦为「独立 producer + 订阅者」，RunManager 维护 "
     "running / completed / failed / cancelled 四态，支撑 71 个 REST 端点、15 张表。"),
    ("长任务与断点恢复：",
     "事件带单调 seq 写入环形缓冲，以 1 万事件 / 8 MiB 双上限支持 after_seq 断点回放，超限降级"
     "实时；订阅者积压超 2000 主动断流、由重连回放补齐，同一对话并发提交直接拒绝。"),
    ("工具权限与沙箱安全：",
     "用 can_use_tool 统一收口工具授权，刻意不用会绕过回调的 allowed_tools 白名单；30 条正则"
     "拦截递归删除、系统路径写入、提权、fork bomb 等命令；路径校验先 realpath 工作区根再拼接，"
     "避免文件未创建时误判越界；Docker 沙箱以 cap_drop=ALL、no-new-privileges、512M 内存、"
     "非 root 运行。"),
    ("技能体系与产出物归因：",
     "技能做成项目级 + 注册中心双轨（zip 包 + SKILL.md），上传侧拦 Zip Slip、符号链接、重复项"
     "并限解压总量与文件数，注册中心走 pending / approved / rejected 状态机且未审核禁止安装；"
     "产出物用 watchdog 监听，Write / Edit 走白名单归因、Bash 走 mtime_ns 快照差集补建。"),
    ("六阶段流水线（方案设计 + 交互原型）：",
     "参与「AI 访谈 → 业务流程 → 业务需求 → 原型 → 数据库 → 低代码」的流水线方案设计与技术选型，"
     "并实现纯前端原型（Vue 3 + Tailwind，localStorage、本地 mock 推理）：以产出物作阶段间上下文"
     "契约，对已有产物做意图识别与定向 patch 增量修改。"),
]

RAG = [
    ("混合检索（核心攻坚）：",
     "从「表格里明明有、问答却查不出」定位到根因是只用稠密向量——「智能吸顶灯」的语义向量与"
     "「门窗传感器」更近而被前置，缺关键词精确匹配；补 BGE-M3 稀疏向量后按 RRF（k=60）融合，"
     "类目查询「照明设备」下单路 Top-3 各漏 1 条，融合后收齐全部正确结果。"),
    ("嵌入选型与两段式检索：",
     "对比 bge-large-zh 等方案后选 BGE-M3（单次前向产出 1024 维稠密 + 稀疏，公开评测 MIRACL "
     "nDCG@10 稠密 69.2 / 稀疏 53.9）；查询侧用 Cross-Encoder 把召回 20 精排至 5；向量库做 "
     "Milvus Server → Milvus Lite → NumPy 三级降级。"),
    ("解析与分块：",
     "统一解析 6 种格式（PyMuPDF / python-docx / 原生），配 chardet 与 gb18030、gbk、big5、"
     "cp936 回退；实现 10 种分块策略按文档类型分派，parent_child 以子块 512 / 父块 1536 双层"
     "建关联（子块检索、命中回取父块补上下文）。"),
    ("切分质量优化：",
     "以召回与重排反馈定位切分问题：智能分块加 min_chunk_size=50 并合并过小章节，分块数 "
     "20 → 11（−45%）、过小分块 12 → 5（−58%）、最小块 8 → 31 tokens（+287%）；表格分块 "
     "2 → 30 块，消除数据行被切断。"),
    ("链路可观测与流式问答：",
     "测试问答接口输出链路中间态字段与 7 项指标（检索 / 重排 / 生成 / 总耗时、输入 / 输出 / "
     "总 Token），超 50 字查询自动 LLM 改写；问答为 SSE 流式，意图识别 5 类并路由 chart / "
     "report / data_table / webpage 四个 Agent。"),
]

# ------------------------------------------------------------ 压缩规则
# 每条规则：正则 -> 替换。按顺序应用，命中即替换。
RULES = [
    # 无信息量的连接与修饰
    (r"统一收口在", "走"),
    (r"权限回调", "回调"),
    (r"独立 producer 任务 \+ 订阅者", "独立 producer + 订阅者"),
    (r"队列积压超", "积压超"),
    (r"并实现纯前端原型", "并实现纯前端原型"),
    (r"流水线的方案设计与技术选型", "流水线方案设计与技术选型"),
    (r"以产出物作阶段间上下文契约", "以产出物作阶段间上下文契约"),
    (r"对已有产物做意图识别与定向 patch 增量修改，避免整段重生成",
     "对已有产物做意图识别与定向 patch 增量修改"),
    (r"并设解压总量与文件数上限、SHA-256 校验", "并限解压总量 / 文件数、校验 SHA-256"),
    (r"注册中心走 pending / approved / rejected 审核状态机，未审核通过禁止安装",
     "注册中心走审核状态机（pending / approved / rejected），未审核禁止安装"),
    (r"监听工作空间，对 Write / Edit 走白名单归因，对 Bash 改用执行前后 mtime_ns 快照差集补建产出物，并把 Artifact 关联到具体 run 与文件，支持产出物溯源",
     "监听工作空间：Write / Edit 走白名单归因，Bash 改用执行前后 mtime_ns 快照差集补建，"
     "Artifact 关联到具体 run 与文件"),
    (r"等危险命令", "等命令"),
    (r"路径校验先 realpath 工作区根再拼接，避免文件未创建时把合法路径误判越界",
     "路径校验先 realpath 工作区根再拼接，避免新建文件被误判越界"),
    # RAG
    (r"定位到根因是只用稠密向量", "定位根因是只用稠密向量"),
    (r"更近而被前置、缺关键词匹配", "更近而被前置，缺关键词匹配"),
    (r"公开评测 MIRACL nDCG@10 稠密 69.2 / 稀疏 53.9，作选型依据",
     "公开评测 MIRACL nDCG@10 稠密 69.2 / 稀疏 53.9"),
    (r"查询侧用 Cross-Encoder 把召回 20 精排至 5", "Cross-Encoder 把召回 20 精排至 5"),
    (r"统一解析 6 种格式（PyMuPDF / python-docx / 原生）并配 chardet 与 gb18030、gbk、big5、cp936 编码回退",
     "解析 6 种格式（PyMuPDF / python-docx / 原生），配 chardet 与 gb18030 / gbk / big5 / cp936 回退"),
    (r"双层建关联（子块检索、命中回取父块补上下文），表格分块把 CSV 每行独立成块并注入表头",
     "双层建关联（子块检索、命中回取父块补上下文）；CSV 每行独立成块并注入表头"),
    (r"以召回与重排反馈定位切分问题：智能分块加 min_chunk_size=50 并自动合并过小章节，分块数 20 → 11（−45%）、过小分块 12 → 5（−58%）、最小块 8 → 31 tokens（+287%）；表格分块 2 → 30 块，消除数据行被切断",
     "以召回与重排反馈定位切分：智能分块加 min_chunk_size=50 并合并过小章节，分块数 20 → 11"
     "（−45%）、过小分块 12 → 5（−58%）、最小块 8 → 31 tokens（+287%）；表格分块 2 → 30 块，"
     "消除数据行被切断"),
    (r"测试问答接口输出链路中间态字段与 7 项指标（检索 / 重排 / 生成 / 总耗时、输入 / 输出 / 总 Token），超 50 字查询自动 LLM 改写，命中 chunk_id 随答案落库可复盘",
     "测试问答接口输出链路中间态与 7 项指标（检索 / 重排 / 生成 / 总耗时、输入 / 输出 / 总 Token），"
     "超 50 字查询自动 LLM 改写，命中 chunk_id 随答案落库"),
    (r"问答链路为 SSE 流式，意图识别 5 类并路由 chart / report / data_table / webpage 四个 Agent，失败回落文本模式",
     "问答为 SSE 流式，意图识别 5 类并路由 chart / report / data_table / webpage 四个 Agent，"
     "失败回落文本"),
    (r"用 LiteLLM 统一接入 10 类 provider", "LiteLLM 统一接入 10 类 provider"),
    (r"实现 MCP Server（JSON-RPC 2.0 over SSE，协议 2024-11-05）暴露 2 个工具供外部 Agent 调用",
     "MCP Server（JSON-RPC 2.0 over SSE，协议 2024-11-05）暴露 2 个工具供外部 Agent 调用"),
    (r"独立完成后端、前端与私有化部署（46 个 Python 文件、37 个接口、7 张表、17 个 Vue 组件，docker-compose 编排 PostgreSQL / Redis / Milvus / MinIO / etcd）",
     "独立完成后端、前端与私有化部署（46 个 Python 文件、37 个接口、7 张表、17 个 Vue 组件，"
     "docker-compose 编排 PostgreSQL / Redis / Milvus / MinIO / etcd）"),
]


def smart_cut(text, limit):
    """按语义边界截断，避免留下半句话。"""
    if len(text) <= limit:
        return text
    if limit <= 0:
        return ""
    win = text[: limit + 1]
    for mark in ("。", "；", "）"):
        i = win.rfind(mark)
        if i >= limit - 12:
            return text[: i + 1]
    i = max(win.rfind("，"), win.rfind("、"))
    if i >= limit - 8:
        return text[:i] + "。"
    return text[:limit] + "。"


def compress(text):
    """应用规则化的文字收紧（去冗余连接词、统一术语）。"""
    out = text
    for pat, rep in RULES:
        out = re.sub(pat, rep, out)
    return out


# ------------------------------------------------------------ 写入
def _normalize_pairs(pairs):
    if isinstance(pairs, tuple):
        return [(pairs[0], True), (pairs[1], False)]
    if not pairs:
        return []
    first = pairs[0]
    if isinstance(first, tuple):
        return list(pairs)
    if isinstance(first, str):
        return [(t, True) for t in pairs]
    raise TypeError(f"无法识别的内容形状: {pairs!r}")


def set_rich(par, pairs):
    pairs = _normalize_pairs(pairs)
    runs = par.runs
    if not runs:
        raise RuntimeError("段落没有 run")
    body_tpl = next((r for r in runs if r.bold is not True), runs[-1])
    label_tpl = runs[0]
    for r in runs:
        r._element.getparent().remove(r._element)
    for _t, bold in pairs:
        par._element.append(copy.deepcopy((label_tpl if bold else body_tpl)._element))
    for r, (text, bold) in zip(par.runs, pairs):
        r.text = text
        r.bold = bold


def tighten(par, after_pt=0.0, line=1.06, before_pt=0.0):
    """压缩段落间距与行距：List Bullet 样式自带的大段间距会白占版面。"""
    from docx.shared import Pt

    pf = par.paragraph_format
    pf.space_before = Pt(before_pt)
    pf.space_after = Pt(after_pt)
    pf.line_spacing = line


def clone_paragraph_after(par, pairs):
    from docx.text.paragraph import Paragraph

    new_el = copy.deepcopy(par._element)
    par._element.addnext(new_el)
    new_par = Paragraph(new_el, par._parent)
    set_rich(new_par, pairs)
    return new_par


def insert_paragraphs_after(par, contents):
    """按顺序在 par 后插入多个段落，返回新插入段落的列表。"""
    anchor = par
    created = []
    for pairs in contents:
        anchor = clone_paragraph_after(anchor, pairs)
        created.append(anchor)
    return created


def build(dst, report=False, after_pt=0.0, line=0.95, drop_limit=0,
          n_intern=None, n_rag=None, compact=True, drop_self_eval=True, scale=1.0,
          cut=True):
    """写出版简历。

    cut=False 时不做语义截断，只按 RULES 收紧措辞（保证每句完整）。
    """
    doc = Document(SRC)
    paras = doc.paragraphs

    set_rich(paras[8], [(INTERN_TITLE, True)])

    def prep(items, limit):
        out = []
        for label, body in items:
            if label == "__DROP__" or not body:
                continue
            if drop_limit and len(label) + len(body) > drop_limit:
                continue
            body = compress(body)
            if cut and scale < 1.0:
                body = smart_cut(body, int(len(body) * scale))
            out.append((label, body))
        return out[:limit] if limit else out

    # 段落池：先按原有段落改写，不足或多余的段落再插入 / 删除
    def apply_block(txt, slots, drop_after):
        for i, par in enumerate(slots):
            if i < len(txt):
                set_rich(par, txt[i])
                tighten(par, after_pt=after_pt, line=line)
            else:
                par._element.getparent().remove(par._element)
        anchor = slots[min(len(txt), len(slots)) - 1]
        extra = insert_paragraphs_after(anchor, txt[len(slots):])
        for par in extra:
            tighten(par, after_pt=after_pt, line=line)
        # 删除原「成果」行等多余段落
        for par in drop_after:
            par._element.getparent().remove(par._element)

    if compact:
        from docx.shared import Pt

        # 1) 主标题：20.5pt -> 18pt，压缩下方留白
        for r in paras[0].runs:
            r.font.size = Pt(18)
        paras[0].paragraph_format.space_after = Pt(0)
        paras[1].paragraph_format.space_after = Pt(0)
        paras[2].paragraph_format.space_after = Pt(2)
        # 2) 节标题：11pt -> 10pt，前后间距收紧
        for i in (3, 6, 15, 20, 25):
            for r in paras[i].runs:
                r.font.size = Pt(10)
            paras[i].paragraph_format.space_before = Pt(3)
            paras[i].paragraph_format.space_after = Pt(1)
        # 3) 教育背景 / 技能：收紧行距与段后距
        for i in (4, 5, 21, 22, 23, 24):
            paras[i].paragraph_format.space_after = Pt(0)
            paras[i].paragraph_format.line_spacing = 1.0
        # 4) 「自我评价」与正文内容重复，整段移除，把版面让给经历
        if drop_self_eval:
            for p in paras[-2:]:
                p._element.getparent().remove(p._element)

    intern_txt = prep(INTERN, n_intern)
    intern_slots = [paras[i] for i in range(9, 13)]
    apply_block(intern_txt, intern_slots, [])

    rag_txt = prep(RAG, n_rag)
    rag_slots = [paras[i] for i in range(16, 21)]
    apply_block(rag_txt, rag_slots, [paras[21]])  # 原「成果」行内容已并入上一条

    doc.save(dst)

    if report:
        total = 0
        for label, body in intern_txt + rag_txt:
            total += len(label) + len(body)
            print(f"{len(label) + len(body):5d}  {label}{body[:22]}...")
        print(f"TOTAL chars = {total}  (intern={len(intern_txt)}, rag={len(rag_txt)})")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("dst", nargs="?", default=r"C:\AP项目文档\简历\_试排_v1.docx")
    ap.add_argument("--drop-limit", type=int, default=0,
                    help="字符数超过该值的 bullet 自动舍弃，用于压回单页")
    args = ap.parse_args()
    build(args.dst, report=True, drop_limit=args.drop_limit)
