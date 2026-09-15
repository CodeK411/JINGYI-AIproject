# PubMedQA：生成式 LoRA-SFT vs 判别式 PubMedBERT

在**完全相同的测试集**上对比判别式与生成式两条技术路线在 PubMedQA
Yes / No / Maybe 三分类上的表现，并检验此前在 BERT 上观察到的
「以 accuracy 选型会放弃少数类」现象是否同样出现在生成式模型上。

## 结果

> Qwen 两行请替换为实际运行结果（见 `results/results_qwen_*.json`）。

| 模型 | 参数量 | accuracy | macro-F1 | weighted-F1 | F1(yes) | F1(no) | F1(maybe) |
|---|---|---|---|---|---|---|---|
| PubMedBERT baseline（判别式） | 110M | 0.6533 | 0.4439 | 0.6119 | 0.746 | 0.586 | **0.000** |
| PubMedBERT improved（判别式） | 110M | 0.6533 | **0.4856** | 0.6252 | 0.730 | 0.615 | **0.111** |
| Qwen2.5-0.5B-Instruct 未微调（生成式） | 0.5B | — | — | — | — | — | — |
| Qwen2.5-0.5B-Instruct + LoRA-SFT（生成式） | 0.5B | — | — | — | — | — | — |

- **baseline** = 无类别权重 + 按验证集 accuracy 选型
- **improved** = 类别加权交叉熵 + 按验证集 macro-F1 选型

## 关键发现

<!-- 跑完后按实际结果写 3–5 条，每条都要能对应到 results/ 里的数据 -->

1. **选型指标决定少数类存亡**：BERT 侧以 accuracy 选型时模型收敛到完全放弃 maybe
   类的解（F1 = 0.000），而 accuracy 反而更"好看"——因为 maybe 仅占测试集 16/150，
   放弃它几乎不损失整体准确率。改用 macro-F1 选型后 maybe F1 回到 0.111，
   **整体 accuracy 完全不变（两者均为 0.6533）**。这说明单一 accuracy 指标在类别不平衡
   任务上会系统性地奖励"放弃少数类"的模型。
2. **生成式模型是否复现同一现象**：…
3. **参数量与收益**：…
4. **评测方法的影响**：见下文"受限打分"。

## 可比性说明

两组实验共享**完全相同**的数据划分：

- 数据集：`qiaojin/PubMedQA` 的 `pqa_labeled`（1000 条专家标注）
- 划分代码逐行沿用 `train_pubmedbert.py`：两阶段分层 `train_test_split`，`random_state=42`
- train 700 / val 150 / test 150；测试集类别分布 yes 83 / no 51 / maybe 16
- 选型协议一致：每 epoch 在验证集评估并保留最优权重，**测试集只评估一次**

已知差异（已在实验记录中标注，非 bug）：

| 维度 | PubMedBERT | Qwen |
|---|---|---|
| 输入形式 | `question [SEP] passages`，512 token 截断 | chat template 指令，上下文截断至 350 词（预算与 512 token 大致对齐）|
| 输出方式 | 分类头 softmax 三分类 | 三个候选标签的序列对数似然打分 |
| 微调方式 | 全参数微调 | LoRA（r=16, alpha=32），仅训练约 0.4% 参数 |

## 方法

### 训练

- LoRA `r=16, alpha=32, dropout=0.05`，作用于 `q/k/v/o/gate/up/down_proj`
- 3 epochs，lr `2e-4`，linear warmup 10%，梯度裁剪 1.0，fp16 混合精度
- **只在答案 token 上计算 loss**，prompt 部分 mask 为 `-100`
- `improved` 模式下按类别频率做样本级损失加权，对应 BERT 脚本中的 `CrossEntropyLoss(weight=...)`

### 评测：受限打分，而非自由生成

自由生成再解析输出时，小模型经常不遵循"只回答一个词"的指令（输出 `Yes.`、
`The answer is yes`、或整段解释），解析失败会被计为错误答案——
**评测结果中因此混入格式不遵循的噪声，测量的不再是分类能力本身**。

本项目改为对 `yes` / `no` / `maybe` 三个候选分别计算其在当前 prompt 下的序列对数似然，
取最大者为预测。每个样本必然得到合法标签，测量的是模型对三个选项的相对偏好，
与 BERT 的 softmax 三分类在语义上对齐，指标可直接比较。

## 复现

Colab（免费 T4 即可，全程 25–40 分钟）：

1. 打开 `notebooks/pubmedqa_lora_colab.ipynb`
2. `代码执行程序` → `更改运行时类型` → **T4 GPU**
3. 从上往下运行。第 3 节会 `assert` 划分为 700/150/150，对不上会直接报错

跑 baseline 模式：把第 2 格的 `RUN_MODE` 改为 `"baseline"` 后重新全部运行。

## 项目结构

```
.
├── notebooks/pubmedqa_lora_colab.ipynb   # 主实验
├── baseline/train_pubmedbert.py          # 已有的 PubMedBERT 微调脚本
├── baseline/results_baseline.txt         # BERT baseline 完整输出
├── baseline/results_improved.txt         # BERT improved 完整输出
├── results/                              # Qwen 实验结果
└── requirements.txt
```

## 相关工作

PubMedBERT 基线来自此前的判别式微调工作，该模型同时作为
医学问答 ReAct Agent 中的结论预测工具使用。
