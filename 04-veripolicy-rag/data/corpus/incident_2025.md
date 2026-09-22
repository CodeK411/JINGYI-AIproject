---
doc_id: incident_2025
title: 生产事件响应手册（2025 版）
policy_family: incident_response
version: "2.0"
effective_from: 2025-01-01
effective_to: null
regions: ["ALL"]
employee_types: ["all"]
authority: 90
---

# 生产事件响应手册（2025 版）

本文件属于 VeriPolicy-RAG 的虚构企业制度基准语料，仅用于工程演示与评测。

## P1 首次响应

<!-- rule: {"key": "incident.p1_ack_minutes", "value": "10", "unit": "分钟", "label": "P1 确认时限", "statement": "自 2025 年起，P1 事件必须在 10 分钟内确认。", "aliases": ["P1", "首次响应", "ack", "确认告警"]} -->

P1 告警触发后，主值班人需要确认告警、声明事件级别并拉起事件指挥。

## 复盘时限

<!-- rule: {"key": "incident.postmortem_days", "value": "3", "unit": "工作日", "label": "复盘提交时限", "statement": "自 2025 年起，P1/P2 事件复盘须在恢复后 3 个工作日内提交。", "aliases": ["复盘", "postmortem", "根因分析"]} -->

事件关闭前必须指定复盘负责人，复盘应记录可验证的行动项和完成日期。
