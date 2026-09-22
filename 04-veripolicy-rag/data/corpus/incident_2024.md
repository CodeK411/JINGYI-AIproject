---
doc_id: incident_2024
title: 生产事件响应手册（2024 版）
policy_family: incident_response
version: "1.0"
effective_from: 2024-01-01
effective_to: 2024-12-31
regions: ["ALL"]
employee_types: ["all"]
authority: 90
---

# 生产事件响应手册（2024 版）

本文件属于 VeriPolicy-RAG 的虚构企业制度基准语料，仅用于工程演示与评测。

## P1 首次响应

<!-- rule: {"key": "incident.p1_ack_minutes", "value": "15", "unit": "分钟", "label": "P1 确认时限", "statement": "2024 年 P1 事件必须在 15 分钟内确认。", "aliases": ["P1", "首次响应", "ack", "确认告警"]} -->

值班工程师收到 P1 告警后必须在规定时间内确认并进入事件频道。

## 复盘时限

<!-- rule: {"key": "incident.postmortem_days", "value": "5", "unit": "工作日", "label": "复盘提交时限", "statement": "2024 年 P1/P2 事件复盘须在恢复后 5 个工作日内提交。", "aliases": ["复盘", "postmortem", "根因分析"]} -->

事件负责人需要形成包含时间线、根因和行动项的无责复盘文档。
