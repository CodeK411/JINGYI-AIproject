---
doc_id: access_global_2024
title: 账号与权限生命周期标准（2024 版）
policy_family: access_control
version: "1.0"
effective_from: 2024-01-01
effective_to: 2024-12-31
regions: ["ALL"]
employee_types: ["all"]
authority: 90
---

# 账号与权限生命周期标准（2024 版）

本文件属于 VeriPolicy-RAG 的虚构企业制度基准语料，仅用于工程演示与评测。

## 离职回收

<!-- rule: {"key": "access.offboarding_hours", "value": "4", "unit": "小时", "label": "离职权限回收", "statement": "2024 年员工离职后须在 4 小时内完成账号和权限回收。", "aliases": ["离职", "账号回收", "权限撤销"]} -->

人力资源系统发出离职事件后，身份平台必须在服务目标内冻结账号并撤销会话。

## 生产权限审批

<!-- rule: {"key": "access.production_approvers", "value": "2", "unit": "人", "label": "生产权限审批人数", "statement": "生产写权限需要 2 名不同角色的审批人。", "aliases": ["生产权限", "审批人", "prod access"]} -->

长期生产写权限需要业务负责人和系统所有者共同审批，并按季度复核。
