---
doc_id: retention_2024
title: 业务数据保留标准（2024 版）
policy_family: data_retention
version: "1.0"
effective_from: 2024-01-01
effective_to: 2024-12-31
regions: ["ALL"]
employee_types: ["all"]
authority: 85
---

# 业务数据保留标准（2024 版）

本文件属于 VeriPolicy-RAG 的虚构企业制度基准语料，仅用于工程演示与评测。

## 客户会话

<!-- rule: {"key": "retention.customer_chat_days", "value": "180", "unit": "天", "label": "客户会话保留期", "statement": "2024 版标准要求客户聊天记录保留 180 天。", "aliases": ["聊天记录", "客户对话", "会话数据"]} -->

客服聊天正文和附件自会话关闭之日起计时；法律保全标记可以暂停删除。

## 应用日志

<!-- rule: {"key": "retention.app_log_days", "value": "365", "unit": "天", "label": "应用日志保留期", "statement": "2024 版标准要求生产应用日志保留 365 天。", "aliases": ["日志", "log", "生产日志"]} -->

生产应用日志进入集中日志平台，期满后自动删除。安全事件证据按单独保全流程处理。
