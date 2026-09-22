---
doc_id: retention_2025
title: 业务数据最小化与保留标准（2025 版）
policy_family: data_retention
version: "2.0"
effective_from: 2025-01-01
effective_to: null
regions: ["ALL"]
employee_types: ["all"]
authority: 85
---

# 业务数据最小化与保留标准（2025 版）

本文件属于 VeriPolicy-RAG 的虚构企业制度基准语料，仅用于工程演示与评测。

## 客户会话

<!-- rule: {"key": "retention.customer_chat_days", "value": "90", "unit": "天", "label": "客户会话保留期", "statement": "自 2025 年起，普通客户聊天记录保留 90 天。", "aliases": ["聊天记录", "客户对话", "会话数据"]} -->

客服聊天正文与普通附件应最小化保存。欺诈调查或法律保全需要通过工单设置例外。

## 应用日志

<!-- rule: {"key": "retention.app_log_days", "value": "180", "unit": "天", "label": "应用日志保留期", "statement": "自 2025 年起，生产应用日志默认保留 180 天。", "aliases": ["日志", "log", "生产日志"]} -->

生产应用日志默认只保留诊断所需字段，含直接标识符的字段必须提前脱敏。

## 人事档案

<!-- rule: {"key": "retention.hr_years", "value": "7", "unit": "年", "label": "人事档案保留期", "statement": "核心人事档案在劳动关系结束后保留 7 年。", "aliases": ["人事档案", "劳动合同", "HR records"]} -->

劳动合同、薪酬变更和离职记录按法务保留表管理。
