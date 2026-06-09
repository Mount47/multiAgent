该项目基于 AutoGen，核心原因是：它需要一个现成的 多 Agent 对话编排框架，而
  AutoGen 已经提供了 agent 抽象、group chat、工具调用、模型客户端、流式执行这些基
  础能力。项目可以把精力放在状态机、trace、memory、前端展示和评测上，而不是从零实
  现多 agent 消息循环。

  为什么用 AutoGen

  当前项目主要用了 AutoGen 这些能力：

  AssistantAgent：定义 PM / Architect / Coder / Tester / Reviewer
  SelectorGroupChat：维护共享对话区和多 agent 发言流程
  selector_func：自定义下一个发言 agent
  FunctionTool：封装工具调用
  OpenAIChatCompletionClient：接入 OpenAI-compatible 模型
  run_stream：流式输出 agent 事件

  也就是说，AutoGen 提供“多 agent 运行骨架”，项目自己补“工程治理层”：

  FSM 状态机
  Guard 判断
  工具观测
  Trace
  Memory
  WebSocket
  Benchmark
  HITL

  AutoGen 的优点

  1. 上手快：不用自己写多 agent 消息循环
  2. Agent 抽象成熟：角色、system prompt、tools 都容易配置
  3. 支持 GroupChat：天然有共享对话区
  4. 支持工具调用：Coder/Tester 可以写文件、跑测试
  5. 支持流式事件：方便接 WebSocket 和前端实时展示
  6. 模型接入方便：OpenAI-compatible provider 可复用
  7. 适合原型和实验：能快速验证多 agent workflow

  AutoGen 的缺点

  1. 对话上下文容易变长，需要自己做摘要和裁剪
  2. Agent 输出不天然可靠，仍然要 schema 校验
  3. 状态转移如果只靠文本，很容易误判
  4. 工具调用失败需要项目自己兜底
  5. Trace、评测、memory 治理不是开箱即完整
  6. 对复杂生产流程，可控性不如自己实现的严格 orchestrator
  7. 版本 API 变化可能带来维护成本

  所以 AutoGen 适合做“多 agent 协作框架”，但不等于完整生产系统。这个项目的价值在于
  在 AutoGen 外面加了一层可观测、可评测、可控制的 harness。

  该项目相比其他多 Agent 项目的优点

  1. 有显式 FSM 状态机，不是完全让 LLM 决定流程
  2. 有固定角色分工：PM → Architect → Coder → Tester → Reviewer
  3. 有 Guard 控制状态流转，测试失败会回到 revision
  4. 有工具权限隔离，不同 agent 工具不同
  5. 有 trace 和 metrics，可复盘每个状态、token、工具调用
  6. 有 WebSocket 前端，能实时观察流程
  7. 有 Memory 层，支持跨任务复用历史上下文
  8. 有 HITL 检查点，可以人工审批架构或 review

  相比很多“几个 agent 互相聊天”的 demo，这个项目更偏工程化。

  该项目相比其他多 Agent 项目的缺点

  1. 当前 memory 还比较粗，是把历史输出检索后拼进 prompt
  2. Agent 输出 schema 还不够强，部分阶段仍依赖 markdown/关键词
  3. Guard 还可能被自然语言误判
  4. 文件工具限制较强，只支持简单文件名，不利于复杂项目
  5. 缺少真正的 per-agent 私有上下文窗口
  6. 缺少完整 benchmark runner
  7. Trace 还没有完整记录 memory 检索、注入、guard 决策细节
  8. 架构较固定，不适合动态增删 agent 或复杂并行工作流

  所以它比普通 demo 更完整，但距离强生产级多 agent 系统还需要结构化输出、memory 治
  理、benchmark 和更强 trace。

  相比单 Agent 的优点

  1. 分工清晰：需求、设计、编码、测试、评审各自负责
  2. 更容易做质量闸门：测试失败回编码，评审失败回修订
  3. 更容易观测问题：知道是 PM、Coder、Tester 还是 Reviewer 出错
  4. 更容易扩展工具权限：Coder 能写文件，Reviewer 不需要写文件
  5. 更符合软件开发流程：先需求，再架构，再实现，再测试，再评审
  6. 对复杂任务更稳：不会让一个 agent 同时承担所有角色

  相比单 Agent 的缺点

  1. 成本更高：多轮 agent 调用会增加 token 和耗时
  2. 上下文更复杂：共享对话区容易变长
  3. 错误会传递：PM 需求错了，后面 agent 可能都跟着错
  4. 状态机和 guard 增加实现复杂度
  5. 多 agent 并不必然更聪明，低质量 agent 反而会互相污染
  6. 简单任务会显得过重，一个单 agent 可能更快更便宜

  一句话总结

  这个项目用 AutoGen 是为了快速获得多 agent 对话、工具调用和流式运行能力；它相比普
  通多 agent demo 更工程化、可观测、可控，但当前 memory、schema、guard、benchmark
  还需要增强。相比单 agent，它更适合复杂开发流程和质量控制，但成本、延迟和系统复杂
  度都会更高。