---
doc_id: access_global_2025
title: 账号与权限生命周期标准（2025 版）
policy_family: access_control
version: "2.0"
effective_from: 2025-01-01
effective_to: null
regions: ["ALL"]
employee_types: ["all"]
authority: 90
---

# 账号与权限生命周期标准（2025 版）

本文件属于 VeriPolicy-RAG 的虚构企业制度基准语料，仅用于工程演示与评测。

## 离职回收

<!-- rule: {"key": "access.offboarding_hours", "value": "1", "unit": "小时", "label": "离职权限回收", "statement": "自 2025 年起，普通员工离职后须在 1 小时内完成权限回收。", "aliases": ["离职", "账号回收", "权限撤销"]} -->

离职事件进入身份平台后自动冻结主账号，高风险系统由系统所有者确认二次撤销。

## 生产权限审批

<!-- rule: {"key": "access.production_approvers", "value": "2", "unit": "人", "label": "生产权限审批人数", "statement": "生产写权限仍需要 2 名不同角色的审批人。", "aliases": ["生产权限", "审批人", "prod access"]} -->

生产写权限必须有职责分离的双人审批，紧急权限最长保留八小时。
