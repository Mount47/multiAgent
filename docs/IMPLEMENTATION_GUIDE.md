# Multi-Agent 协作开发系统 - 实现指南与进度追踪

> 本文档用于跨会话参考，记录项目完整实现计划、当前进度、以及每个模块的具体实现思路。
> 每次开新对话时，请 Claude 读取此文档，继续未完成的工作。

更新时间：2026-03-16

---

## 一、简历描述（最终版本）

> 以下为优化后的简历内容，相比原版调整了措辞，突出了技术深度和量化指标。

**多 Agent 软件开发协作系统**

项目介绍：基于 Microsoft AutoGen 0.4 构建多 Agent 协作框架，设计 ProductManager、Architect、Coder、Tester、Reviewer 五种角色，通过有限状态机驱动需求分析→系统设计→代码生成→单元测试→代码评审的全自动化开发流程，支持多轮修订迭代。

- 构建 Agent Orchestration Workflow，基于 SelectorGroupChat + 自定义有限状态机（7 状态 / 8 转移 / 5 Guard 条件）实现多 Agent 协同决策与任务路由，支持最多 3 轮修订迭代与 30 轮对话上限的自动终止机制。
- 设计 Tool System，实现 7 个工具函数的角色级权限注册机制，使 Coder/Tester Agent 能安全调用代码执行（subprocess 沙箱）、文件读写（路径遍历防护）、依赖安装（命令注入防护）和自动化 pytest 测试等能力。
- 构建 Agent Memory 模块，基于 ChromaDB 向量数据库实现双集合（对话 + 代码片段）存储，通过余弦相似度检索实现跨任务长期记忆与上下文增强推理（Memory-Augmented Agent），支持 Architect/Coder 在设计与编码阶段自动检索历史方案。
- 开发可视化 Web UI（FastAPI + React + WebSocket），实现 Agent Workflow 状态图实时渲染、多 Agent 对话流实时推送、任务生命周期管理与代码生成结果展示，支持多模型供应商（Gemini/OpenAI/DeepSeek/Ollama）动态切换。
- 实现 Agent Observability 系统，包含 WorkflowTracer（调用链追踪、状态转移耗时、Token 消耗统计）和 MetricsCollector（工作流完成率、Agent 调用频次、平均耗时），通过 REST API 暴露监控数据，支持调试与性能分析。

---

## 二、模块实现进度总览

| # | 模块 | 简历要点 | 状态 | 完成度 |
|---|------|---------|------|--------|
| 1 | Agent 角色定义 | 5 种角色 + Prompt | ✅ 已完成 | 100% |
| 2 | Orchestration 状态机 | FSM + Guard + SelectorGroupChat | ✅ 已完成 | 100% |
| 3 | Tool System | 7 工具 + 角色权限注册 + 降级策略 | ✅ 已完成 | 100% |
| 4 | Memory 模块 | ChromaDB + 双集合 + 工具集成 | ✅ 已完成 | 85% |
| 5 | Web UI | Vite + React + TS + Tailwind + WebSocket | ✅ 已完成 | 95% |
| 6 | Observability | Tracer + Metrics + API | ✅ 已完成 | 90% |
| 7 | 持久化层 | SQLite + SQLAlchemy Async | ✅ 已完成 | 90% |
| 8 | 模型配置 | 4 供应商 + Factory + 热切换 | ✅ 已完成 | 100% |
| 9 | 端到端稳定性 | 健康检查 + 结构化Guard + 降级 | ✅ 已完成 | 85% |
| 10 | 测试覆盖 | 单元测试 + 集成测试 (114 passed) | ✅ 已完成 | 80% |

---

## 三、各模块详细实现状态与待办

### 模块 1：Agent 角色定义 ✅

**已完成：**
- [x] ProductManager Agent - 需求分析，结构化输出
- [x] Architect Agent - 系统设计，模块/接口定义
- [x] Coder Agent - 代码生成，工具调用，reflect_on_tool_use
- [x] Tester Agent - 测试编写与执行，pytest 集成
- [x] Reviewer Agent - 代码评审，APPROVED/REVISE 判定
- [x] AgentFactory 工厂模式 - 统一创建，模型注入
- [x] 5 个角色的 Markdown System Prompt（config/prompts/）
- [x] base.py 提供 prompt 加载工具函数

**待优化（非阻塞）：**
- [ ] **Prompt 参数化**：当前 prompt 硬编码，后续可支持模板变量注入（如项目名、语言偏好）
- [ ] **Agent 自我介绍**：在 GroupChat 开始时各 Agent 声明能力边界，帮助 Selector 更好判断

**关键文件：**
```
src/agents/base.py              # prompt 加载
src/agents/factory.py           # AgentFactory
src/agents/product_manager.py   # PM Agent
src/agents/architect.py         # 架构师 Agent
src/agents/coder.py             # 编码 Agent
src/agents/tester.py            # 测试 Agent
src/agents/reviewer.py          # 评审 Agent
config/prompts/*.md             # 角色 Prompt
```

---

### 模块 2：Orchestration 状态机 ✅

**已完成：**
- [x] WorkflowState 枚举（7 状态）
- [x] STATE_AGENT_MAP 状态→Agent 映射
- [x] 5 个 Guard 函数（always, tests_passed, tests_failed, review_approved, review_revision_needed）
- [x] WorkflowStateMachine 类（from_yaml 加载、advance 推进、reset 重置）
- [x] Transition 数据类（source, target, guard）
- [x] max_rounds=30 防无限循环
- [x] max_revisions=3 防无限修订
- [x] create_workflow_selector() 桥接 AutoGen SelectorGroupChat
- [x] build_team() 异步组装团队
- [x] workflows.yaml 配置文件（声明式工作流定义）

**待优化：**
- [ ] **结构化输出判定**：当前 Guard 基于关键字匹配（如检测 "APPROVED"），应改为 JSON schema 结构化输出，提高鲁棒性
- [ ] **Guard 失败回退**：当所有 Guard 都不匹配时的默认策略（当前会卡住）

**关键文件：**
```
src/orchestration/states.py         # 状态定义
src/orchestration/transitions.py    # Guard 函数
src/orchestration/state_machine.py  # FSM 核心
src/orchestration/selector.py       # AutoGen 桥接
src/orchestration/team_builder.py   # 团队组装
config/workflows.yaml               # 工作流配置
```

---

### 模块 3：Tool System ✅

**已完成：**
- [x] execute_python_code - subprocess 执行，30s 超时
- [x] write_file - 路径遍历防护（Path.name）
- [x] read_file - 工作区文件读取
- [x] run_tests - pytest 自动执行，60s 超时
- [x] install_dependency - pip install，命令注入防护（危险字符过滤）
- [x] search_memory - ChromaDB 向量检索
- [x] save_to_memory - ChromaDB 向量存储
- [x] ROLE_TOOLS 角色→工具映射注册表
- [x] get_tools_for_role() 工具分配函数
- [x] Tool 调用观测装饰器（输入/输出/耗时/成功失败/traceback）
- [x] 工具异步包装层（instrumented tools）并接入 registry

**待优化：**
- [ ] **工具调用降级**：当模型不支持 function calling 时（如部分 Ollama 模型），自动切换为 prompt-based 工具调用
- [ ] **执行沙箱增强**：当前 subprocess 无资源限制，生产环境应加 CPU/内存/磁盘限制

**关键文件：**
```
src/tools/registry.py              # 角色→工具映射
src/tools/instrumented.py          # 可观测包装工具
src/tools/code_executor.py         # 代码执行
src/tools/file_manager.py          # 文件读写
src/tools/test_runner.py           # 测试运行
src/tools/dependency_installer.py  # 依赖安装
src/tools/memory_tools.py          # 记忆工具
```

---

### 模块 4：Memory 模块 ✅（需增强）

**已完成：**
- [x] MemoryStore 类（ChromaDB 持久化存储）
- [x] 双集合：conversations + code_snippets
- [x] 余弦相似度检索（HNSW space）
- [x] search_memory 工具（供 Architect/Coder 调用）
- [x] save_to_memory 工具（供 Coder 调用）
- [x] 惰性初始化（避免未安装 chromadb 时报错）
- [x] 元数据过滤支持

**待实现：**
- [ ] **4.1 工作流阶段自动存储**：每个阶段结束后自动将产出存入 Memory
  - PM 输出 → conversations 集合（metadata: phase=requirements）
  - Architect 输出 → conversations 集合（metadata: phase=architecture）
  - Coder 输出 → code_snippets 集合（metadata: phase=coding, filename=xxx）
  - Tester 输出 → conversations 集合（metadata: phase=testing）
  - Reviewer 输出 → conversations 集合（metadata: phase=review）
  - **实现思路**：在 TaskService 的事件回调中，根据 source agent 自动调用 MemoryStore

- [ ] **4.2 跨任务上下文检索**：新任务开始时自动检索相关历史任务
  - **实现思路**：在 PM 阶段前，用任务描述做向量检索，注入 system prompt 作为参考

- [ ] **4.3 Memory 管理 API**：通过 REST API 查看/清理/导出 Memory 内容
  - GET /api/memory/search?q=xxx
  - DELETE /api/memory/collection/{name}
  - GET /api/memory/stats

**关键文件：**
```
src/memory/store.py         # MemoryStore 核心
src/tools/memory_tools.py   # Agent 调用入口
```

---

### 模块 5：Web UI 🟡（需完善）

**已完成：**
- [x] FastAPI 后端（CORS、Lifespan、路由注册）
- [x] REST API 路由（tasks CRUD, providers, workflow graph, metrics, traces）
- [x] WebSocket 实时推送（TaskWebSocketManager）
- [x] React 前端（Babel 在线编译）
- [x] SVG 工作流状态图（7 节点，8 边，动态着色）
- [x] 节点状态动画（idle/active/visited + 脉冲发光）
- [x] 实时事件流展示（按 Agent 着色）
- [x] 任务创建表单（描述 + 供应商选择）
- [x] 响应式布局（3 列 → 2 列 → 1 列）

**待实现：**
- [ ] **5.1 任务历史列表页**：展示所有历史任务，点击进入详情
  - 左侧边栏增加任务列表（GET /api/tasks）
  - 显示状态标签（queued/running/completed/failed）
  - 点击切换当前查看的任务

- [ ] **5.2 代码结果展示面板**：展示 Coder 生成的代码文件
  - 在右侧面板下方增加"Generated Code"标签页
  - 语法高亮展示（引入 Prism.js 或 Highlight.js CDN）
  - 显示 workspace/ 下生成的文件列表
  - **需要新 API**：GET /api/tasks/{task_id}/files

- [ ] **5.3 Metrics 仪表盘**：可视化展示 Observability 指标
  - 工作流完成率（饼图/进度条）
  - Agent 调用频次（柱状图）
  - 平均耗时（折线图）
  - 引入 Chart.js CDN 或 Recharts

- [ ] **5.4 Trace Timeline 视图**：可视化工作流执行时间线
  - 横向时间轴
  - 每个 State 一个色块，宽度 = 耗时
  - 显示 Token 消耗
  - **数据源**：GET /api/traces/{task_id}

- [ ] **5.5 前端工程化**（可选，低优先级）
  - 从 CDN + Babel 迁移到 Vite + React 构建
  - 组件拆分，引入 TypeScript
  - 打包输出到 static/

**关键文件：**
```
src/api/app.py                    # FastAPI 主入口
src/api/routes/tasks.py           # 任务路由
src/api/routes/workflow.py        # 工作流路由
src/api/routes/providers.py       # 模型供应商路由
src/api/schemas/tasks.py          # 数据模型
src/api/websocket/manager.py      # WebSocket 管理
src/api/task_service.py           # 任务执行服务
src/api/static/index.html         # 前端入口
src/api/static/react-app.jsx      # React 应用
```

---

### 模块 6：Observability 系统 🟡（需增强）

**已完成：**
- [x] WorkflowTracer - 工作流级别追踪
  - start_workflow / enter_state / exit_state / end_workflow
  - StateTransitionRecord（from/to/agent/duration/tokens）
- [x] MetricsCollector - 聚合指标收集
  - 工作流总数、完成数、失败数
  - 平均耗时、状态转移次数、Token 统计
  - Agent 调用频次统计
- [x] REST API 暴露（/api/metrics、/api/traces/{task_id}）
- [x] 结构化日志（time | level | module | message）
- [x] **6.2 Tool 调用链记录**
  - 装饰器自动记录输入参数（脱敏）、输出（截断）、耗时、成功/失败
  - 记录到 `TaskEvent`（source=`tool:<name>`）并写入 Trace 的 `tool_calls`
- [x] **6.3 Token 消耗精确统计**
  - 从 AutoGen stream event 的 `models_usage.prompt_tokens/completion_tokens` 提取
  - 在 Tracer/Metrics 中按 prompt/completion 分开累计并汇总
- [x] **6.5 错误追踪增强**
  - 任务异常时写入完整 `traceback` 到 `TaskEvent`（source=`system_error`）

**待实现：**
- [ ] **6.1 Prompt 日志记录**：记录每次 Agent 的完整 Prompt（system + user）
  - **实现思路**：在 AutoGen 的消息回调中拦截，写入 TaskEvent（source=system, type=prompt）
  - 包括：角色 prompt、上下文消息、工具调用结果

- [ ] **6.4 Metrics 持久化**：当前 MetricsCollector 为内存存储，重启丢失
  - **实现思路**：定期写入 SQLite（新建 metrics 表），或者在 workflow_end 时写入
  - 支持历史趋势查询

**关键文件：**
```
src/observability/tracer.py   # 工作流追踪
src/observability/metrics.py  # 指标收集
src/observability/tool_observer.py  # Tool 调用观测
src/api/task_service.py       # usage 提取 + traceback 事件写入
```

---

### 模块 7：持久化层 ✅

**已完成：**
- [x] SQLite + aiosqlite 异步数据库
- [x] TaskModel（任务表）
- [x] TaskEventModel（事件表）
- [x] TaskRepository 异步 CRUD
- [x] init_db() 自动建表
- [x] API 启动时初始化

**待优化：**
- [ ] **数据库迁移工具**：引入 Alembic 支持 schema 变更
- [ ] **产物文件索引表**：记录每个任务生成的文件列表（filename, path, size, created_at）

**关键文件：**
```
src/persistence/database.py    # 数据库连接
src/persistence/models.py      # ORM 模型
src/persistence/repository.py  # CRUD 操作
```

---

### 模块 8：模型配置 ✅

**已完成：**
- [x] 4 个供应商配置（Gemini, OpenAI, DeepSeek, Ollama）
- [x] ModelClientFactory（缓存 + 按需创建）
- [x] 按 Agent 角色分配模型（agent_models 映射）
- [x] OpenAI 兼容 API 统一抽象
- [x] 超时 + 重试配置（LLM_TIMEOUT_SECONDS, LLM_MAX_RETRIES）
- [x] DEFAULT_MODEL 环境变量 fallback

**无需改动。**

---

### 模块 9：端到端稳定性 ✅

**已完成：**
- [x] **9.1 启动前健康检查**（src/health.py）
  - 检查 workspace 目录可写、python/pip/pytest 可用、LLM API Key 已配置
  - 可选异步 LLM 可达性检测
  - CLI 启动时自动执行，critical_ok 判定是否继续
- [x] **9.2 工具调用降级策略**（src/agents/factory.py）
  - AgentFactory._supports_tools() 检测模型 function_calling 能力
  - 不支持时创建无工具 Agent + 降级 prompt 提示
- [x] **9.3 Guard 结构化输出**（src/orchestration/transitions.py）
  - _extract_json_verdict() 解析 fenced/bare JSON verdict
  - 5 个 Guard 函数优先解析 JSON，失败回退关键字匹配
  - Tester/Reviewer prompt 已更新，要求输出 JSON verdict 块
- [x] **9.5 集成测试**（tests/integration/test_workflow_e2e.py，23 cases）
  - JSON verdict 解析测试（5 cases）
  - Guard JSON + 关键字兼容测试（9 cases）
  - Happy path 全流程（keyword + JSON，2 cases）
  - Revision path（fail→revise→pass，3 cases）
  - 边界条件（max_rounds / max_revisions 强制终止，2 cases）
  - Health check + Tool degradation 测试（3 cases）

**待优化：**
- [ ] **9.4 错误恢复机制**
  - LLM API 超时/失败时的重试策略（已有 max_retries 配置，需验证生效）
  - Tool 执行失败时 Agent 可感知并尝试修复
  - 状态机卡住时的超时强制推进

**关键文件：**
```
src/health.py                              # 健康检查
src/agents/factory.py                      # 工具降级
src/orchestration/transitions.py           # 结构化 Guard
config/prompts/tester.md                   # JSON verdict prompt
config/prompts/reviewer.md                 # JSON verdict prompt
tests/integration/test_workflow_e2e.py     # 23 个集成测试
```

---

### 模块 10：测试覆盖 🟡

**已完成：**
- [x] test_state_machine.py - 状态机转移
- [x] test_transitions.py - Guard 函数
- [x] test_states.py - 状态枚举
- [x] test_metrics.py - 指标收集
- [x] test_tracer.py - 工作流追踪
- [x] test_tools.py - 工具函数
- [x] test_registry.py - 工具注册
- [x] test_models.py - 模型工厂
- [x] test_persistence.py - 数据库操作
- [x] test_tool_observer.py - Tool 调用观测装饰器

**待实现：**
- [ ] **10.1 API 路由测试**：使用 httpx AsyncClient 测试所有 REST 端点
- [ ] **10.2 WebSocket 测试**：测试事件推送和连接管理
- [ ] **10.3 集成测试（Mock LLM）**：Mock 模型响应，走完整工作流
- [ ] **10.4 Memory 模块测试**：MemoryStore 的 CRUD 和搜索
- [ ] **10.5 测试覆盖率报告**：引入 pytest-cov，目标覆盖率 > 80%

**关键文件：**
```
tests/unit/              # 已有 9 个测试文件
tests/integration/       # 待填充
```

---

## 四、推荐实施顺序

按照 **简历可展示价值** 和 **系统稳定性** 排序：

### Phase 1：核心稳定化（使系统真正可运行）
> 目标：能稳定跑通一个完整任务，可以录屏演示

| 优先级 | 任务 | 对应模块 | 预计工作量 |
|--------|------|---------|-----------|
| P0 | 9.1 启动前健康检查 | 稳定性 | 小 |
| P0 | 9.5 Mock 集成测试（happy path） | 测试 | 中 |
| P0 | 9.4 错误恢复（LLM 超时重试验证） | 稳定性 | 小 |
| P1 | 9.2 工具调用降级策略 | 稳定性 | 中 |
| P1 | 9.3 Guard 结构化输出 | 稳定性 | 中 |

### Phase 2：Observability 完善（简历亮点增强）
> 目标：完整的可观测性系统，支持排障和性能分析

| 优先级 | 任务 | 对应模块 | 预计工作量 |
|--------|------|---------|-----------|
| P0 | 6.2 Tool 调用链记录 ✅ | Observability | 中 |
| P0 | 6.3 Token 消耗精确统计 ✅ | Observability | 小 |
| P1 | 6.1 Prompt 日志记录 | Observability | 中 |
| P1 | 6.5 错误追踪增强 ✅ | Observability | 小 |
| P2 | 6.4 Metrics 持久化 | Observability | 中 |

### Phase 3：Web UI 完善（演示效果提升）
> 目标：可视化效果完整，能展示全部功能

| 优先级 | 任务 | 对应模块 | 预计工作量 |
|--------|------|---------|-----------|
| P0 | 5.1 任务历史列表 | Web UI | 中 |
| P0 | 5.2 代码结果展示 | Web UI | 中 |
| P1 | 5.4 Trace Timeline 视图 | Web UI | 大 |
| P1 | 5.3 Metrics 仪表盘 | Web UI | 大 |
| P2 | 5.5 前端工程化 | Web UI | 大 |

### Phase 4：Memory 深度集成（技术深度提升）
> 目标：真正的 Memory-Augmented Agent

| 优先级 | 任务 | 对应模块 | 预计工作量 |
|--------|------|---------|-----------|
| P0 | 4.1 工作流阶段自动存储 | Memory | 中 |
| P1 | 4.2 跨任务上下文检索 | Memory | 中 |
| P2 | 4.3 Memory 管理 API | Memory | 小 |

### Phase 5：测试与质量
> 目标：生产级代码质量

| 优先级 | 任务 | 对应模块 | 预计工作量 |
|--------|------|---------|-----------|
| P1 | 10.1 API 路由测试 | 测试 | 中 |
| P1 | 10.4 Memory 模块测试 | 测试 | 小 |
| P2 | 10.2 WebSocket 测试 | 测试 | 中 |
| P2 | 10.3 完整集成测试 | 测试 | 大 |
| P2 | 10.5 覆盖率报告 | 测试 | 小 |

---

## 五、项目架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         Entry Points                            │
│  ┌──────────────┐  ┌──────────────────────────────────────────┐ │
│  │  CLI (cli.py) │  │  API Server (FastAPI + Uvicorn)         │ │
│  │  agent-dev    │  │  agent-dev-api                          │ │
│  └──────┬───────┘  │  ┌─────────┐ ┌──────────┐ ┌──────────┐ │ │
│         │          │  │REST API │ │WebSocket │ │Static UI │ │ │
│         │          │  └────┬────┘ └────┬─────┘ └──────────┘ │ │
│         │          └───────┼───────────┼─────────────────────┘ │
│         │                  │           │                        │
│         ▼                  ▼           │                        │
│  ┌──────────────────────────────┐      │                        │
│  │     TaskService              │◄─────┘                        │
│  │  (任务生命周期管理)           │                                │
│  └──────────┬───────────────────┘                               │
│             │                                                    │
│             ▼                                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Orchestration Layer                          │   │
│  │  ┌────────────────┐  ┌───────────────┐  ┌────────────┐  │   │
│  │  │ TeamBuilder     │  │StateMachine   │  │ Selector   │  │   │
│  │  │ (组装团队)      │  │(FSM 7状态)    │  │ (桥接AGC)  │  │   │
│  │  └────────┬───────┘  └───────┬───────┘  └─────┬──────┘  │   │
│  │           │                  │                 │          │   │
│  │           ▼                  ▼                 │          │   │
│  │  ┌──────────────────────────────────────┐     │          │   │
│  │  │  SelectorGroupChat (AutoGen 0.4)     │◄────┘          │   │
│  │  │  (多 Agent 协同对话)                  │                │   │
│  │  └──────────────┬───────────────────────┘                │   │
│  └─────────────────┼────────────────────────────────────────┘   │
│                    │                                             │
│         ┌──────────┼──────────┐                                 │
│         ▼          ▼          ▼                                  │
│  ┌───────────┐ ┌────────┐ ┌──────────┐                         │
│  │   Agents  │ │ Tools  │ │ Memory   │                         │
│  ├───────────┤ ├────────┤ ├──────────┤                         │
│  │ PM        │ │ Code   │ │ ChromaDB │                         │
│  │ Architect │ │ File   │ │ 对话集合 │                         │
│  │ Coder     │ │ Test   │ │ 代码集合 │                         │
│  │ Tester    │ │ Pip    │ └──────────┘                         │
│  │ Reviewer  │ │ Memory │                                      │
│  └───────────┘ └────────┘                                      │
│                    │                                             │
│         ┌──────────┼──────────┐                                 │
│         ▼          ▼          ▼                                  │
│  ┌───────────┐ ┌────────────┐ ┌──────────────┐                 │
│  │  Models   │ │ Persistence│ │Observability │                 │
│  ├───────────┤ ├────────────┤ ├──────────────┤                 │
│  │ Gemini    │ │ SQLite     │ │ Tracer       │                 │
│  │ OpenAI    │ │ Tasks 表   │ │ Metrics      │                 │
│  │ DeepSeek  │ │ Events 表  │ │ Logger       │                 │
│  │ Ollama    │ └────────────┘ └──────────────┘                 │
│  └───────────┘                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 六、关键技术选型说明

| 技术 | 选择 | 理由 |
|------|------|------|
| Agent 框架 | AutoGen 0.4 | 微软开源，SelectorGroupChat 支持自定义选择器 |
| 编排模式 | FSM + SelectorGroupChat | 显式状态控制 > 隐式 LLM 路由，可调试可观测 |
| LLM 接口 | OpenAI-Compatible API | 统一抽象，一个 Client 适配所有供应商 |
| 向量数据库 | ChromaDB | 轻量嵌入式，无需外部服务，适合单机部署 |
| Web 框架 | FastAPI + WebSocket | 异步原生，性能好，自动 OpenAPI 文档 |
| ORM | SQLAlchemy Async | 成熟的异步 ORM，配合 aiosqlite |
| 前端 | React + SVG | CDN 引入无构建步骤，SVG 工作流图灵活可控 |
| 测试 | pytest + pytest-asyncio | Python 标准测试框架，异步测试支持 |

---

## 七、每次开新对话时的使用指南

1. **告诉 Claude**：「请读取 docs/IMPLEMENTATION_GUIDE.md，继续未完成的工作」
2. **指定具体任务**：例如「请实现 Phase 1 的 9.1 启动前健康检查」
3. **完成后更新状态**：让 Claude 将对应的 `[ ]` 改为 `[x]`，并更新顶部的完成度百分比
4. **有新想法时**：让 Claude 在对应模块的「待实现」部分添加新条目

---

## 八、文件清单速查

```
multiAgent/
├── config/
│   ├── models.yaml              # LLM 供应商配置
│   ├── workflows.yaml           # 工作流状态机配置
│   ├── settings.py              # Pydantic 环境变量
│   └── prompts/                 # Agent 系统提示词
│       ├── product_manager.md
│       ├── architect.md
│       ├── coder.md
│       ├── tester.md
│       └── reviewer.md
├── src/
│   ├── cli.py                   # CLI 入口
│   ├── agents/                  # Agent 角色实现
│   │   ├── base.py
│   │   ├── factory.py
│   │   ├── product_manager.py
│   │   ├── architect.py
│   │   ├── coder.py
│   │   ├── tester.py
│   │   └── reviewer.py
│   ├── orchestration/           # 编排层
│   │   ├── states.py
│   │   ├── transitions.py
│   │   ├── state_machine.py
│   │   ├── selector.py
│   │   └── team_builder.py
│   ├── tools/                   # 工具系统
│   │   ├── registry.py
│   │   ├── instrumented.py
│   │   ├── code_executor.py
│   │   ├── file_manager.py
│   │   ├── test_runner.py
│   │   ├── dependency_installer.py
│   │   └── memory_tools.py
│   ├── memory/                  # 记忆模块
│   │   └── store.py
│   ├── models/                  # 模型配置
│   │   ├── config.py
│   │   └── factory.py
│   ├── persistence/             # 持久化
│   │   ├── database.py
│   │   ├── models.py
│   │   └── repository.py
│   ├── observability/           # 可观测性
│   │   ├── tracer.py
│   │   ├── metrics.py
│   │   └── tool_observer.py
│   └── api/                     # Web API
│       ├── app.py
│       ├── task_service.py
│       ├── routes/
│       │   ├── tasks.py
│       │   ├── workflow.py
│       │   └── providers.py
│       ├── schemas/
│       │   └── tasks.py
│       ├── websocket/
│       │   └── manager.py
│       └── static/
│           ├── index.html
│           └── react-app.jsx
├── tests/
│   ├── unit/                    # 10 个单元测试
│   └── integration/             # 待填充
├── docs/
│   ├── IMPLEMENTATION_GUIDE.md  # 本文档
│   ├── PROJECT_STATUS.md        # 项目状态
│   └── ROADMAP_TODO.md          # 路线图
├── pyproject.toml               # 项目配置
├── .env                         # 环境变量
└── .env.example                 # 环境变量示例
```
