# VeriPolicy-RAG 今晚学习路线

目标是让你能够独立解释每个模块为什么存在、输入输出是什么、改掉它会发生什么。不要一开始逐行看完所有代码；先沿着一次查询走完整条链路，再回头研究实现。

## 第一轮：先看到系统真的运行

在项目根目录完成安装后，依次运行：

```bash
python -m veripolicy.cli inspect --corpus data/corpus

python -m veripolicy.cli ask \
  --question "2024 年国内出差一天饭补上限多少？" \
  --as-of 2024-06-01 \
  --region CN \
  --employee-type full_time

python -m veripolicy.cli ask \
  --question "2025 年国内出差一天饭补上限多少？" \
  --as-of 2025-06-01 \
  --region CN \
  --employee-type full_time
```

观察两个答案分别来自 `travel_cn_2024` 和 `travel_cn_2025`。问题文本几乎相同，真正改变结果的是 `as_of`。这就是项目与普通知识库问答的第一处区别。

再运行冲突问题：

```bash
python -m veripolicy.cli ask \
  --question "客户礼品单人单次上限是多少？" \
  --as-of 2025-06-01 \
  --region CN \
  --employee-type full_time \
  --threshold 0
```

两份同等权威的有效制度分别写了 300 元和 500 元。系统应返回冲突并拒绝给出确定值。`--threshold 0` 排除了低置信度的影响，证明停止作答是由冲突逻辑触发的。

## 第二轮：沿一次查询读代码

从 `src/veripolicy/pipeline.py` 的 `VeriPolicyRAG.ask()` 开始，调用顺序如下：

1. `retrieve()` 根据 mode 决定是否启用混合检索、元数据过滤和重排。
2. `scope.py` 判断一个 chunk 在查询日期是否生效，并检查地区、员工类型。
3. `retrieval.py` 分别计算 Dense 与 BM25 排名，再用 RRF 合并。
4. `rerank.py` 对候选计算语义分、关键词分、问题覆盖率、规则短语、适用范围和权威等级。
5. `conflicts.py` 对相同 `rule_key` 的不同值做优先级解析。
6. `confidence.py` 给当前证据计算可回答置信度。
7. `answering.py` 生成抽取式答案，或调用兼容 OpenAI 协议的模型。
8. `audit.py` 把 trace 写入 SQLite，方便后续分析错误样本。

每看完一步，用 `print(hit.to_dict())` 或 PyCharm Debug 查看数据结构。你需要重点认识三个对象：

- `QueryContext`：问题之外还有日期、地区和员工类型。
- `Chunk`：正文之外还有版本、有效期、权威等级和结构化规则。
- `SearchHit`：既有最终分数，也保留 dense、BM25、覆盖率等中间信号。

## 第三轮：把理论映射到代码

### Dense 检索

CPU profile 先把字符 n-gram TF-IDF 矩阵做 Truncated SVD，得到低维稠密向量，再计算余弦相似度。它可以离线快速复现，但语义能力有限。`SentenceTransformerDenseIndex` 才是生产用神经向量入口。

你要能回答：双塔 Embedding 为什么适合第一阶段大规模召回？因为文档向量可以提前计算，查询时只需一次编码和向量相似度搜索。

### BM25

`BM25Index` 统计词频、文档频率和长度归一化。它对 `P1`、金额、制度编号、缩写等精确信息更稳定。中文 tokenizer 同时保留汉字、二元词和短文本整体，以避免完全依赖分词库。

### RRF

Dense 余弦分数和 BM25 分数不在同一量纲。RRF 使用排名：

\[
\operatorname{RRF}(d)=\sum_r \frac{w_r}{k+\operatorname{rank}_r(d)}
\]

项目中 Dense 权重为 0.55，BM25 为 0.45，`k=60`。它稳定、无训练数据要求，适合作为第一个混合检索方案。

### 元数据过滤

`is_applicable()` 同时检查：

- `effective_from <= as_of <= effective_to`
- 地区为全局或与查询地区一致
- 员工类型为全员或与查询人群一致

本项目最明显的提升来自这里。它说明 RAG 的效果上限经常由数据建模和候选约束决定，换更大的 Embedding 不能自动解决旧版本混入。

### 重排

CPU 重排器保留每项特征，方便做错误分析。生产 profile 的 Cross-Encoder 会把 query 和 document 一起输入模型，能观察更细的交互，但每个候选都需要一次前向计算，因此只放在 Top-N 后。

### 冲突和拒答

冲突优先级是：适用范围更具体 > authority 更高 > 生效时间更新。如果最高优先级仍有两个不同值，系统不猜。

拒答阈值在开发集上最大化 balanced accuracy。测试集只评估，不参与阈值选择。你要能区分：检索 Hit@K 衡量“证据有没有被找到”，回答性准确率衡量“系统什么时候该开口”。

## 第四轮：亲手跑消融实验

执行：

```bash
python -m veripolicy.cli eval --output artifacts/eval
```

然后打开：

- `artifacts/eval/report.md`：总指标。
- `artifacts/eval/metrics.json`：机器可读结果。
- `artifacts/eval/per_query.jsonl`：每个问题的首个相关结果排名、置信度和 Top-1。

四组实验只改变一个主要因素：

1. `dense`
2. `hybrid`
3. `hybrid_temporal`
4. `full`

看指标时先看 Hit@1、MRR 和 `stale_or_wrong_scope@1`。Hit@3 已经很高但 Hit@1 较低，意味着相关证据在候选里，排序仍需优化；错版本率较高，说明问题出在有效性约束。

## 第五轮：做三个小修改验证理解

### 实验 A：移除时间过滤

在 `pipeline.py` 暂时把 `use_filter` 设为 `False`，重新跑测试。观察 2024/2025 成对制度的 Top-1 变化。实验后恢复代码。

### 实验 B：只用 BM25

在 Python Console 中调用：

```python
rag.index.search("P1 ack SLA", mode="bm25", top_k=5)
```

再换成中文语义改写，比较 BM25 与 Dense 的强弱。

### 实验 C：制造一个可解析冲突

复制一条相同 `rule_key` 的规则，给它更高 `authority`。原来的 unresolved conflict 应变成 `resolved_by_precedence`。这能帮助你理解业务优先级和模型相似度属于两类问题。

## 第六轮：升级到神经模型

在 GPU 环境安装 `requirements-ml.txt`，先只替换 Embedding：

```bash
python -m veripolicy.cli eval \
  --dense-backend sentence-transformers \
  --embedding-model Qwen/Qwen3-Embedding-0.6B \
  --reranker heuristic \
  --output artifacts/eval_qwen_embed
```

确认结果后再加入 Cross-Encoder。每个 profile 使用独立输出目录，避免覆盖。记录：

- Hit@1/3、MRR、nDCG
- 各 tag 的 Hit@3
- P50/P95 延迟
- 显存或内存占用
- 索引构建时间

不要只汇报总平均值。跨语言、时间问题和适用范围问题的变化更能说明模型到底解决了什么。

## Agent 升级路线

当前 `agent_tools.py` 已经把确定性能力封装成工具。推荐按以下顺序升级：

1. 意图路由：普通查询调用 `search_policy`，变化类问题调用 `compare_policy_versions`。
2. 缺槽追问：缺少日期、地区或员工类型时先提问，不默认猜测。
3. 工具循环：允许模型读取检索结果后决定是否补一次版本比较。
4. Human-in-the-loop：未决冲突、低置信度或高风险问题创建人工工单。
5. 离线 Agent 评测：衡量工具选择正确率、参数正确率、最终答案 groundedness 和平均调用次数。

Agent 只负责规划和工具选择。时间过滤、冲突解析、权限控制和最终引用验证继续留在工具内部。

## 今晚结束前的自测

你能够不看文档回答以下问题，就算真正掌握：

1. 为什么旧版本问题不能只靠向量相似度解决？
2. RRF 为什么比直接把 BM25 分数和余弦分数相加更稳？
3. 为什么元数据过滤应在重排前完成？
4. Cross-Encoder 为什么只处理 Top-N？
5. Hit@3 提升但 Hit@1 不变说明什么？
6. 同级制度冲突时系统为什么必须拒答？
7. 开发集选阈值、测试集报结果的边界在哪里？
8. 内置 CPU 指标为什么不能冒充 Qwen3 指标？
9. 接入十万文档后，哪些模块需要换成向量数据库或搜索引擎？
10. Agent 加进来后，哪些逻辑绝不能交给 LLM 自由决定？

