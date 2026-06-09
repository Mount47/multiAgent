# Agentic Loop 工程设计问答

本文用于把 Agent 项目从“调用大模型 API”讲深到“Agent Infra / AgentOps 系统设计”。重点不是照抄某个框架，而是建立一套判断标准：一个成熟 Agent 系统通常包含 Agentic Loop、工具注册、上下文管理、记忆、权限控制、错误恢复、可观测性、人工确认和评测闭环。

## 1. Agentic Loop 是怎么设计的？

Agentic Loop 不是简单的 `while True -> LLM -> tool -> LLM`。成熟设计通常会把一次 Agent 执行拆成几个明确阶段：

1. 输入归一化：接收用户任务、历史状态、系统约束、可用工具、外部资料。
2. 上下文构造：将 system prompt、developer 指令、任务、短期记忆、长期记忆、工具定义和历史轨迹组合成模型输入。
3. 模型决策：模型输出下一步动作，可能是自然语言回复、工具调用、计划更新、等待用户确认或结束。
4. 工具执行：系统根据工具名、参数、权限、预算和安全策略执行工具。
5. 结果回填：工具结果进入执行轨迹，并被压缩后加入下一轮上下文。
6. 状态推进：根据模型输出或外部规则更新 task state。
7. 终止判断：达到目标、用户中断、最大步数、预算耗尽、错误不可恢复或人工拒绝。

在当前项目中，对应实现主要是：

- `src/orchestration/state_machine.py`：用有限状态机控制需求分析、架构设计、编码、测试、评审、修订。
- `src/orchestration/selector.py`：根据上一条消息推进状态，选择下一个 Agent。
- `src/orchestration/team_builder.py`：基于 AutoGen `SelectorGroupChat` 组装多 Agent 团队。
- `src/api/task_service.py`：负责任务创建、事件发布、trace、metrics、memory 注入和 HITL 检查。

面试中可以这样讲：

> 我没有让 Agent 完全自由循环，而是采用固定 Workflow + 局部自适应的设计。高层流程由 FSM 约束，避免 Agent 乱跳；每个阶段内部由对应角色 Agent 结合工具完成任务。循环有最大轮数和最大 revision 次数，防止无限迭代。

当前可改进点：

- 将状态机 checkpoint 持久化，使任务崩溃后可从某个状态恢复。
- 区分 fixed workflow 和 autonomous planning：简单任务走固定流程，复杂任务先规划再执行。
- 将每一步 action 抽象成统一的 `StepRecord`，包含输入、输出、工具调用、状态变更和错误。

## 2. 模型什么时候思考，什么时候调用工具？

模型是否调用工具，通常由三层机制决定：

1. Prompt 约束：告诉模型哪些场景必须调用工具，例如读文件前不能凭空猜测、执行测试必须调用 test runner。
2. 工具 schema：把可用工具以结构化定义暴露给模型，模型输出工具名和参数。
3. Runtime policy：即使模型想调用工具，系统也要做权限、参数、安全和预算校验。

成熟 Agent 系统一般会区分几类动作：

- `think/plan`：模型内部推理或生成计划，不触发外部副作用。
- `read`：读取文件、检索记忆、搜索资料。
- `write`：修改文件、写数据库、创建任务。
- `execute`：运行代码、测试、命令。
- `ask_user`：需要人工确认或补充信息。
- `finish`：产出最终结果。

在当前项目中，工具主要通过 AutoGen Agent 的工具能力和 `src/tools/registry.py` 按角色注册。例如 Coder 可以读写文件、执行代码、安装依赖、访问 memory；Tester 可以执行测试；Architect 可以搜索 memory。

面试中可以这样讲：

> 我把模型决策和工具执行分开。模型只负责选择意图和参数，真正的执行由 runtime 统一处理。这样可以在工具层做权限控制、审计、超时、错误捕获和结果脱敏。

当前可改进点：

- 给工具调用增加统一 `ToolCallRequest` 和 `ToolCallResult` 数据结构。
- 引入工具调用前 hook：校验角色、路径、参数、预算、是否需要人工确认。
- 引入工具调用后 hook：记录 trace、脱敏输出、压缩结果、触发重试。

## 3. 工具结果如何回填上下文？

工具结果不能原样无限塞回上下文，否则很快爆炸。成熟做法一般分三层：

1. 原始结果：完整保存到持久化存储或 trace 中，便于审计和复盘。
2. 可读摘要：提取关键字段，放入下一轮模型上下文。
3. Evidence Pack：把多个工具结果整理成结构化证据包，供模型判断下一步。

例如一次测试工具结果可以保存为：

```json
{
  "tool": "run_tests",
  "success": false,
  "duration_ms": 1200,
  "summary": "3 tests failed, 12 passed",
  "evidence": [
    "test_user_login failed: expected 200 got 401",
    "test_token_refresh failed: missing refresh_token"
  ],
  "raw_ref": "trace://task_id/tool_call_id"
}
```

当前项目中，`src/observability/tool_observer.py` 和 `src/observability/tracer.py` 已经记录工具输入、输出、耗时、成功失败和 traceback；`src/api/task_service.py` 会把工具事件发布到 WebSocket，并写入 task event。

面试中可以这样讲：

> 工具结果有两种用途：给下一轮 Agent 决策，以及给人审计。给模型的不一定是完整 stdout，而是压缩后的摘要；完整结果进入 trace 和 event store。这样既能避免上下文膨胀，也能保留可追溯性。

当前可改进点：

- 对长输出做结构化压缩，例如 pytest 只保留失败用例、错误栈顶和统计信息。
- 为工具结果保存 `raw_ref`，上下文只放摘要，需要时再按引用取回。
- 对敏感输出做脱敏，如 API key、路径、环境变量。

## 4. 多轮执行如何避免上下文爆炸？

上下文爆炸通常来自四类内容：完整对话历史、长工具输出、大文件内容、重复 RAG 结果。成熟系统会采用分层上下文：

- 短期上下文：最近几轮高价值消息。
- 工作记忆：当前任务目标、约束、计划、已完成步骤、未解决问题。
- 证据包：工具结果摘要、文件片段、测试失败摘要。
- 长期记忆：跨任务经验、代码片段、设计决策。
- 原始日志：不进入模型上下文，只保存在 trace/event store。

常见策略：

1. Sliding window：只保留最近 N 轮。
2. Summary memory：定期把历史压缩成摘要。
3. Retrieval memory：需要时按 query 检索相关历史。
4. Reference instead of content：上下文放引用，不放完整内容。
5. Budget-aware packing：按 token 预算决定哪些内容进入上下文。

当前项目已经有 `src/memory/store.py` 和任务启动前的 memory retrieval，但还没有完整的上下文预算管理。

面试中可以这样讲：

> 我不会把所有历史都塞给模型。执行轨迹完整保存在 trace 中，模型上下文只保留近期关键消息、当前状态、压缩后的工具证据和检索到的少量相关记忆。这样能控制 token 成本，也能减少模型被旧信息干扰。

当前可改进点：

- 实现 `ContextBuilder`：统一负责 prompt packing、token 预算和证据选择。
- 给每类上下文设置预算，例如 system 20%、task 10%、recent history 30%、evidence 30%、memory 10%。
- 对历史做阶段摘要：requirements summary、architecture summary、test summary、review summary。

## 5. 记忆机制如何设计？

Agent 记忆不应该只是向量库。成熟设计至少区分四类记忆：

- Episodic Memory：一次任务的执行过程、关键决策、错误和结果。
- Semantic Memory：通用知识、项目规范、架构原则。
- Procedural Memory：如何执行某类任务的流程和经验。
- Working Memory：当前任务的目标、计划、状态和待办。

写入记忆时需要考虑：

- 什么值得记：成功经验、失败原因、架构决策、可复用代码、用户偏好。
- 什么时候写：阶段完成后、任务结束后、人工确认后。
- 如何检索：按任务描述、代码模块、错误信息、工具名、标签检索。
- 如何遗忘：过期、低质量、重复、错误记忆需要淘汰或降权。

当前项目中，`MemoryStore` 使用 ChromaDB 存 conversations 和 code snippets；`TaskService` 会在任务开始前检索相关历史，并在 Agent 输出后自动保存部分内容。

面试中可以这样讲：

> 我把 memory 设计成辅助上下文，而不是事实来源。检索结果会作为 relevant context 注入，但模型仍需要结合当前代码和工具结果验证。记忆写入也要分阶段和分类型，否则会污染后续任务。

当前可改进点：

- 给 memory 增加质量分、来源、时间、任务类型和有效期。
- 保存阶段级摘要，而不是直接保存长文本。
- 检索后生成 Evidence Pack，并标注来源和置信度。

## 6. Skill 是怎么被匹配和执行的？

Skill 的核心是把可复用能力从大 prompt 中拆出来。成熟 Skill 系统通常采用渐进式披露：

1. Registry 层只暴露 skill 名称、描述和入口路径。
2. 路由层根据用户意图匹配可能的 skill。
3. 命中后才读取 `SKILL.md`。
4. `SKILL.md` 再按需引用脚本、模板、assets、references。
5. 执行时遵守 skill 里的边界、流程和安全约束。

匹配通常不是只靠关键词，而是结合：

- 用户显式点名：例如 `$skill-creator`。
- 意图匹配：例如“创建一个 skill”命中 skill-creator。
- 任务类型：例如“生成图片资产”命中 imagegen。
- 负向边界：例如安装 skill 不应该命中创建 skill。

面试中可以这样讲：

> Skill 的价值是减少上下文常驻负担。系统不会一开始加载所有技能全文，只加载可路由的元信息。真正命中后再读取详细说明和引用文件，这就是渐进式披露。正确性依赖于 skill description 的边界清晰度。

当前项目可借鉴的设计：

- 将常见开发任务沉淀成 skills，例如“写测试”“修复 CI”“生成 API 路由”“分析 trace”。
- 每个 skill 规定触发条件、输入输出、可用工具和禁止行为。
- 将 skill 执行结果纳入 trace，便于复盘技能效果。

## 7. MCP 工具如何注册、调用和鉴权？

MCP 可以理解为把外部系统能力标准化暴露给 Agent 的协议层。成熟 MCP 工具体系一般包括：

- Server 注册：声明工具、资源、资源模板和能力边界。
- Tool schema：定义工具名、参数、类型、描述和返回格式。
- Client discovery：Agent runtime 拉取可用工具列表。
- Authorization：按用户、workspace、tenant、角色决定工具是否可见和可调用。
- Execution gateway：统一执行工具调用，记录审计日志和错误。

工具调用流程可以设计为：

1. Agent runtime 获取当前 session 可用 MCP server。
2. 根据权限过滤工具列表，只把允许的工具暴露给模型。
3. 模型生成工具调用请求。
4. Runtime 校验工具名、参数 schema、角色权限、资源权限和风险等级。
5. 调用 MCP server。
6. 记录 tool span、输入摘要、输出摘要、错误和耗时。
7. 将压缩后的结果回填上下文。

鉴权要覆盖：

- 用户身份：谁在调用。
- 工作区：能访问哪些 repo、文件、数据库。
- 工具级权限：能不能执行命令、写文件、访问网络。
- 参数级权限：能不能写某个路径、删除某个资源。
- 风险级别：高风险操作需要人工确认。

面试中可以这样讲：

> MCP 工具不是简单注册给模型就完了。工具暴露前要经过权限过滤，调用时要经过 schema 校验和 policy 校验，执行后要进入审计链路。模型只看到自己当前会话被允许使用的工具。

当前项目可改进点：

- 把 `src/tools/registry.py` 升级成 policy-aware registry。
- 引入 `ToolPolicy`：allowed_roles、read_paths、write_paths、network、requires_approval、timeout。
- 对危险工具如 install dependency、execute code 增加人工确认或沙箱限制。

## 8. 权限控制和安全 hook 如何设置？

安全不能只靠 prompt。成熟 Agent 系统需要在 runtime 层做强约束：

- Pre-call hook：工具执行前检查权限、参数、预算、路径、命令风险。
- Post-call hook：工具执行后脱敏、截断、记录审计、更新预算。
- Human approval hook：高风险操作需要人工确认。
- Sandbox hook：执行代码或命令时进入隔离环境。
- Network hook：控制是否允许外网访问。
- Secret hook：禁止模型读取或输出敏感信息。

当前项目已有一些安全雏形：

- `write_file` 和 `read_file` 限制在 workspace 且禁止路径穿越。
- `execute_python_code` 有 30 秒 timeout。
- 工具调用有 observer，可记录失败和 traceback。

但当前执行隔离仍然偏弱，因为 Python 代码是在本机 subprocess 中运行。更成熟的做法是 Docker/gVisor 沙箱：

- 只挂载临时 workspace。
- 禁止或限制网络。
- 设置 CPU、内存、进程数、执行时间。
- 使用非 root 用户。
- 容器结束后销毁。

面试中可以这样讲：

> 我不会依赖 prompt 防止越权。Prompt 只负责引导，真正的边界在工具 runtime。每次工具调用都会经过 pre-hook，检查角色、路径、风险级别和预算；执行结果经过 post-hook 脱敏和审计；危险动作需要 HITL。

当前可改进点：

- 将代码执行迁移到 Docker sandbox。
- 增加 denylist/allowlist 命令策略。
- 对文件写入增加 diff preview 和确认机制。

## 9. 提示词规范如何约束模型行为？

Prompt 规范的目标不是让模型“听话”，而是降低系统不确定性。成熟提示词通常约束：

- 角色职责：这个 Agent 只负责什么，不负责什么。
- 输入输出格式：必须返回 JSON、Markdown、patch 或 verdict。
- 工具使用规则：什么时候必须读文件，什么时候必须跑测试。
- 终止条件：什么时候输出 `APPROVED`、`REVISE`、`FAILED`。
- 安全边界：不能泄漏 secret，不能越权操作。
- 错误处理：不确定时询问或调用工具验证。

当前项目中，角色 prompt 位于 `config/prompts/`，状态转移 guard 会解析测试和评审输出中的 verdict。例如测试 Agent 输出 `PASSED/FAILED`，Reviewer 输出 `APPROVED/REVISE`。

面试中可以这样讲：

> Prompt 不是孤立的文本，而是和状态机、guard、工具 schema 配套设计的。比如 Reviewer 的输出格式会直接影响状态机是否进入 approved 或 revision，所以我会用结构化 verdict 降低解析歧义。

当前可改进点：

- 所有关键 Agent 输出改成强 schema，例如 Pydantic model 或 JSON schema。
- 对模型输出做 parser + validator，不通过则触发修复提示。
- 为 prompt 增加版本号，记录每次任务使用的 prompt version。

## 10. 工具失败或模型输出格式错误时如何恢复？

成熟系统需要把错误分级，而不是一失败就终止：

- 可重试错误：网络超时、临时 API 错误、工具进程超时。
- 可修复错误：JSON 格式错误、缺少字段、测试失败、依赖缺失。
- 需要人工介入：权限不足、高风险操作、需求不明确。
- 不可恢复错误：预算耗尽、连续失败超过阈值、安全策略拒绝。

工具失败恢复策略：

1. 捕获错误，生成结构化 `ToolCallResult`。
2. 判断是否可重试。
3. 对可重试错误做指数退避。
4. 对可修复错误把错误摘要回填给 Agent。
5. 超过最大次数后进入 failed 或 waiting_approval。

模型格式错误恢复策略：

1. 用 parser 验证输出。
2. 如果失败，向模型发送 repair prompt，只要求修复格式，不重新做任务。
3. 如果连续失败，降级为关键词 fallback 或人工确认。
4. 将格式错误记录到 trace，作为 prompt 质量评估依据。

当前项目已有：

- `TaskService` 捕获 workflow 异常并写入 `system_error` 事件。
- `WorkflowTracer` 记录失败状态。
- guard 支持 JSON verdict 和关键词 fallback。
- 工具 observer 会记录异常、错误输出和 traceback。

面试中可以这样讲：

> 我把失败当成 Agent Loop 的一等状态处理。工具失败不会直接丢给用户，而是先结构化记录，再判断是否重试、是否让 Agent 修复、是否需要人工确认。模型输出格式错误也会走 parser validation 和 repair prompt。

当前可改进点：

- 增加统一 retry policy：按工具类型设置最大重试次数和退避策略。
- 增加 output repair pipeline：结构化输出解析失败时自动修复。
- 将失败原因分类写入 metrics，例如 `tool_timeout`、`schema_error`、`permission_denied`。

## 11. 如何把这些设计讲成项目亮点？

不要只说：

> 我做了一个多 Agent 协作写代码系统。

更好的说法是：

> 我做的是一个面向软件开发任务的 AgentOps 原型。高层用 FSM 约束多 Agent 协作流程，底层通过工具注册表控制不同角色的能力边界；每一步 Agent 输出、工具调用、状态迁移都会进入 trace 和 event stream；系统支持 memory 检索、HITL checkpoint、测试/评审驱动的 revision loop，并通过最大轮数和最大 revision 次数防止无限循环。

如果继续补强，可以进一步说：

> 后续我把代码执行迁移到 Docker sandbox，并增加 policy-aware tool registry、eval harness 和 OpenTelemetry trace。这样项目就不只是 demo，而是能体现 Agent Infra 中编排、隔离、观测、评测和恢复能力的完整闭环。

## 12. 面试追问速查

| 问题 | 回答重点 |
|------|----------|
| Agentic Loop 怎么设计？ | 输入归一化、上下文构造、模型决策、工具执行、结果回填、状态推进、终止判断 |
| 为什么不用完全自主 Agent？ | 固定 Workflow 可控、可测、可审计；复杂任务可局部引入 planning |
| 怎么防止无限循环？ | 最大轮数、最大 revision 次数、预算限制、状态机终止条件 |
| 工具失败怎么办？ | 结构化错误、重试、错误摘要回填、人工确认、失败入 trace |
| 输出格式错怎么办？ | parser validation、repair prompt、fallback、记录 schema error |
| 上下文太长怎么办？ | sliding window、summary、retrieval、evidence pack、raw_ref |
| 记忆怎么设计？ | episodic、semantic、procedural、working memory 分层 |
| Skill 怎么匹配？ | registry 元信息路由，命中后读取 SKILL.md，按需加载引用文件 |
| MCP 工具怎么鉴权？ | 工具暴露前权限过滤，调用时 schema + policy 校验，执行后审计 |
| Prompt 有什么工程规范？ | 角色职责、输出 schema、工具规则、终止条件、安全边界、错误处理 |
| 如何体现 AgentOps？ | trace、metrics、event stream、checkpoint、HITL、eval、恢复 |

## 13. 对当前项目的优先改造路线

1. 补 `ContextBuilder`：统一管理 system prompt、任务、历史、memory、tool evidence 和 token budget。
2. 补 `ToolPolicy`：角色级、路径级、风险级权限控制。
3. 补 Docker sandbox：替代本机 subprocess 执行代码。
4. 补 eval harness：固定任务集，记录 pass rate、token、耗时、revision 次数。
5. 补 output parser：关键 Agent 输出全部走 JSON schema validation。
6. 补 checkpoint resume：HITL 和失败任务可以从 DB 恢复。
7. 补 OpenTelemetry/Prometheus：让 trace 和 metrics 标准化。

这条路线能把项目从“Agent 应用 demo”推进到“Agent Infra 实习项目”，也更贴近 Agent 平台、AgentOps、LLMOps 和安全隔离方向的面试要求。
