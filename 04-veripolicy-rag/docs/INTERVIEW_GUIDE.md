# 面试与简历指南

## 30 秒项目介绍

我做了一个面向企业制度的时效和冲突感知 RAG。普通 RAG 在同一制度有多个版本、地区补充条款和员工类型例外时，容易召回已失效规则。我从零实现了结构化切块、Dense 与 BM25 混合检索、RRF 融合、日期/地区/人群过滤、候选重排、规则优先级、冲突拒答和引用校验，并构建了 108 条含 hard negatives 的评测集。在 CPU 可复现实验中，Hit@1 从 35.4% 提升到 83.3%，错版本或错适用范围的 Top-1 从 50% 降到 0。

## 两分钟项目介绍

项目场景是企业政策问答。同一个问题的答案会随着时间、地区和员工身份改变。例如 2024 年和 2025 年的出差餐补不同，英国员工和中国员工的休假制度也不同。只做向量 Top-K 会把文本很相似的旧版制度一起召回，大模型很难可靠判断哪个有效。

我的解决方案分四层。第一层是数据建模，在 Markdown 元数据中记录有效期、地区、员工类型、authority 和结构化 rule。第二层是 Dense + BM25，通过 RRF 做候选融合。第三层在检索阶段过滤失效或不适用的 chunk，再用可解释特征或 Cross-Encoder 重排。第四层对相同 rule 的不同值做优先级解析；同级冲突或低置信度时拒答，正常答案必须通过 citation 白名单校验。

我构造了 29 份版本化制度和 108 条问题，按开发/测试各 54 条划分，包含历史问法、跨语言表达、地区和员工类型 hard negatives、缺失规则和同级冲突。消融结果显示 Hit@1 从 35.4% 提升到 83.3%，MRR 从 57.7% 提升到 87.7%，错版本/错范围率从 50% 降到 0。当前 CPU profile 用 LSA 保证复现，接口支持切换 Qwen3 Embedding 和 Reranker。后续可以让 Agent 根据意图选择普通检索、版本比较或追问缺失条件。

## 简历写法

项目名称建议：

**VeriPolicy-RAG：时效与冲突感知的企业制度问答系统**

中文三条版：

- 从零实现面向版本化企业制度的 RAG，完成标题感知切块、Dense/BM25 混合召回、RRF 融合、Cross-Encoder 可插拔重排及 FastAPI 服务，不依赖 LangChain。
- 设计日期、地区、员工类型和 authority 元数据过滤，以及同规则冲突解析、置信度拒答和 citation 白名单校验，避免失效条款与地区例外被错误用于回答。
- 构建 108 问的 hard-negative 评测集并完成四组消融；CPU profile 上 Hit@1 由 35.4% 提升至 83.3%，MRR 由 57.7% 提升至 87.7%，错版本/错范围 Top‑1 由 50.0% 降至 0。

英文三条版：

- Built a version- and scope-aware enterprise policy RAG from scratch, including heading-aware chunking, dense/BM25 retrieval, reciprocal-rank fusion, pluggable reranking, and a FastAPI service without LangChain.
- Added effective-date, region, employee-type and authority constraints, plus rule-conflict resolution, calibrated abstention and citation allow-list validation to prevent stale or inapplicable evidence from reaching generation.
- Created a 108-query hard-negative benchmark and four-stage ablation; improved Hit@1 from 35.4% to 83.3% and MRR@10 from 57.7% to 87.7%, while reducing stale/wrong-scope Top‑1 retrieval from 50.0% to 0% in the reproducible CPU profile.

等你在 GPU 上跑过 Qwen3 profile 后，再替换模型名称和数字。没有实跑的结果不要写。

## 高频追问

### 为什么选这个项目？

它把 RAG 中最常见但经常被忽略的问题显式化：相关不等于适用。旧制度和新制度的语义最相似，向量检索反而容易同时找回；答案正确性取决于版本、范围和优先级。这个场景可以系统展示检索、排序、评测、安全拒答和工程服务化。

### 为什么不用微调把制度知识学进模型？

制度更新频繁，微调后的知识难以精确删除或追溯；不同地区和日期的答案还需要运行时条件。RAG 可以更新索引、展示原文并提供引用。微调更适合学习格式、语气或稳定行为，不适合作为频繁变化事实的唯一存储方式。

### 为什么混合检索？

Dense 对改写和语义近似更好，BM25 对金额、缩写、专有词和编号更稳定。两者错误模式不同。RRF 只依赖各自排名，避免手工把余弦分数与 BM25 原始分数放在同一尺度相加。

### 为什么先过滤再重排？

失效制度即使语义非常相关，也不应参加最终竞争。先过滤能缩小候选集、降低 Cross-Encoder 成本，并从结构上保证错误版本不能进入生成上下文。若业务允许查询历史版本，过滤依据是用户的 `as_of`，不会简单丢掉所有旧文件。

### 为什么还要 Cross-Encoder？

双塔分别编码 query 和 document，适合大规模召回，但交互有限。Cross-Encoder 联合编码二者，能更细地判断问题是否对应某一条具体规则。代价是每个候选都要做一次前向，因此只重排 Top-N。

### 你的 CPU Dense 算真正的 Embedding 吗？

它是 LSA 稠密向量基线，由 TF-IDF 经 Truncated SVD 得到，能复现完整流程，但语义能力不等同于预训练 Embedding。生产接口支持 Qwen3-Embedding；仓库报告明确区分两个 profile，没有把 LSA 结果冒充神经模型结果。

### 为什么 Hit@1 比 Hit@3 更值得关注？

生成上下文容量有限，首条证据对简短事实题影响最大。Hit@3 高而 Hit@1 低，说明召回覆盖还可以，问题集中在排序。两者都要报告；只报 Hit@K 容易掩盖错误版本排在第一位的风险。

### nDCG、MRR 和 Hit@K 分别说明什么？

- Hit@K：前 K 个结果里是否至少有相关证据。
- MRR：第一个相关结果出现得有多早，对首个正确证据很敏感。
- nDCG：考虑多个相关结果在整个排名中的位置，并使用对数折扣。

### 规则冲突怎么处理？

先按 scope specificity、authority、生效时间排序。更具体地区或员工类型的条款可以覆盖全球规则，高 authority 文件优先；若最高优先级仍有不同值，标记 unresolved 并停止作答。系统不会让 LLM自己猜哪个部门文件更权威。

### 拒答阈值如何选择？

从 Top-1 的问题覆盖率、Dense/BM25 信号、规则匹配、候选间 margin 等得到置信度，在开发集上网格搜索阈值并最大化 balanced accuracy。测试集只用于一次最终评估。生产中还应按高风险/低风险问题设置不同阈值并持续用反馈校准。

### 评测集会不会泄漏？

文档当然同时用于开发和测试检索；检索任务不会把问题用于训练 Embedding。每条规则有一个开发问法和一个测试改写，阈值只看开发集。它能验证改写鲁棒性，但仍属于同域评测，因此数据卡明确要求未来增加跨公司、跨模板的外部测试。

### 为什么不直接让 LLM 判断哪份制度最新？

日期比较和适用范围是确定性逻辑，用代码更便宜、稳定、可审计。把无效候选先删除也减少了模型被相似旧文本干扰的机会。LLM 适合组织答案和处理复杂语言，不适合替代数据库约束。

### 十万或百万 chunk 怎么扩展？

离线构建神经向量并写入 Qdrant、Milvus、Vespa 或 Elasticsearch；BM25 放在搜索引擎；日期、地区和员工类型使用 payload filter；RRF 可以由搜索层或服务层完成。Cross-Encoder 只处理几十个候选，并做批处理、缓存和量化。服务层还需加异步请求、限流、模型服务和监控。

### 为什么样例数据是虚构的？

企业制度通常涉及隐私和版权，公开数据又很难同时具备清晰版本、地区覆盖和可验证答案。受控语料可以有意构造旧版本、地区例外、同级冲突和缺失规则，适合验证算法。局限是规模和语言风格不代表真实分布，因此下一步要接入公开或获授权的真实制度并做外部评测。

### 如何升级 Agent？

让 Planner 在 `search_policy`、`compare_policy_versions`、追问缺失条件和人工升级之间路由。高风险逻辑仍由工具内部执行。评测要增加工具选择正确率、参数正确率、平均调用次数和最终引用正确率，不能只看最终文本是否流畅。

## 面试现场演示顺序

1. 问同一个差旅问题，只改变 `as_of`，展示 2024 和 2025 不同答案。
2. 问实习生学习预算，展示员工类型 scope。
3. 问客户礼品上限，展示同级冲突和拒答。
4. 打开 `artifacts/eval/report.md`，讲四组消融。
5. 打开一条 `per_query.jsonl` 失败案例，说明下一步如何改。

这个顺序十分钟内能覆盖业务问题、算法、可靠性和工程实现。

