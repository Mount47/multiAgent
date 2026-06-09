下面这版可以直接按面试口吻回答，注意我把“已实现”和“可扩展/规划”分开说，避免被追问时露怯。

  1. Agent 项目具体做了什么？主要有哪些 skill？

  这个项目是一个多 Agent 软件开发协作系统，目标是把一个开发任务从需求到交付自动化串起来。

  整体流程是：

  需求分析 -> 架构设计 -> 编码实现 -> 测试 -> 代码评审 -> 修改回流 -> 通过

  我没有让 Agent 自由聊天，而是用有限状态机控制流程。每个阶段由不同角色 Agent 负责，状态转移
  由 guard 函数判断，比如测试通过才进入 review，测试失败就回到 revision。

  主要 skill 可以理解成两层：

  第一层是主流程 skill，也就是“软件开发协作 skill”，负责整体任务编排。

  第二层是子 skill，对应不同专业能力：

  - ProductManager：需求分析，输出结构化需求。
  - Architect：架构设计，定义模块、接口、技术方案。
  - Coder：代码生成、读写文件、执行代码、安装依赖、保存记忆。
  - Tester：写测试、运行 pytest、分析失败日志。
  - Reviewer：代码评审，判断 APPROVED 或 REVISE。
  - Memory/RAG skill：检索历史任务经验，注入上下文。
  - Observability skill：记录 trace、token、状态耗时、工具调用链路。

  2. 主 skill 和子 skill 的作用分别是什么？

  主 skill 负责“控流程”，子 skill 负责“做具体事”。

  主 skill 更像一个 orchestrator，它决定：

  - 当前任务走到哪个阶段。
  - 下一个该哪个 Agent 执行。
  - 测试失败、评审失败时如何回流。
  - 最大轮次和最大 revision 次数，避免死循环。

  子 skill 更像专业工种：

  - PM 只关注需求。
  - Architect 只关注设计。
  - Coder 只关注实现。
  - Tester 只关注验证。
  - Reviewer 只关注质量。

  这样做的好处是职责边界清楚，prompt 可以分别优化，问题也更容易定位。比如结果不对，我能看是需
  求没分析清楚、架构设计偏了、代码写错了，还是测试/评审 guard 判断错了。

  3. MCP 做了啥？MCP 的调用流程是怎么样的？

  这个项目当前代码里没有完整接入标准 MCP Server/Client，实际实现的是 AutoGen 的 FunctionTool
  工具体系。但设计上和 MCP 的思想是一致的：把模型能力和外部工具能力解耦，让 Agent 通过统一协
  议调用工具。

  当前项目里工具包括：

  - execute_code
  - write_file
  - read_file
  - run_tests
  - install_dependency
  - search_memory
  - save_to_memory

  调用流程是：

  1. Agent 根据当前任务和 system prompt 判断是否需要工具。
  2. 模型通过 function calling 生成工具名和参数。
  3. AutoGen 捕获工具调用请求。
  4. Tool Registry 根据 agent role 判断它有没有权限使用该工具。
  5. 后端执行具体函数，比如写文件、跑测试、查 ChromaDB。
  6. 工具结果返回给 Agent。
  7. Agent 基于工具返回继续生成下一步输出。
  8. Trace 系统记录工具名、参数摘要、耗时、成功失败和错误信息。

  如果后续换成 MCP，核心变化是：工具不再只是本地 Python FunctionTool，而是通过 MCP Client 调
  远端 MCP Server。流程会变成：

  Agent -> MCP Client -> MCP Server -> Tool/Resource -> MCP Server 返回 -> Agent

  也就是把工具注册、工具描述、参数 schema、执行结果都标准化。

  4. RAG 整体流程？怎么量化召回率？怎么提优？

  这个项目里的 RAG 主要用于长期记忆增强，不是查百科知识，而是复用历史开发经验。

  整体流程是：

  1. 写入：把历史任务中的需求分析、架构设计、代码片段、测试结果、评审结论写入 ChromaDB。
  2. 分库：conversation 类内容进 conversations collection，代码类内容进 code_snippets
     collection。
  3. 向量化：ChromaDB 负责 embedding，默认模型通常是 all-MiniLM-L6-v2，384 维。
  4. 检索：新任务开始时，用任务描述作为 query，分别查 conversation 和 code。
  5. Top-K：当前默认取少量结果，比如每类 2 到 3 条，避免 prompt 被噪声撑大。
  6. 注入：把召回内容裁剪后拼到 prompt 里，作为历史上下文。
  7. 生成：Agent 参考这些历史经验完成设计、编码或测试。

  召回率量化我会用离线评测集：

  - 人工标注一批 query 和相关历史片段。
  - 对每个 query 检索 Top-K。
  - 计算 Recall@K = Top-K 中命中的相关文档数 / 所有相关文档数。
  - 同时看 Hit@K、MRR、nDCG，因为 RAG 不只要召回，还要排序靠前。

  提优手段：

  - query 改写：把原始需求扩展成“任务类型 + 技术栈 + 约束”。
  - metadata filter：按 phase、语言、任务类型过滤。
  - chunking：避免整段长文本入库，改成语义块。
  - rerank：先向量召回，再用关键词/模型重排。
  - distance 阈值：比如经验上 distance 大于 0.4 的结果噪声偏多，可以过滤。
  - 控制 Top-K：K 太小漏召回，K 太大引入噪声和 token 成本。

  5. 向量数据库怎么选择的？多少维？用索引了吗？比较过其他索引吗？

  我选 ChromaDB 是因为项目阶段更偏原型和工程闭环，数据量不大，重点是本地持久化、接入简单、和
  Python/AutoGen 集成快。

  选型对比是：

  - Milvus：适合更大规模、分布式、高并发场景，但部署和运维成本更高。
  - pgvector：如果业务数据已经在 PostgreSQL 里，适合和关系数据一起管理。

  当前 embedding 维度是 384 维，主要来自 ChromaDB 默认 embedding 模型 all-MiniLM-L6-v2。如果
  换 OpenAI embedding，维度会变，比如 1536 或 3072，取决于模型。

  索引用了。ChromaDB 底层默认使用 HNSW 近似最近邻索引，项目里 collection metadata 设置了：

  hnsw:space = cosine

  也就是用 cosine distance 做相似度检索。

  其他索引没有在项目里做完整 benchmark。我的判断是：当前数据规模下 HNSW 足够；如果数据上百万
  级，再比较 Flat、IVF、IVF-PQ、HNSW 的召回率、延迟、内存占用。

  6. Transformer 讲一下

  Transformer 是现在大模型的基础架构，核心是 self-attention。

  它解决的问题是：如何让模型在处理一个 token 时，动态关注输入序列中其他 token。

  整体结构包括：

  - Token Embedding：把 token 转成向量。
  - Positional Encoding：补充位置信息，因为 attention 本身不天然知道顺序。
  - Self-Attention：计算 token 之间的相关性。
  - Multi-Head Attention：多个 attention head 从不同角度看上下文关系。
  - Feed Forward Network：对每个位置做非线性变换。
  - Residual Connection + LayerNorm：稳定训练，缓解深层网络梯度问题。

  Self-Attention 的核心公式是：

  Attention(Q, K, V) = softmax(QK^T / sqrt(d_k)) V

  含义是：

  - Q 是 query，表示当前 token 想找什么。
  - K 是 key，表示每个 token 能提供什么信息。
  - V 是 value，表示真正被聚合的信息。
  - Q 和 K 做相似度，softmax 后作为权重，再加权求和 V。

  LLM 常用的是 decoder-only Transformer，比如 GPT 系列。它使用 causal mask，保证当前位置只能
  看到前面的 token，不能偷看未来 token，所以适合自回归生成。

  Transformer 的优势是并行训练能力强、长距离依赖建模能力强；劣势是 attention 复杂度通常是
  O(n²)，上下文越长，计算和显存成本越高。

─ Worked for 3m 05s ─────────────────────────────────────────────────────────────────────────


› 人工标注一批 query 和相关历史片段是指什么，具体怎么操作呢，举个例子


• “人工标注一批 query 和相关历史片段”，意思是：先准备一些模拟用户问题，然后人工判断历史记忆库
  里哪些内容应该被 RAG 检索出来。这个标注结果就是评测集，也叫 ground truth。

  举个和你项目贴近的例子。

  假设历史记忆库里有这些片段：

  doc_001:
  任务：实现用户登录注册 API
  内容：使用 FastAPI + JWT，密码用 bcrypt 哈希，登录成功返回 access_token。

  doc_002:
  任务：实现商品评论 API
  内容：评论接口需要校验 JWT，防止 SQL 注入，评论内容需要长度限制。

  doc_003:
  任务：实现文件上传功能
  内容：限制文件大小，校验 MIME type，上传后保存到本地 storage。

  doc_004:
  任务：修复 pytest 失败
  内容：测试失败原因是 mock 数据缺少 user_id 字段，补齐 fixture 后通过。

  doc_005:
  任务：实现订单支付接口
  内容：接入 Stripe，处理 webhook 签名校验和支付状态更新。

  现在你设计一个评测 query：

  query_001:
  我要做一个商品评价接口，需要登录后才能评论，还要注意数据库安全。

  人工标注时，你要判断哪些历史片段“应该被召回”。

  这里相关的是：

  相关文档：
  doc_002

  因为它直接讲了商品评论 API、JWT 校验、SQL 注入防护。

  可能部分相关的是：

  doc_001

  因为它讲了 JWT 登录鉴权，但没有讲商品评论和数据库安全。

  不相关的是：

  doc_003, doc_004, doc_005

  于是你可以做一个标注表：

  | query_id | query | relevant_docs |
  |---|---|---|
  然后跑你的 RAG 检索。如果系统返回：

  Top-3 = [doc_002, doc_005, doc_003]

  那 Recall@3 就是：

  命中的相关文档数 / 人工标注的相关文档总数
  = 1 / 2
  = 50%

  因为人工认为 doc_002 和 doc_001 都相关，但系统 Top-3 只召回了 doc_002。

  如果返回：

  Top-3 = [doc_002, doc_001, doc_005]

  那：

  Recall@3 = 2 / 2 = 100%

  这说明相关内容都被召回了。

  实际操作可以这样做：

  1. 从历史任务库里抽取 50 到 100 条文档片段，给每条一个 doc_id。
  2. 人工设计 20 到 50 个 query，覆盖常见任务类型，比如鉴权、测试失败、代码评审、安全问题。
  3. 对每个 query，人工标出哪些 doc 是相关的。
  4. 把结果存成 JSON 或 CSV。
  5. 写脚本批量调用 RAG 检索。
  6. 计算 Recall@K、Hit@K、MRR 等指标。

  JSON 示例：

  [
    {
      "query_id": "q001",
      "query": "我要做商品评价接口，需要登录后才能评论，还要注意数据库安全",
      "relevant_docs": ["doc_002", "doc_001"]
    },
    {
      "query_id": "q002",
      "query": "pytest 报错 fixture 缺字段，应该怎么修",
      "relevant_docs": ["doc_004"]
    }
  ]

  面试里可以这样说：

  “我们会人工构造一批 query，然后从历史 memory 里标注哪些片段是应该被召回的。比如 query 是‘做
  商品评论 API，需要 JWT 鉴权和 SQL 注入防护’，那历史里关于商品评论、JWT、SQL 注入防护的片段
  就标为 relevant。之后跑向量检索，看 Top-K 里命中了多少人工标注的 relevant doc，用 Recall@K
  来量化召回效果。”


基本绕不开长短期记忆怎么实现、多 Agent 怎么交互编
  排、RAG 的切片策略和检索指标，还有意图识别这些，怎么
  检验agent执行效果