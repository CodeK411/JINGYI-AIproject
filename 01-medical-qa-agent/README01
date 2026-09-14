# 医学问答 Agent：PubMedBERT 微调 + ReAct 工具链

一条完整链路——先训出一个分类器，发现它在证据不足时会瞎猜，于是套一层 Agent
让它先检索再判断，并在模型没把握时拒绝作答。

```
Question
   ↓
┌─────────────────────────────────────────┐
│  Thought → Action → Action Input        │
│     ↑                    ↓              │
│  Observation ←────── 工具执行            │
│                  ├ search_literature    │
│                  ├ classify_answer ─────┼──→ 自研微调 PubMedBERT
│                  └ calculator           │
└─────────────────────────────────────────┘
   ↓
Final Answer（须通过输出层证据校验）
```

---

# 第一部分 · PubMedBERT 微调与类别不平衡诊断

## 任务

PubMedQA 专家标注子集 PQA-L，仅 1000 条样本，需依据多段文献摘要判断医学问题的结论为
yes / no / maybe。三类分布约为 552 / 338 / 110，maybe 占比约 11%，
属于典型的**小样本 + 类别不平衡**任务。

## 实现

- **输入构造**：`question [SEP] contexts`，按 `max_length=512` 截断
- **模型**：`BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext` + 分类头，端到端微调而非冻结特征
- **训练**：AdamW（lr=2e-5, weight_decay=0.01）+ 10% linear warmup + 梯度裁剪（max_norm=1.0）
  + 混合精度（autocast + GradScaler）
- **划分**：train 700 / val 150 / test 150，两次切分均分层。**验证集选 checkpoint，测试集全程不参与任何决策，最后只评一次**

## 对照实验

脚本通过 `RUN_MODE` 切换两种配置，其余完全一致：

| | baseline | improved |
|---|---|---|
| 损失函数 | 普通交叉熵 | 类别加权交叉熵（按频率倒数） |
| 选型指标 | val accuracy | val macro-F1 |

### 测试集结果（150 条，held out，仅评估一次）

| | baseline | improved |
|---|---|---|
| Accuracy | 0.6533 | 0.6533 |
| **Macro-F1** | 0.4439 | **0.4856** |
| Weighted-F1 | 0.6119 | 0.6252 |
| yes 类 F1 | 0.7459 | 0.7303 |
| no 类 F1 | 0.5859 | 0.6154 |
| **maybe 类 F1** | **0.0000** | **0.1111** |

**准确率分毫不差，macro-F1 提升 9.4%。** 变化全部来自模型不再完全放弃 maybe 类。

### 关键发现：选型指标本身会淘汰对少数类友好的模型

看 baseline 的逐 epoch 记录：

```
epoch 3: val_acc=0.6933  macro_f1=0.4733  f1_maybe=0.000   ← 被 accuracy 选中
epoch 5: val_acc=0.6733  macro_f1=0.4897  f1_maybe=0.118
```

epoch 5 的 macro-F1 更高、maybe 也起来了，但因为按 accuracy 选型，
系统挑走了 epoch 3 那个**完全放弃 maybe** 的 checkpoint。

也就是说，问题不只出在损失函数上——**以 accuracy 作为选型指标，会主动选中忽略少数类的模型**，
因为忽略少数类反而让整体准确率更高。

### 局限

- 测试集仅 150 条，其中 maybe 类 16 条，单样本变动即可影响 F1 数个百分点
- improved 方案下 maybe 类 recall 仅 0.0625，问题只是**缓解**而非解决
- 验证集 macro-F1（0.5254）明显高于测试集（0.4856），这个 gap 本身就是小样本下
  "按验证集选出的最优 epoch 在未见数据上会打折"的实证

## 运行

```bash
pip install torch transformers datasets scikit-learn
python train_pubmedbert_v3.py     # 顶部 RUN_MODE 切换 "baseline" / "improved"
```

输出 `pubmedbert_{mode}.pt` 与 `results_{mode}.txt`。完整结果见本目录下两个 txt。

---

# 第二部分 · ReAct Agent

从零实现，不依赖 LangChain 等现成框架。Agent 自主决定调用哪个工具、调用几次、何时停止。

## 工具集

| 工具 | 实现 | 设计考量 |
|---|---|---|
| `search_literature` | TF-IDF + 余弦相似度，检索 PQA-L 1000 篇摘要 | 语料仅 1000 条，TF-IDF 足够；医学术语的精确匹配比语义相似更可靠，无需引入向量库的复杂度 |
| `classify_answer` | 加载第一部分微调的 PubMedBERT | 返回预测**与三类概率**，Agent 据此判断模型是否有把握 |
| `calculator` | AST 白名单解析 | 不用 `eval()`——输入来自 LLM 生成，属于不可信输入 |

LLM 调用统一走 OpenAI 兼容接口，切换供应商（Gemini / DeepSeek / 本地 Ollama）只需改一个字符串，
业务逻辑零改动。

## Bad Case 与修复

四类失败模式均为实际运行中观察到，修复后重新验证。

### ① 无效循环：连续 6 次检索，从不进入分类

**现象**：Agent 换了 6 种关键词反复调用 `search_literature`，撞上 `MAX_STEPS` 失败退出。

**根因（两层）**：测试问题超出语料覆盖范围，检索相关度仅 0.19–0.22；
Agent 没有放弃机制——看到结果不满意就换关键词重试，没有终止条件。

**修复**：检索工具在相关度低于阈值时主动提示"语料中可能无此主题，不要重复检索"；
主循环增加重复动作计数，同一工具调用超过 3 次即注入强制提示打断。

### ② 检索索引漏建 question 字段

**现象**：从语料中采样的问题（原文必然在库中），相关度仍只有 0.179。

**根因**：建索引时只使用了 context 段落，未包含 question 字段。用户是拿"问题"去检索的，
而问题的关键词往往出现在 question 而非摘要正文里。

**修复**：`question + context` 拼接后建立索引。同一问题相关度 **0.18 → 0.34**。

### ③ Prompt 层的置信度约束被模型无视

**现象**：分类器返回 `yes=0.386, no=0.377, maybe=0.237`（前两名相差 0.009，模型实际无法区分），
Agent 仍输出了斩钉截铁的结论。Prompt 中明确写过"三类概率接近时应重新检索，不要下结论"。

**修复**：把判断从 Prompt 下沉到工具代码——最高概率低于 0.50 或前两名差距小于 0.12 时，
工具**直接不返回预测值**，只返回"置信度不足，此结果不可作为结论使用"。

**结论**：Prompt 是建议，代码才是保证。凡是能用代码兜住的硬约束，不要指望 LLM 遵守。

### ④ 工具拒答后，模型改用自身先验知识作答

**现象**：工具层已明确拒绝给出结论，Agent 依然输出了确定性答案，并补充了检索结果中不存在的
医学常识——它在用参数里的知识回答，而非证据。

**根因**：工具层只能保证"工具不返回结论"，保证不了"LLM 不自己编结论"。

**修复**：增加输出层校验。全程跟踪是否获得过有效分类结果，若在无证据支撑的情况下给出
肯定/否定结论，则打回要求重答（最多 2 次），仍不改则强制标注"无工具证据支撑"。

**修复后实测**：Agent 被打回一次后，改用更精准的关键词重新检索，最终输出
「经过文献检索和分类模型验证，目前的证据不足以明确判断……因此无法给出确定的结论」。

### 三级约束

| 层 | 作用 | 能挡住什么 |
|---|---|---|
| Prompt | 建议 | 实测什么都挡不住 |
| 工具层 | 工具不返回结论 | 挡住"拿低置信度当依据" |
| 输出层 | 校验结论是否有工具证据支撑 | 挡住"凭先验知识作答" |

## 其他工程细节

- **`stop=["Observation:"]`**：不设置的话，模型会一口气把 Observation 和 Final Answer
  一起编出来，工具实际从未被调用，但输出看起来完全正常。
- **限流与指数退避**：ReAct 是循环结构，一个问题要连续调用 LLM 多次，在有 RPM 限制的
  免费额度下会瞬间触发 429。实现了调用间隔控制 + 指数退避重试。
- **Observation 截断**：检索返回的摘要很长，不截断会迅速撑爆上下文。
- **解析失败自纠**：格式错误时把错误信息作为 Observation 喂回，让模型自行纠正，最多 2 次。
- **文本格式而非强制 JSON**：小模型生成 JSON 常出现括号不闭合，解析失败率反而更高；
  Thought / Action 文本格式用正则容错更好，代价是格式约束较弱。
- **轨迹记录**：每次运行的完整轨迹写入 `trajectories.jsonl`，是上述 Bad Case 分析的原始材料。

## 运行

```bash
pip install openai transformers datasets scikit-learn torch

export GEMINI_API_KEY=your_key      # 代码中不含任何密钥

python agent.py                     # 入口处切换 offline_test() / real_run() / batch_run()
```

`offline_test()` 使用预设脚本的 MockLLM，不需要 API key，仅验证输出解析、工具分发与
Observation 回填是否正确。
