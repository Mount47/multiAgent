# Multi-Agent 项目 Benchmark / Evaluation 落地方案

本文档说明如何为当前多 Agent 软件开发系统构建一套可执行、可复现、可对比的评测体系。目标不是只做演示，而是用固定任务集和离线回放证明不同 harness 策略是否真的提升了 Agent 效果。

适用范围：

- 评估多 Agent 工作流最终代码质量
- 评估 Memory 检索、chunk、threshold、rerank 是否有效
- 评估不同模型、Prompt、Guard、工具策略的效果差异
- 为后续 SFT / Agentic RL 积累可清洗的轨迹数据

---

## 1. 总体目标

当前项目已有：

- Workflow Trace
- Metrics
- Tool Observation
- SQLite Task/Event 记录
- ChromaDB Memory
- 状态机与 Guard 单测

但这些更偏 observability，能说明“系统发生了什么”，还不能完整说明“Agent 效果是否变好”。完整 Evaluation 需要固定 benchmark、固定运行配置和可重复的评分逻辑。

本方案的核心思想：

```text
固定任务集
  -> 固定模型/参数/工具版本
  -> 多种策略配置回放
  -> 自动评分 + 少量人工/LLM judge 辅助
  -> 统计质量、成本、稳定性、Memory 检索质量
```

---

## 2. 目录结构设计

建议新增如下目录：

```text
benchmarks/
  cases/
    coding_palindrome_basic/
      task.yaml
      starter/
      hidden_tests/
        test_solution.py
      expected/
        rubric.md

    bugfix_csv_parser/
      task.yaml
      starter/
        csv_parser.py
      hidden_tests/
        test_csv_parser.py
      expected/
        rubric.md

    memory_slugify_to_filename/
      task.yaml
      seed_memory/
        memories.jsonl
      starter/
      hidden_tests/
        test_solution.py

  memory_gold/
    query_memory_labels.jsonl

  configs/
    baseline.yaml
    memory_off.yaml
    memory_threshold.yaml
    memory_chunk_rerank.yaml

  runs/
    2026-05-07_baseline/
      results.jsonl
      summary.json
      traces/

scripts/
  benchmark/
    run_benchmark.py
    score_case.py
    build_memory_gold.py
    tune_retrieval_threshold.py
    compare_runs.py
```

如果短期不想新增太多代码，可以先从 `benchmarks/cases`、`benchmarks/configs`、`scripts/benchmark/run_benchmark.py` 三部分开始。

---

## 3. Step 1：先建 Gold Benchmark

### 3.1 任务数量

第一版建议 30-50 个任务，数量不要过大，重点是覆盖面和稳定性。

任务分布建议：

| 类型 | 数量 | 目的 |
|---|---:|---|
| coding | 10-15 | 评估从零实现能力 |
| bugfix | 8-10 | 评估读代码、定位 bug、最小修复能力 |
| refactor | 5-8 | 评估保持行为不变下的结构改进 |
| memory_reuse | 5-8 | 评估长期记忆是否帮助相似任务 |
| revision_loop | 5-8 | 评估测试失败/评审拒绝后的回流修复能力 |

### 3.2 每个 case 的标准结构

每个 case 是一个可回放任务包。

```text
benchmarks/cases/<case_id>/
  task.yaml
  starter/
  hidden_tests/
  expected/
```

`task.yaml` 示例：

```yaml
id: memory_slugify_to_filename
type: memory_reuse
difficulty: easy
tags: [python, string_processing, memory]

prompt: |
  Implement `safe_filename(title: str) -> str` in `solution.py`.
  It should lowercase text, remove punctuation, collapse repeated separators,
  and use hyphens between words.

starter_files: []
expected_files:
  - solution.py

run:
  command: python -m pytest hidden_tests -q
  timeout_seconds: 60

success_criteria:
  hidden_tests_passed: true
  expected_files_exist: true

metadata:
  language: python
  requires_memory: true
  expected_memory_topics:
    - slugify
    - punctuation normalization
    - repeated separator collapse
```

`hidden_tests/test_solution.py` 示例：

```python
from solution import safe_filename


def test_basic_spaces():
    assert safe_filename("Hello World") == "hello-world"


def test_punctuation():
    assert safe_filename("Hello, World!") == "hello-world"


def test_repeated_separators():
    assert safe_filename("Hello---World___Again") == "hello-world-again"


def test_strip_edges():
    assert safe_filename("  --Hello--  ") == "hello"
```

### 3.3 Gold Benchmark 的判定原则

一个 case 能进入 gold benchmark，需要满足：

- hidden tests 稳定，不能依赖外部网络或时间
- 成功标准可由代码自动判断
- 任务描述不泄漏 hidden tests 全部答案
- starter files 和 expected files 明确
- 至少人工确认过一次标准答案可通过

---

## 4. Step 2：给 Memory 样本做人工标注

### 4.1 为什么需要人工标注

向量数据库只能返回“语义距离近”的片段，但评测需要知道“这个片段对当前任务是否真的有帮助”。因此需要小规模人工 gold set 来校准 threshold、Top-K、rerank。

### 4.2 Memory 文档格式

切块入库后的每条 memory 建议有稳定 ID：

```json
{
  "memory_id": "mem_slugify_func_001",
  "content": "def slugify(text): ...",
  "summary": "Implements slug generation by lowercasing, removing punctuation, and collapsing separators.",
  "metadata": {
    "task_id": "task_001",
    "agent": "coder",
    "phase": "coding",
    "language": "python",
    "task_type": "coding",
    "chunk_type": "function",
    "symbol": "slugify",
    "tests_passed": true,
    "approved": true
  }
}
```

### 4.3 Query-Memory 标注格式

`benchmarks/memory_gold/query_memory_labels.jsonl`：

```json
{
  "query_id": "q_safe_filename_001",
  "case_id": "memory_slugify_to_filename",
  "query": "Implement safe_filename(title), lowercase, remove punctuation, collapse separators, use hyphens.",
  "labels": [
    {
      "memory_id": "mem_slugify_func_001",
      "relevance": 2,
      "reason": "Same normalization and slug generation pattern."
    },
    {
      "memory_id": "mem_review_slugify_edges_001",
      "relevance": 2,
      "reason": "Mentions edge cases for punctuation and repeated separators."
    },
    {
      "memory_id": "mem_fastapi_auth_001",
      "relevance": 0,
      "reason": "Different domain and not useful for string normalization."
    }
  ]
}
```

相关性分级：

| relevance | 含义 | 注入策略 |
|---:|---|---|
| 2 | 强相关，应该注入 | 优先保留 |
| 1 | 弱相关，可选 | budget 足够时可保留 |
| 0 | 无关，不应注入 | 应过滤 |

### 4.4 标注流程

1. 先收集历史任务输出，按 chunk 策略生成 memory 文档。
2. 对每个 benchmark case，用原始检索策略召回 Top-20。
3. 人工查看 query 和候选 memory。
4. 标注 `2/1/0` 和简短原因。
5. 保存 JSONL，作为 retrieval gold set。

第一版不需要标太多，建议：

- 30-50 个 query
- 每个 query 标 Top-20
- 总计 600-1000 个 query-memory pair

这个规模已经足够调初版 threshold 和 rerank。

---

## 5. Step 3：调检索阈值

### 5.1 先明确 ChromaDB 返回的是 distance 还是 similarity

ChromaDB cosine space 通常返回 `distance`。不同 embedding 配置下数值范围和含义可能不同，因此不能直接套用“0.8 相似度”这种经验值。

需要先把结果标准化，例如：

```python
similarity = 1.0 - distance
```

但是否适用要基于当前 ChromaDB 返回值验证。

### 5.2 阈值调参目标

用人工标注集计算：

- `Precision@K`：注入的 Top-K 中有多少相关
- `Recall@K`：所有相关 memory 中召回了多少
- `MRR`：第一个相关结果排第几
- `nDCG@K`：排序质量
- `Noise Rate`：注入 memory 中 relevance=0 的比例

核心目标不是单纯 Precision 越高越好，而是：

```text
在 Noise Rate 可控的前提下，尽量提高 Recall，并最终提升 downstream pass rate。
```

### 5.3 阈值搜索伪代码

```python
thresholds = [0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]

for threshold in thresholds:
    metrics = evaluate_retrieval(
        gold_file="benchmarks/memory_gold/query_memory_labels.jsonl",
        threshold=threshold,
        top_k=5,
    )
    print(threshold, metrics)
```

输出示例：

```json
{
  "threshold": 0.35,
  "precision_at_5": 0.72,
  "recall_at_5": 0.61,
  "mrr": 0.80,
  "noise_rate": 0.12
}
```

### 5.4 推荐策略

第一版可以采用：

```text
粗召回 Top-30
过滤低于 threshold 的候选
最多保留 Top-5
注入时最多 Top-3
```

如果任务是 `memory_reuse`，可以略放宽 recall；如果任务是普通 coding，可以更保守，避免无关记忆污染。

---

## 6. Step 4：调 Chunk 策略

### 6.1 需要比较的策略

至少比较三种：

| 策略 | 说明 |
|---|---|
| fixed_truncation | 当前策略：Agent 输出整体存储，固定截断 |
| semantic_markdown | PM/Architect/Reviewer 按 Markdown section 或 issue 切 |
| code_symbol_ast | Coder 按文件/类/函数切；Tester 按测试用例/traceback 切 |

### 6.2 不同 Agent 的切块规则

| Agent | 推荐切块 |
|---|---|
| ProductManager | 按需求项、边界条件、验收标准 |
| Architect | 按模块、接口、技术决策 |
| Coder | 按文件、class、function、关键代码块 |
| Tester | 按测试用例、失败日志、traceback、verdict |
| Reviewer | 按 issue、建议项、最终 verdict |

### 6.3 为什么不完全交给模型切

不建议让 LLM 决定切块边界，原因：

- 不稳定，同一内容可能多次切出不同结果
- 成本高
- 不利于 benchmark 复现
- 容易切断代码结构

更合理的方案：

```text
代码规则负责切块边界
LLM 只负责生成 summary / tags / task_type / concepts
```

### 6.4 代码切块示例

Python 代码可基于 AST：

```python
import ast


def chunk_python_file(path: str, source: str) -> list[dict]:
    tree = ast.parse(source)
    lines = source.splitlines()
    chunks = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = node.lineno
            end = getattr(node, "end_lineno", node.lineno)
            content = "\n".join(lines[start - 1:end])
            chunks.append({
                "content": content,
                "metadata": {
                    "file": path,
                    "symbol": node.name,
                    "chunk_type": type(node).__name__,
                    "language": "python",
                },
            })

    return chunks
```

### 6.5 文本切块示例

Markdown 可按标题切：

```python
def chunk_markdown(text: str) -> list[str]:
    chunks = []
    current = []

    for line in text.splitlines():
        if line.startswith("#") and current:
            chunks.append("\n".join(current).strip())
            current = [line]
        else:
            current.append(line)

    if current:
        chunks.append("\n".join(current).strip())

    return [c for c in chunks if c]
```

### 6.6 Chunk 策略评估指标

每种 chunk 策略都要跑：

- retrieval Precision@K
- retrieval Recall@K
- Noise Rate
- Memory 注入 token 数
- benchmark hidden test pass rate
- revision 次数

最终选择不是看“chunk 越细越好”，而是看下游任务是否更稳定。

---

## 7. Step 5：固定评测配置

### 7.1 为什么必须固定

LLM 评测很容易被随机性污染。如果同时修改模型、temperature、Prompt、chunk、threshold，就无法判断效果提升来自哪里。

必须固定：

- 模型供应商和模型名
- temperature
- max retries
- timeout
- workspace 初始状态
- benchmark 版本
- tools 版本
- prompts 版本
- workflow 配置版本
- memory seed 数据版本

### 7.2 配置文件示例

`benchmarks/configs/baseline.yaml`：

```yaml
name: baseline

model:
  provider: deepseek-chat
  temperature: 0.2
  timeout_seconds: 60
  max_retries: 2

workflow:
  config_path: config/workflows.yaml
  max_rounds: 30
  max_revisions: 3

memory:
  enabled: true
  chunk_strategy: fixed_truncation
  retrieval_top_k: 2
  threshold: null
  rerank: none
  injection_budget_tokens: 1200

tools:
  run_tests_timeout_seconds: 60
  execute_code_timeout_seconds: 30

benchmark:
  cases_dir: benchmarks/cases
  repeat: 3
  random_seed: 42
```

`benchmarks/configs/memory_chunk_rerank.yaml`：

```yaml
name: memory_chunk_rerank

model:
  provider: deepseek-chat
  temperature: 0.2
  timeout_seconds: 60
  max_retries: 2

memory:
  enabled: true
  chunk_strategy: code_symbol_ast
  retrieval_top_k: 30
  threshold: 0.35
  rerank: cross_encoder
  rerank_top_k: 5
  inject_top_k: 3
  injection_budget_tokens: 1600
```

---

## 8. Step 6：做 Ablation

### 8.1 Ablation 原则

每次只改一个变量。不要同时改模型、Prompt、Memory 和 Guard。

推荐实验矩阵：

| 实验名 | Memory | Threshold | Chunk | Rerank |
|---|---|---|---|---|
| A_baseline_memory_off | off | - | - | - |
| B_memory_current | on | no | fixed_truncation | no |
| C_memory_threshold | on | yes | fixed_truncation | no |
| D_memory_chunk | on | yes | semantic/code chunk | no |
| E_memory_chunk_rerank | on | yes | semantic/code chunk | yes |

### 8.2 对比目标

| 对比 | 要证明什么 |
|---|---|
| B vs A | Memory 是否总体有帮助 |
| C vs B | Threshold 是否降低噪声 |
| D vs C | 语义切块是否提高召回质量 |
| E vs D | Rerank 是否提高排序质量 |

### 8.3 统计输出

每组实验输出：

```json
{
  "run_id": "2026-05-07_memory_chunk_rerank",
  "config": "memory_chunk_rerank",
  "num_cases": 40,
  "repeat": 3,
  "hidden_tests_pass_rate": 0.78,
  "first_pass_rate": 0.55,
  "final_success_rate": 0.82,
  "avg_revision_count": 0.9,
  "avg_total_tokens": 7200,
  "avg_duration_ms": 48120,
  "retrieval_precision_at_5": 0.74,
  "retrieval_recall_at_5": 0.63,
  "noise_rate": 0.11
}
```

### 8.4 判断策略是否有效

一个策略可以认为有效，至少要满足：

- hidden tests pass rate 不下降
- final success rate 上升，或 revision/token 显著下降
- Noise Rate 下降
- token 成本增长可解释且可接受
- 多次 repeat 后趋势一致

如果 Memory 开启后 pass rate 没提升但 token 明显增加，说明 Memory 策略不值得上线。

---

## 9. Step 7：记录统计结果

### 9.1 Case 级结果

`results.jsonl` 每行一个 case run：

```json
{
  "run_id": "2026-05-07_memory_chunk_rerank",
  "case_id": "memory_slugify_to_filename",
  "repeat_index": 1,
  "status": "passed",
  "hidden_tests_passed": true,
  "expected_files_exist": true,
  "duration_ms": 42800,
  "total_tokens": 6120,
  "prompt_tokens": 4800,
  "completion_tokens": 1320,
  "revision_count": 1,
  "tool_call_count": 7,
  "tool_failed_count": 0,
  "state_path": [
    "requirements_analysis",
    "architecture_design",
    "coding",
    "testing",
    "code_review",
    "approved"
  ],
  "memory": {
    "enabled": true,
    "retrieved_count": 12,
    "injected_count": 3,
    "injected_tokens": 980,
    "noise_count": 0
  },
  "model": "deepseek-chat"
}
```

### 9.2 Summary 级结果

`summary.json`：

```json
{
  "run_id": "2026-05-07_memory_chunk_rerank",
  "config_name": "memory_chunk_rerank",
  "started_at": "2026-05-07T10:00:00Z",
  "ended_at": "2026-05-07T11:20:00Z",
  "num_cases": 40,
  "repeat": 3,
  "metrics": {
    "final_success_rate": 0.82,
    "hidden_tests_pass_rate": 0.78,
    "first_pass_rate": 0.55,
    "avg_revision_count": 0.9,
    "avg_total_tokens": 7200,
    "avg_duration_ms": 48120,
    "avg_tool_failed_count": 0.3
  }
}
```

### 9.3 多次运行

每个配置至少跑 3 次。LLM 输出有随机性，即使 temperature 较低也可能出现波动。

建议记录：

- mean
- median
- standard deviation
- min/max

如果样本量足够，可做置信区间或 bootstrap。

---

## 10. Benchmark Runner 实现流程

### 10.1 Runner 主流程

```text
load config
  -> load benchmark cases
  -> for each case and repeat
      -> create isolated workspace
      -> copy starter files
      -> seed memory if needed
      -> create task through TaskService or CLI wrapper
      -> wait workflow complete/failed/timeout
      -> run hidden tests
      -> collect trace and metrics
      -> write result jsonl
  -> aggregate summary
```

### 10.2 Runner 伪代码

```python
async def run_benchmark(config_path: str):
    config = load_yaml(config_path)
    cases = load_cases(config["benchmark"]["cases_dir"])
    results = []

    for case in cases:
        for repeat_index in range(config["benchmark"]["repeat"]):
            workspace = create_workspace(case.id, repeat_index)
            copy_starter_files(case, workspace)
            seed_memory_if_needed(case, config)

            task_id = await submit_task(
                prompt=case.prompt,
                provider=config["model"]["provider"],
                workspace=workspace,
                memory_config=config["memory"],
            )

            task_result = await wait_task_done(task_id, timeout=case.timeout)
            test_result = run_hidden_tests(case, workspace)
            trace = fetch_trace(task_id)

            result = score_case(case, task_result, test_result, trace)
            append_jsonl("results.jsonl", result)
            results.append(result)

    summary = aggregate(results)
    write_json("summary.json", summary)
```

### 10.3 与当前项目的接入方式

短期最简单：

- 通过 API `POST /api/tasks` 提交任务
- 通过 `GET /api/tasks/{id}` 轮询状态
- 通过 `GET /api/traces/{id}` 获取 trace
- 直接在 workspace 中运行 hidden tests

长期更推荐：

- 增加 `BenchmarkTaskService`
- 允许为每个 case 指定独立 workspace
- 允许注入 memory 配置
- 允许 mock LLM 做流程回归测试

---

## 11. 自动评分逻辑

### 11.1 强确定性评分

优先用代码评分：

- hidden tests 是否通过
- expected files 是否存在
- 函数签名是否保持
- pytest exit code
- 是否超时
- 是否触发 max revisions
- 工具调用是否失败
- 状态路径是否符合预期

### 11.2 示例评分代码

```python
def score_case(case, task_result, test_result, trace):
    transitions = trace.get("transitions", [])
    state_path = [t["from_state"] for t in transitions]

    return {
        "case_id": case.id,
        "status": "passed" if test_result.exit_code == 0 else "failed",
        "hidden_tests_passed": test_result.exit_code == 0,
        "expected_files_exist": all(
            (case.workspace / f).exists() for f in case.expected_files
        ),
        "duration_ms": trace.get("duration_ms", 0),
        "total_tokens": trace.get("total_tokens", 0),
        "prompt_tokens": trace.get("total_prompt_tokens", 0),
        "completion_tokens": trace.get("total_completion_tokens", 0),
        "revision_count": state_path.count("revision"),
        "tool_call_count": len(trace.get("tool_calls", [])),
        "tool_failed_count": sum(
            1 for tc in trace.get("tool_calls", []) if not tc["success"]
        ),
        "state_path": state_path,
    }
```

### 11.3 LLM Judge 的位置

LLM Judge 只能作为补充，不作为最终 pass/fail 标准。

适合评：

- 代码可读性
- 架构合理性
- 测试覆盖质量
- 需求分析完整性

不适合替代：

- hidden tests
- pytest
- lint/type check
- API signature check

原则：

```text
硬正确性用代码评
软质量用 judge 辅助
```

---

## 12. Rerank 实现方案

### 12.1 两阶段检索

```text
ChromaDB 向量召回 Top-30
  -> metadata filter
  -> cross-encoder reranker
  -> token budget 选择 Top-3 注入
```

### 12.2 为什么选择 Cross-Encoder

Embedding 检索是分别编码 query 和 chunk，再算距离，适合粗召回。Cross-Encoder 会把 `(query, chunk)` 拼在一起输入模型，直接输出相关性分数，更适合精排。

优点：

- 排序质量通常高于纯向量相似度
- 成本低于大模型 judge
- 输出是数值分数，方便阈值和 ablation
- 可批量处理候选

候选技术：

- `bge-reranker-base`
- `bge-reranker-large`
- `jina-reranker`
- Cohere Rerank API

第一版可优先选择本地 `bge-reranker-base`，原因是成本低、便于离线 benchmark、结果可复现。

### 12.3 Rerank 伪代码

```python
def retrieve_with_rerank(query: str, top_n: int = 30, inject_k: int = 3):
    candidates = chroma_search(query, n_results=top_n)
    candidates = metadata_filter(candidates, query)
    candidates = [c for c in candidates if c.similarity >= THRESHOLD]

    pairs = [(query, c.content) for c in candidates]
    rerank_scores = reranker.predict(pairs)

    for c, score in zip(candidates, rerank_scores):
        c.rerank_score = score
        c.final_score = 0.7 * score + 0.2 * c.similarity + 0.1 * metadata_score(c)

    ranked = sorted(candidates, key=lambda x: x.final_score, reverse=True)
    return fit_token_budget(ranked, inject_k=inject_k, budget_tokens=1600)
```

---

## 13. 如何判断这套评测真的有效

一套有效 benchmark 应该满足：

- 能稳定复现 baseline 结果
- 能发现明显 regression
- 能区分不同 harness 策略
- 指标和人工直觉基本一致
- 不依赖单次 LLM 输出
- 任务覆盖真实项目场景

如果某次改动号称“优化 Memory”，但 benchmark 显示：

```text
pass rate 不变
token 上升 30%
noise rate 上升
revision 次数不变
```

那这个改动就不应该上线。

---

## 14. 面试回答模板

如果面试官问“这 7 步怎么落地”，可以回答：

> 我会先把 benchmark 做成可回放任务包，每个 case 包含 task.yaml、starter files、hidden tests 和评分规则。第一版选 30-50 个任务，覆盖 coding、bugfix、refactor、memory reuse 和多轮修订。  
>
> 对 Memory，我会额外做一个 query-memory 标注集。每个 benchmark task 作为 query，人工标注历史 memory 里哪些强相关、弱相关、无关。这个 gold set 用来调检索 threshold，指标包括 Precision@K、Recall@K、MRR 和 Noise Rate。  
>
> Chunk 策略不会只用固定截断，而是比较固定截断、Markdown 语义切块、代码 AST 函数级切块。每次只改一个变量做 ablation，比如先 memory off，再 memory on，再加 threshold，再加 chunk，再加 rerank。  
>
> 运行时固定模型、temperature、工具版本、workspace 和 benchmark 版本。每个配置至少重复跑 3 次，记录 hidden tests pass rate、一次通过率、最终成功率、revision 次数、token、耗时、工具失败率和 memory 噪声注入率。这样才能判断某个 harness 优化是否真的提升了 Agent 效果，而不是靠主观感觉。

---

## 15. 第一阶段实施清单

短期最小可行版本：

- [ ] 新建 `benchmarks/cases`
- [ ] 先写 10 个 case：5 个 coding、3 个 bugfix、2 个 memory_reuse
- [ ] 定义 `task.yaml` schema
- [ ] 写 `scripts/benchmark/run_benchmark.py`
- [ ] 写 `scripts/benchmark/score_case.py`
- [ ] 输出 `results.jsonl` 和 `summary.json`
- [ ] 人工标注 10 个 query 的 Top-20 memory
- [ ] 实现 threshold sweep
- [ ] 跑 `memory_off` vs `memory_current` vs `memory_threshold`

第二阶段：

- [ ] 实现 Markdown semantic chunk
- [ ] 实现 Python AST code chunk
- [ ] 接入 cross-encoder reranker
- [ ] 完整跑 30-50 个 case
- [ ] 形成 ablation 报告
