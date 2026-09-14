# AI 算法项目集


两个项目，覆盖 **LLM Agent 工程**、**预训练模型微调与评估方法论**、**注意力机制与网络结构改进**。
所有指标均来自可复现的实验，训练脚本与结果文件一并提交。

---

## 项目导航

### [01 · 医学问答 Agent（PubMedBERT 微调 + ReAct 工具链）](./01-medical-qa-react-agent)

一条完整的链路：先在 PubMedQA 上微调 PubMedBERT 做三分类，再把这个模型包装成工具，
交给自己实现的 ReAct Agent 调用。Agent 根据分类器返回的置信度，决定是继续检索还是下结论。

**第一部分 · PubMedBERT 微调与类别不平衡诊断**

通过 baseline / improved 对照实验发现：**以 accuracy 作为选型指标，会主动选中完全放弃少数类的
checkpoint**。

| 测试集（150 条，held out） | baseline | improved |
|---|---|---|
| Accuracy | 0.6533 | 0.6533 |
| **Macro-F1** | 0.4439 | **0.4856** |
| maybe 类 F1 | 0.0000 | **0.1111** |

准确率完全持平，macro-F1 提升 9.4%，少数类由完全不被预测变为可识别。

**第二部分 · ReAct Agent**

从零实现 ReAct 推理循环（不依赖 LangChain 等框架），接入三类工具：TF-IDF 文献检索、
上述自研微调模型、AST 白名单计算器。核心工作是定位并修复 4 类真实失败模式，
最终形成 **Prompt → 工具层 → 输出层**的三级约束，使 Agent 在证据不足时由"编造结论"
转为明确输出「证据不足，无法判断」。

| | |
|---|---|
| 关键技术 | ReAct、Tool Calling、输出解析与容错、循环检测、限流与指数退避 |
| 典型修复 | 检索索引漏建 question 字段 → 相关度 0.18 提升至 0.34 |
| 工程原则 | Prompt 是建议，代码才是保证 |

### [02 · 基于 CBAM 改进 ResNet 的中草药细粒度分类](./03-cbam-resnet-herb)

手写实现 CBAM 通道与空间注意力模块，嵌入 ResNet 的 BasicBlock 与 Bottleneck，
支持 ResNet34 / 50 / 101 与 ResNeXt 切换做消融对比。

| 同等 80 epoch | 验证准确率 | 训练损失 |
|---|---|---|
| ResNet34 | 89.1% | 0.491 |
| **ResNet34 + CBAM** | **93.7%** | **0.351** |

延长至 150 epoch 后验证准确率稳定在 97.4%；在 1502 张测试样本上 accuracy 93.94%、
macro-F1 0.939，18 个类别 F1 分布均衡，无少数类坍塌。

---

## 技术栈

**深度学习**：PyTorch（自定义 Dataset / nn.Module、手写注意力模块、混合精度训练、梯度裁剪、
warmup 调度、checkpoint 管理）、Hugging Face Transformers / Datasets

**大模型与 Agent**：ReAct、Tool Calling、Prompt 工程、结构化输出解析、OpenAI 兼容接口封装

**评估方法论**：macro-F1 与逐类 F1、混淆矩阵、错误样本归因、类别不平衡处理（加权交叉熵、
分层采样）、train / val / test 三划分与选型偏差控制

**工程**：Python、scikit-learn、pandas、NumPy、SQL / MySQL、Git、Linux、CUDA

---

## 说明

- 模型权重（`.pt`，约 440MB）未纳入版本控制，可由训练脚本复现。
- 运行 Agent 需自行配置 LLM API key（环境变量 `GEMINI_API_KEY`），代码中未包含任何密钥。
- 各项目目录下有独立 README，包含完整的实现细节与实验记录。
