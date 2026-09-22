from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIR = ROOT / "data" / "corpus"
EVAL_PATH = ROOT / "data" / "eval" / "queries.jsonl"


def rule(
    key: str,
    value: str | int,
    label: str,
    statement: str,
    aliases: list[str],
    unit: str = "",
) -> dict[str, Any]:
    return {
        "key": key,
        "value": str(value),
        "unit": unit,
        "label": label,
        "statement": statement,
        "aliases": aliases,
    }


def section(title: str, prose: str, *rules: dict[str, Any]) -> dict[str, Any]:
    return {"title": title, "prose": prose, "rules": list(rules)}


DOCS: list[dict[str, Any]] = [
    {
        "doc_id": "leave_global_2023",
        "title": "员工带薪休假制度（2023 版）",
        "family": "annual_leave",
        "version": "1.0",
        "start": "2023-01-01",
        "end": "2024-12-31",
        "regions": ["ALL"],
        "employees": ["full_time"],
        "authority": 50,
        "sections": [
            section(
                "年度额度",
                "正式员工完成试用期后，每个自然年度获得固定的带薪年假额度。入职不足一年按在职月份折算。",
                rule("annual_leave.days", 10, "年假天数", "2023—2024 年适用的年度带薪年假为 10 天。", ["年假", "带薪休假", "annual leave"], "天"),
            ),
            section(
                "结转规则",
                "未使用的年假可以结转到下一自然年度，但超过上限的部分在年末失效，不折现。",
                rule("annual_leave.carryover", 3, "年假结转上限", "旧版制度允许最多结转 3 天年假。", ["结转", "顺延", "carry over"], "天"),
                rule("annual_leave.carryover_deadline", "03-31", "结转使用期限", "结转年假须在次年 3 月 31 日前使用。", ["结转期限", "过期", "deadline", "最晚", "几月几日前", "用掉"]),
            ),
            section("申请流程", "连续休假三天及以上须提前十个工作日提交申请，并由直属经理批准。紧急情况可以补交说明。"),
        ],
    },
    {
        "doc_id": "leave_global_2025",
        "title": "员工带薪休假制度（2025 版）",
        "family": "annual_leave",
        "version": "2.0",
        "start": "2025-01-01",
        "end": None,
        "regions": ["ALL"],
        "employees": ["full_time"],
        "authority": 50,
        "sections": [
            section(
                "年度额度",
                "正式员工通过试用期后按月累计年假，每满一个月累计一天；全年额度按自然年度核算。",
                rule("annual_leave.days", 12, "年假天数", "自 2025 年起，正式员工每年可享 12 天带薪年假。", ["年假", "带薪休假", "annual leave"], "天"),
            ),
            section(
                "结转与失效",
                "年假结转需要在系统中自动完成，员工无需另行申请；逾期部分不再保留。",
                rule("annual_leave.carryover", 5, "年假结转上限", "2025 版制度允许最多结转 5 天年假。", ["结转", "顺延", "carry over"], "天"),
                rule("annual_leave.carryover_deadline", "06-30", "结转使用期限", "结转年假须在次年 6 月 30 日前使用。", ["结转期限", "过期", "deadline", "最晚", "几月几日前", "用掉"]),
            ),
            section("申请流程", "连续休假五天及以上须提前十五个工作日提交；两天以内由直属经理在系统审批。"),
        ],
    },
    {
        "doc_id": "leave_cn_service_2025",
        "title": "中国区长期服务员工休假补充规定",
        "family": "annual_leave",
        "version": "1.0",
        "start": "2025-01-01",
        "end": None,
        "regions": ["CN"],
        "employees": ["full_time"],
        "authority": 70,
        "sections": [
            section(
                "十年以上工龄",
                "中国区员工累计可认定工龄达到十年时，长期服务额度替代全球基础额度，以较高标准执行。",
                rule("annual_leave.long_service_days", 15, "长期服务年假", "中国区累计工龄满十年的正式员工每年可享 15 天年假。", ["十年工龄", "长期服务", "老员工"], "天"),
            ),
            section("证明材料", "外部单位工龄需要提交社保记录或离职证明，由人力资源团队在十五个工作日内完成认定。"),
        ],
    },
    {
        "doc_id": "leave_gb_2025",
        "title": "英国区带薪休假补充规定",
        "family": "annual_leave",
        "version": "1.0",
        "start": "2025-01-01",
        "end": None,
        "regions": ["GB"],
        "employees": ["full_time"],
        "authority": 70,
        "sections": [
            section(
                "年度额度",
                "英国区正式员工执行本地额度，本条覆盖全球员工带薪休假制度中的基础年度额度。公共假日另计。",
                rule("annual_leave.days", 25, "英国区年假天数", "英国区正式员工每年可享 25 天带薪年假，公共假日另计。", ["英国年假", "UK annual leave", "holiday entitlement"], "天"),
            ),
            section(
                "结转规则",
                "经经理批准后可以将少量未休额度带入下一年度。",
                rule("annual_leave.carryover", 8, "英国区结转上限", "英国区最多可结转 8 天年假。", ["英国结转", "carry over"], "天"),
            ),
        ],
    },
    {
        "doc_id": "leave_intern_2025",
        "title": "实习员工休假补充规定",
        "family": "annual_leave",
        "version": "1.0",
        "start": "2025-01-01",
        "end": None,
        "regions": ["ALL"],
        "employees": ["intern"],
        "authority": 65,
        "sections": [
            section(
                "实习期休假",
                "连续实习满六个月后开放带薪休假额度；不足六个月可以申请无薪事假。",
                rule("annual_leave.days", 5, "实习生年假", "连续实习满六个月的实习生每年可享 5 天带薪休假。", ["实习生年假", "intern leave"], "天"),
            )
        ],
    },
    {
        "doc_id": "travel_cn_2024",
        "title": "中国区差旅与住宿标准（2024 版）",
        "family": "business_travel",
        "version": "1.0",
        "start": "2024-01-01",
        "end": "2024-12-31",
        "regions": ["CN"],
        "employees": ["all"],
        "authority": 70,
        "sections": [
            section(
                "餐饮补贴",
                "中国境内出差按自然日计算餐饮额度，已由客户提供餐食的对应餐次不得重复报销。",
                rule("travel.meal_limit", 150, "中国区餐补", "2024 年中国境内出差餐饮补贴上限为每天 150 元。", ["餐补", "饭补", "伙食费"], "CNY/天"),
            ),
            section(
                "住宿标准",
                "一线城市酒店费用按每晚含税价格审核，超标需要成本中心负责人事前批准。",
                rule("travel.hotel_tier1", 600, "一线城市酒店上限", "2024 年中国一线城市住宿上限为每晚 600 元。", ["酒店", "住宿", "一线城市"], "CNY/晚"),
            ),
            section("交通工具", "员工应优先选择公共交通。夜间到达或携带重要设备时可以使用合规网约车。"),
        ],
    },
    {
        "doc_id": "travel_cn_2025",
        "title": "中国区差旅与住宿标准（2025 版）",
        "family": "business_travel",
        "version": "2.0",
        "start": "2025-01-01",
        "end": None,
        "regions": ["CN"],
        "employees": ["all"],
        "authority": 70,
        "sections": [
            section(
                "餐饮补贴",
                "中国境内出差采用按日限额、凭票报销方式；客户已提供的餐食应从当天报销中扣除。",
                rule("travel.meal_limit", 200, "中国区餐补", "自 2025 年起，中国境内出差餐饮报销上限为每天 200 元。", ["餐补", "饭补", "伙食费"], "CNY/天"),
            ),
            section(
                "住宿标准",
                "一线城市和其他城市分别设置住宿上限，价格均按含税金额计算。",
                rule("travel.hotel_tier1", 750, "一线城市酒店上限", "2025 年中国一线城市住宿上限为每晚 750 元。", ["酒店", "住宿", "一线城市"], "CNY/晚"),
                rule("travel.hotel_other", 500, "其他城市酒店上限", "2025 年中国其他城市住宿上限为每晚 500 元。", ["酒店", "住宿", "非一线"], "CNY/晚"),
            ),
            section(
                "夜间交通",
                "员工因工作在深夜出发或到达时，可以在安全优先原则下使用出租车或合规网约车。",
                rule("travel.late_taxi_after", "22:00", "夜间打车时间", "工作差旅在 22:00 后可直接乘坐出租车或合规网约车。", ["打车", "出租车", "网约车", "夜间"]),
            ),
        ],
    },
    {
        "doc_id": "travel_gb_2025",
        "title": "UK Business Travel Standard 2025",
        "family": "business_travel",
        "version": "1.0",
        "start": "2025-01-01",
        "end": None,
        "regions": ["GB"],
        "employees": ["all"],
        "authority": 70,
        "sections": [
            section(
                "Meals",
                "Employees travelling inside the United Kingdom may claim actual meal costs up to the daily cap. Alcohol is excluded.",
                rule("travel.meal_limit", 45, "UK meal allowance", "The UK business-travel meal cap is GBP 45 per day.", ["meal allowance", "food expenses", "UK travel"], "GBP/day"),
            ),
            section(
                "London accommodation",
                "The cap applies to the room rate including mandatory taxes. Conference hotels need prior approval when above the cap.",
                rule("travel.hotel_london", 180, "London hotel cap", "The London accommodation cap is GBP 180 per night.", ["London hotel", "accommodation"], "GBP/night"),
            ),
        ],
    },
    {
        "doc_id": "remote_global_2024",
        "title": "混合办公制度（2024—2025 版）",
        "family": "remote_work",
        "version": "1.0",
        "start": "2024-01-01",
        "end": "2025-12-31",
        "regions": ["ALL"],
        "employees": ["full_time"],
        "authority": 50,
        "sections": [
            section(
                "每周远程额度",
                "通过试用期的正式员工可以申请固定远程办公日，团队协作日必须到办公室。",
                rule("remote.days_per_week", 2, "每周远程天数", "2024—2025 版制度允许每周最多远程办公 2 天。", ["远程办公", "居家办公", "WFH"], "天/周"),
            ),
            section("工作环境", "员工必须使用公司设备和批准的网络连接，不得在公共场所处理受限数据。"),
        ],
    },
    {
        "doc_id": "remote_global_2026",
        "title": "混合办公制度（2026 版）",
        "family": "remote_work",
        "version": "2.0",
        "start": "2026-01-01",
        "end": None,
        "regions": ["ALL"],
        "employees": ["full_time"],
        "authority": 50,
        "sections": [
            section(
                "每周远程额度",
                "正式员工在满足团队现场协作要求时，可以由经理按季度批准远程办公安排。",
                rule("remote.days_per_week", 3, "每周远程天数", "自 2026 年起，正式员工每周最多可远程办公 3 天。", ["远程办公", "居家办公", "WFH"], "天/周"),
            ),
            section("跨境限制", "远程办公地点跨越雇佣所在国家时，员工须提前三十天提交税务和信息安全评估。"),
        ],
    },
    {
        "doc_id": "remote_cn_secure_2024",
        "title": "中国区受限岗位远程办公补充条款",
        "family": "remote_work",
        "version": "1.0",
        "start": "2024-01-01",
        "end": None,
        "regions": ["CN"],
        "employees": ["secure_role"],
        "authority": 80,
        "sections": [
            section(
                "受限岗位",
                "能够接触未脱敏生产数据、核心密钥或安全运营平台的岗位执行更严格的现场要求。",
                rule("remote.days_per_week", 1, "受限岗位远程天数", "中国区受限岗位每周最多远程办公 1 天。", ["受限岗位", "安全岗位", "生产数据"], "天/周"),
            )
        ],
    },
    {
        "doc_id": "retention_2024",
        "title": "业务数据保留标准（2024 版）",
        "family": "data_retention",
        "version": "1.0",
        "start": "2024-01-01",
        "end": "2024-12-31",
        "regions": ["ALL"],
        "employees": ["all"],
        "authority": 85,
        "sections": [
            section(
                "客户会话",
                "客服聊天正文和附件自会话关闭之日起计时；法律保全标记可以暂停删除。",
                rule("retention.customer_chat_days", 180, "客户会话保留期", "2024 版标准要求客户聊天记录保留 180 天。", ["聊天记录", "客户对话", "会话数据"], "天"),
            ),
            section(
                "应用日志",
                "生产应用日志进入集中日志平台，期满后自动删除。安全事件证据按单独保全流程处理。",
                rule("retention.app_log_days", 365, "应用日志保留期", "2024 版标准要求生产应用日志保留 365 天。", ["日志", "log", "生产日志"], "天"),
            ),
        ],
    },
    {
        "doc_id": "retention_2025",
        "title": "业务数据最小化与保留标准（2025 版）",
        "family": "data_retention",
        "version": "2.0",
        "start": "2025-01-01",
        "end": None,
        "regions": ["ALL"],
        "employees": ["all"],
        "authority": 85,
        "sections": [
            section(
                "客户会话",
                "客服聊天正文与普通附件应最小化保存。欺诈调查或法律保全需要通过工单设置例外。",
                rule("retention.customer_chat_days", 90, "客户会话保留期", "自 2025 年起，普通客户聊天记录保留 90 天。", ["聊天记录", "客户对话", "会话数据"], "天"),
            ),
            section(
                "应用日志",
                "生产应用日志默认只保留诊断所需字段，含直接标识符的字段必须提前脱敏。",
                rule("retention.app_log_days", 180, "应用日志保留期", "自 2025 年起，生产应用日志默认保留 180 天。", ["日志", "log", "生产日志"], "天"),
            ),
            section(
                "人事档案",
                "劳动合同、薪酬变更和离职记录按法务保留表管理。",
                rule("retention.hr_years", 7, "人事档案保留期", "核心人事档案在劳动关系结束后保留 7 年。", ["人事档案", "劳动合同", "HR records"], "年"),
            ),
        ],
    },
    {
        "doc_id": "incident_2024",
        "title": "生产事件响应手册（2024 版）",
        "family": "incident_response",
        "version": "1.0",
        "start": "2024-01-01",
        "end": "2024-12-31",
        "regions": ["ALL"],
        "employees": ["all"],
        "authority": 90,
        "sections": [
            section(
                "P1 首次响应",
                "值班工程师收到 P1 告警后必须在规定时间内确认并进入事件频道。",
                rule("incident.p1_ack_minutes", 15, "P1 确认时限", "2024 年 P1 事件必须在 15 分钟内确认。", ["P1", "首次响应", "ack", "确认告警"], "分钟"),
            ),
            section(
                "复盘时限",
                "事件负责人需要形成包含时间线、根因和行动项的无责复盘文档。",
                rule("incident.postmortem_days", 5, "复盘提交时限", "2024 年 P1/P2 事件复盘须在恢复后 5 个工作日内提交。", ["复盘", "postmortem", "根因分析"], "工作日"),
            ),
        ],
    },
    {
        "doc_id": "incident_2025",
        "title": "生产事件响应手册（2025 版）",
        "family": "incident_response",
        "version": "2.0",
        "start": "2025-01-01",
        "end": None,
        "regions": ["ALL"],
        "employees": ["all"],
        "authority": 90,
        "sections": [
            section(
                "P1 首次响应",
                "P1 告警触发后，主值班人需要确认告警、声明事件级别并拉起事件指挥。",
                rule("incident.p1_ack_minutes", 10, "P1 确认时限", "自 2025 年起，P1 事件必须在 10 分钟内确认。", ["P1", "首次响应", "ack", "确认告警"], "分钟"),
            ),
            section(
                "复盘时限",
                "事件关闭前必须指定复盘负责人，复盘应记录可验证的行动项和完成日期。",
                rule("incident.postmortem_days", 3, "复盘提交时限", "自 2025 年起，P1/P2 事件复盘须在恢复后 3 个工作日内提交。", ["复盘", "postmortem", "根因分析"], "工作日"),
            ),
        ],
    },
    {
        "doc_id": "learning_cn_2024",
        "title": "中国区学习发展预算（2024 版）",
        "family": "learning_budget",
        "version": "1.0",
        "start": "2024-01-01",
        "end": "2024-12-31",
        "regions": ["CN"],
        "employees": ["full_time"],
        "authority": 60,
        "sections": [
            section(
                "正式员工额度",
                "通过试用期的正式员工可以用于课程、考试和专业书籍，设备不在报销范围内。",
                rule("learning.annual_budget", 5000, "年度学习预算", "2024 年中国区正式员工学习预算为每年 5000 元。", ["学习经费", "培训预算", "课程报销"], "CNY/年"),
            )
        ],
    },
    {
        "doc_id": "learning_cn_2025",
        "title": "中国区学习发展预算（2025 版）",
        "family": "learning_budget",
        "version": "2.0",
        "start": "2025-01-01",
        "end": None,
        "regions": ["CN"],
        "employees": ["full_time"],
        "authority": 60,
        "sections": [
            section(
                "正式员工额度",
                "正式员工可将预算用于岗位相关课程、行业会议、认证考试与专业书籍。单笔超过三千元须事前审批。",
                rule("learning.annual_budget", 8000, "年度学习预算", "2025 年中国区正式员工学习预算提高到每年 8000 元。", ["学习经费", "培训预算", "课程报销"], "CNY/年"),
            ),
            section(
                "认证考试重考",
                "同一认证首次考试可以正常报销；未通过后的重考仅承担部分费用。",
                rule("learning.retake_percent", 50, "重考报销比例", "认证考试重考最多报销费用的 50%。", ["重考", "考试没过", "retake"], "%"),
            ),
        ],
    },
    {
        "doc_id": "learning_intern_cn_2025",
        "title": "中国区实习生学习预算补充规定",
        "family": "learning_budget",
        "version": "1.0",
        "start": "2025-01-01",
        "end": None,
        "regions": ["CN"],
        "employees": ["intern"],
        "authority": 70,
        "sections": [
            section(
                "实习生额度",
                "连续实习三个月以上的实习生可申请岗位相关课程，申请需要导师确认。",
                rule("learning.annual_budget", 2000, "实习生学习预算", "中国区实习生年度学习预算为 2000 元。", ["实习生培训", "实习学习经费"], "CNY/年"),
            )
        ],
    },
    {
        "doc_id": "expense_cn_2024",
        "title": "中国区费用报销规则（2024 版）",
        "family": "expense",
        "version": "1.0",
        "start": "2024-01-01",
        "end": "2024-12-31",
        "regions": ["CN"],
        "employees": ["all"],
        "authority": 75,
        "sections": [
            section(
                "发票要求",
                "达到门槛的费用必须提供合规发票；门槛以下仍需提供支付记录和用途说明。",
                rule("expense.receipt_threshold", 100, "发票门槛", "2024 年单笔费用达到 100 元时必须提供发票。", ["发票", "小票", "凭证"], "CNY"),
            ),
            section(
                "提交期限",
                "费用应从交易发生日开始计算提交期限，跨年度费用仍受本条限制。",
                rule("expense.submission_days", 30, "报销提交期限", "2024 年费用须在发生后 30 天内提交报销。", ["报销期限", "多久提交", "expense claim"], "天"),
            ),
        ],
    },
    {
        "doc_id": "expense_cn_2025",
        "title": "中国区费用报销规则（2025 版）",
        "family": "expense",
        "version": "2.0",
        "start": "2025-01-01",
        "end": None,
        "regions": ["CN"],
        "employees": ["all"],
        "authority": 75,
        "sections": [
            section(
                "发票要求",
                "达到门槛的费用必须上传发票原件或电子发票；拆分交易规避门槛视为违规。",
                rule("expense.receipt_threshold", 50, "发票门槛", "自 2025 年起，单笔费用达到 50 元就必须提供发票。", ["发票", "小票", "凭证"], "CNY"),
            ),
            section(
                "提交期限",
                "员工应及时提交费用，逾期申请需要部门负责人和财务共同批准。",
                rule("expense.submission_days", 15, "报销提交期限", "自 2025 年起，费用须在发生后 15 天内提交报销。", ["报销期限", "多久提交", "expense claim"], "天"),
            ),
        ],
    },
    {
        "doc_id": "access_global_2024",
        "title": "账号与权限生命周期标准（2024 版）",
        "family": "access_control",
        "version": "1.0",
        "start": "2024-01-01",
        "end": "2024-12-31",
        "regions": ["ALL"],
        "employees": ["all"],
        "authority": 90,
        "sections": [
            section(
                "离职回收",
                "人力资源系统发出离职事件后，身份平台必须在服务目标内冻结账号并撤销会话。",
                rule("access.offboarding_hours", 4, "离职权限回收", "2024 年员工离职后须在 4 小时内完成账号和权限回收。", ["离职", "账号回收", "权限撤销"], "小时"),
            ),
            section(
                "生产权限审批",
                "长期生产写权限需要业务负责人和系统所有者共同审批，并按季度复核。",
                rule("access.production_approvers", 2, "生产权限审批人数", "生产写权限需要 2 名不同角色的审批人。", ["生产权限", "审批人", "prod access"], "人"),
            ),
        ],
    },
    {
        "doc_id": "access_global_2025",
        "title": "账号与权限生命周期标准（2025 版）",
        "family": "access_control",
        "version": "2.0",
        "start": "2025-01-01",
        "end": None,
        "regions": ["ALL"],
        "employees": ["all"],
        "authority": 90,
        "sections": [
            section(
                "离职回收",
                "离职事件进入身份平台后自动冻结主账号，高风险系统由系统所有者确认二次撤销。",
                rule("access.offboarding_hours", 1, "离职权限回收", "自 2025 年起，普通员工离职后须在 1 小时内完成权限回收。", ["离职", "账号回收", "权限撤销"], "小时"),
            ),
            section(
                "生产权限审批",
                "生产写权限必须有职责分离的双人审批，紧急权限最长保留八小时。",
                rule("access.production_approvers", 2, "生产权限审批人数", "生产写权限仍需要 2 名不同角色的审批人。", ["生产权限", "审批人", "prod access"], "人"),
            ),
        ],
    },
    {
        "doc_id": "access_contractor_2025",
        "title": "外包人员账号回收补充标准",
        "family": "access_control",
        "version": "1.0",
        "start": "2025-01-01",
        "end": None,
        "regions": ["ALL"],
        "employees": ["contractor"],
        "authority": 95,
        "sections": [
            section(
                "合同终止",
                "外包人员合同终止时间应由供应商负责人提前录入；到期触发自动冻结。",
                rule("access.offboarding_hours", "0.5", "外包账号回收", "外包人员合同终止后须在 30 分钟内完成权限回收。", ["外包离场", "供应商账号", "contractor offboarding"], "小时"),
            )
        ],
    },
    {
        "doc_id": "procurement_2024",
        "title": "采购审批矩阵（2024 版）",
        "family": "procurement",
        "version": "1.0",
        "start": "2024-01-01",
        "end": "2024-12-31",
        "regions": ["ALL"],
        "employees": ["all"],
        "authority": 80,
        "sections": [
            section(
                "经理审批门槛",
                "采购申请达到门槛后须由成本中心经理审批，申请人不得代替审批人操作。",
                rule("procurement.manager_threshold", 5000, "经理审批门槛", "2024 年采购金额达到 5000 元时需要经理审批。", ["采购审批", "经理审批", "买设备"], "CNY"),
            ),
            section(
                "财务复核门槛",
                "大额采购还需财务控制团队复核预算和供应商信息。",
                rule("procurement.finance_threshold", 50000, "财务复核门槛", "采购金额达到 50000 元时需要财务复核。", ["财务复核", "大额采购"], "CNY"),
            ),
        ],
    },
    {
        "doc_id": "procurement_2025",
        "title": "采购审批矩阵（2025 版）",
        "family": "procurement",
        "version": "2.0",
        "start": "2025-01-01",
        "end": None,
        "regions": ["ALL"],
        "employees": ["all"],
        "authority": 80,
        "sections": [
            section(
                "经理审批门槛",
                "为加强成本控制，达到较低门槛的采购也需要成本中心经理在下单前审批。",
                rule("procurement.manager_threshold", 3000, "经理审批门槛", "自 2025 年起，采购金额达到 3000 元就需要经理审批。", ["采购审批", "经理审批", "买设备"], "CNY"),
            ),
            section(
                "财务复核门槛",
                "财务控制团队负责检查预算、合同和供应商准入状态。",
                rule("procurement.finance_threshold", 30000, "财务复核门槛", "自 2025 年起，采购金额达到 30000 元需要财务复核。", ["财务复核", "大额采购"], "CNY"),
            ),
        ],
    },
    {
        "doc_id": "parental_cn_2025",
        "title": "中国区育儿假公司福利",
        "family": "parental_leave",
        "version": "1.0",
        "start": "2025-01-01",
        "end": None,
        "regions": ["CN"],
        "employees": ["full_time"],
        "authority": 70,
        "sections": [
            section(
                "公司额外育儿假",
                "本福利为公司提供的额外带薪额度，员工所在地法定待遇更高时按更高标准执行。",
                rule("parental.company_paid_days", 10, "公司额外育儿假", "中国区正式员工每年可申请 10 天公司带薪育儿假。", ["育儿假", "陪护孩子", "parental leave"], "天"),
            )
        ],
    },
    {
        "doc_id": "parental_gb_2025",
        "title": "UK Enhanced Parental Leave Benefit",
        "family": "parental_leave",
        "version": "1.0",
        "start": "2025-01-01",
        "end": None,
        "regions": ["GB"],
        "employees": ["full_time"],
        "authority": 70,
        "sections": [
            section(
                "Enhanced paid leave",
                "The company enhancement is available after twelve months of continuous service and operates alongside statutory entitlements.",
                rule("parental.company_paid_weeks", 6, "UK enhanced parental leave", "Eligible UK employees receive 6 weeks of company-paid parental leave.", ["parental leave", "UK family leave"], "weeks"),
            )
        ],
    },
    {
        "doc_id": "gift_finance_2025",
        "title": "客户礼品费用控制通知",
        "family": "expense",
        "version": "1.0",
        "start": "2025-01-01",
        "end": None,
        "regions": ["CN"],
        "employees": ["all"],
        "authority": 75,
        "sections": [
            section(
                "客户礼品",
                "财务通知要求礼品具有明确业务目的，并在费用系统中登记收礼方。",
                rule("expense.client_gift_limit", 300, "客户礼品上限", "客户礼品单人单次上限为 300 元。", ["客户礼物", "商务礼品", "gift"], "CNY"),
            )
        ],
    },
    {
        "doc_id": "gift_sales_2025",
        "title": "销售团队客户礼品操作指引",
        "family": "expense",
        "version": "1.0",
        "start": "2025-01-01",
        "end": None,
        "regions": ["CN"],
        "employees": ["all"],
        "authority": 75,
        "sections": [
            section(
                "客户礼品",
                "销售指引要求在客户关系系统记录礼品用途和批准人。",
                rule("expense.client_gift_limit", 500, "客户礼品上限", "销售客户礼品单人单次上限为 500 元。", ["客户礼物", "商务礼品", "gift"], "CNY"),
            )
        ],
    },
]


CASES: list[dict[str, Any]] = [
    {"queries": ["2024 年正式员工一年有多少天带薪年假？", "旧版制度里 annual leave entitlement 是多少？"], "as_of": "2024-06-01", "region": "CN", "employee": "full_time", "doc": "leave_global_2023", "key": "annual_leave.days", "value": "10", "tags": ["temporal", "leave"]},
    {"queries": ["2025 年正式员工的年假额度是多少？", "新制度一年给几天带薪休假？"], "as_of": "2025-06-01", "region": "CN", "employee": "full_time", "doc": "leave_global_2025", "key": "annual_leave.days", "value": "12", "tags": ["temporal", "leave"]},
    {"queries": ["2024 年没休完的年假最多能顺延几天？", "旧政策年假结转上限是多少？"], "as_of": "2024-11-01", "region": "CN", "employee": "full_time", "doc": "leave_global_2023", "key": "annual_leave.carryover", "value": "3", "tags": ["temporal", "alias"]},
    {"queries": ["2025 版年假最多可以结转多少天？", "今年剩余带薪假能 carry over 几天？"], "as_of": "2025-11-01", "region": "CN", "employee": "full_time", "doc": "leave_global_2025", "key": "annual_leave.carryover", "value": "5", "tags": ["temporal", "alias"]},
    {"queries": ["2024 年结转年假最晚什么时候用完？", "旧规顺延的假到哪天失效？"], "as_of": "2024-09-01", "region": "CN", "employee": "full_time", "doc": "leave_global_2023", "key": "annual_leave.carryover_deadline", "value": "03-31", "tags": ["temporal"]},
    {"queries": ["2025 新规结转年假使用截止日是什么时候？", "新版剩余年假几月几日前要用掉？"], "as_of": "2025-09-01", "region": "CN", "employee": "full_time", "doc": "leave_global_2025", "key": "annual_leave.carryover_deadline", "value": "06-30", "tags": ["temporal"]},
    {"queries": ["中国区十年以上工龄员工有几天年假？", "老员工累计工龄满十年休假额度多少？"], "as_of": "2025-08-01", "region": "CN", "employee": "full_time", "doc": "leave_cn_service_2025", "key": "annual_leave.long_service_days", "value": "15", "tags": ["scope", "leave"]},
    {"queries": ["英国正式员工 2025 年有多少天 holiday？", "What is the annual leave entitlement for a UK employee?"], "as_of": "2025-08-01", "region": "GB", "employee": "full_time", "doc": "leave_gb_2025", "key": "annual_leave.days", "value": "25", "tags": ["scope", "cross_lingual"]},
    {"queries": ["英国员工最多能 carry over 几天假？", "UK 年假可以结转多少天？"], "as_of": "2025-08-01", "region": "GB", "employee": "full_time", "doc": "leave_gb_2025", "key": "annual_leave.carryover", "value": "8", "tags": ["scope", "cross_lingual"]},
    {"queries": ["实习半年后有几天带薪休假？", "intern 能拿到多少天年假？"], "as_of": "2025-08-01", "region": "CN", "employee": "intern", "doc": "leave_intern_2025", "key": "annual_leave.days", "value": "5", "tags": ["scope", "alias"]},
    {"queries": ["2024 年国内出差一天饭补上限多少？", "旧差旅标准伙食费每天能报多少？"], "as_of": "2024-06-01", "region": "CN", "employee": "full_time", "doc": "travel_cn_2024", "key": "travel.meal_limit", "value": "150", "tags": ["temporal", "alias"]},
    {"queries": ["2025 年中国境内出差餐补一天多少？", "新规一天饭钱最多报销多少？"], "as_of": "2025-06-01", "region": "CN", "employee": "full_time", "doc": "travel_cn_2025", "key": "travel.meal_limit", "value": "200", "tags": ["temporal", "alias"]},
    {"queries": ["2024 年一线城市酒店每晚最多报多少？", "旧版北上广深住宿标准是多少？"], "as_of": "2024-06-01", "region": "CN", "employee": "full_time", "doc": "travel_cn_2024", "key": "travel.hotel_tier1", "value": "600", "tags": ["temporal"]},
    {"queries": ["2025 年一线城市住宿上限是多少？", "新版差旅酒店一晚最多报多少？"], "as_of": "2025-06-01", "region": "CN", "employee": "full_time", "doc": "travel_cn_2025", "key": "travel.hotel_tier1", "value": "750", "tags": ["temporal"]},
    {"queries": ["去非一线城市出差酒店限额多少？", "2025 年其他城市住宿能报多少？"], "as_of": "2025-06-01", "region": "CN", "employee": "full_time", "doc": "travel_cn_2025", "key": "travel.hotel_other", "value": "500", "tags": ["scope"]},
    {"queries": ["差旅晚上几点以后可以直接打车？", "深夜抵达从什么时间起能坐网约车？"], "as_of": "2025-06-01", "region": "CN", "employee": "full_time", "doc": "travel_cn_2025", "key": "travel.late_taxi_after", "value": "22:00", "tags": ["alias"]},
    {"queries": ["What is the daily meal cap for UK business travel?", "英国出差一天吃饭最多报多少英镑？"], "as_of": "2025-06-01", "region": "GB", "employee": "full_time", "doc": "travel_gb_2025", "key": "travel.meal_limit", "value": "45", "tags": ["scope", "cross_lingual"]},
    {"queries": ["London hotel allowance per night?", "伦敦出差住宿一晚上限多少？"], "as_of": "2025-06-01", "region": "GB", "employee": "full_time", "doc": "travel_gb_2025", "key": "travel.hotel_london", "value": "180", "tags": ["scope", "cross_lingual"]},
    {"queries": ["2025 年每周能在家办公几天？", "旧版混合办公一周允许几天 WFH？"], "as_of": "2025-05-01", "region": "CN", "employee": "full_time", "doc": "remote_global_2024", "key": "remote.days_per_week", "value": "2", "tags": ["temporal", "alias"]},
    {"queries": ["2026 年新制度每周能远程几天？", "新版居家办公额度是多少？"], "as_of": "2026-05-01", "region": "CN", "employee": "full_time", "doc": "remote_global_2026", "key": "remote.days_per_week", "value": "3", "tags": ["temporal", "alias"]},
    {"queries": ["中国区能看生产数据的受限岗位一周能远程几天？", "安全敏感岗位的 WFH 上限是多少？"], "as_of": "2025-05-01", "region": "CN", "employee": "secure_role", "doc": "remote_cn_secure_2024", "key": "remote.days_per_week", "value": "1", "tags": ["scope", "hard_negative"]},
    {"queries": ["2024 年客户聊天记录要留多久？", "旧数据标准保存客服会话多少天？"], "as_of": "2024-05-01", "region": "CN", "employee": "full_time", "doc": "retention_2024", "key": "retention.customer_chat_days", "value": "180", "tags": ["temporal"]},
    {"queries": ["2025 年普通客户对话保留多少天？", "新规聊天记录多久自动删除？"], "as_of": "2025-05-01", "region": "CN", "employee": "full_time", "doc": "retention_2025", "key": "retention.customer_chat_days", "value": "90", "tags": ["temporal", "alias"]},
    {"queries": ["2024 版生产日志保存期是多少？", "旧政策 app log 留几年？"], "as_of": "2024-05-01", "region": "CN", "employee": "full_time", "doc": "retention_2024", "key": "retention.app_log_days", "value": "365", "tags": ["temporal", "cross_lingual"]},
    {"queries": ["2025 年应用日志默认留多久？", "新数据标准 production logs retention 是多少天？"], "as_of": "2025-05-01", "region": "CN", "employee": "full_time", "doc": "retention_2025", "key": "retention.app_log_days", "value": "180", "tags": ["temporal", "cross_lingual"]},
    {"queries": ["员工离职后核心人事档案保存几年？", "劳动合同在 employment ended 后留多久？"], "as_of": "2025-05-01", "region": "CN", "employee": "full_time", "doc": "retention_2025", "key": "retention.hr_years", "value": "7", "tags": ["cross_lingual"]},
    {"queries": ["2024 年 P1 告警要几分钟内确认？", "旧响应手册 P1 ack SLA 是多少？"], "as_of": "2024-04-01", "region": "CN", "employee": "full_time", "doc": "incident_2024", "key": "incident.p1_ack_minutes", "value": "15", "tags": ["temporal", "cross_lingual"]},
    {"queries": ["2025 年 P1 首次响应时限几分钟？", "新手册严重事故多久必须 acknowledge？"], "as_of": "2025-04-01", "region": "CN", "employee": "full_time", "doc": "incident_2025", "key": "incident.p1_ack_minutes", "value": "10", "tags": ["temporal", "alias"]},
    {"queries": ["2024 年事故恢复后几天交复盘？", "旧版 postmortem deadline 是多少工作日？"], "as_of": "2024-04-01", "region": "CN", "employee": "full_time", "doc": "incident_2024", "key": "incident.postmortem_days", "value": "5", "tags": ["temporal"]},
    {"queries": ["2025 年 P1 复盘最晚几天提交？", "新规根因分析报告期限多久？"], "as_of": "2025-04-01", "region": "CN", "employee": "full_time", "doc": "incident_2025", "key": "incident.postmortem_days", "value": "3", "tags": ["temporal", "alias"]},
    {"queries": ["2024 年中国正式员工培训预算多少？", "旧版学习经费一年有多少钱？"], "as_of": "2024-07-01", "region": "CN", "employee": "full_time", "doc": "learning_cn_2024", "key": "learning.annual_budget", "value": "5000", "tags": ["temporal"]},
    {"queries": ["2025 年正式员工学习预算是多少？", "今年课程和证书最多报销多少钱？"], "as_of": "2025-07-01", "region": "CN", "employee": "full_time", "doc": "learning_cn_2025", "key": "learning.annual_budget", "value": "8000", "tags": ["temporal", "alias"]},
    {"queries": ["中国实习生一年有多少培训经费？", "intern 可以报销多少学习课程？"], "as_of": "2025-07-01", "region": "CN", "employee": "intern", "doc": "learning_intern_cn_2025", "key": "learning.annual_budget", "value": "2000", "tags": ["scope", "cross_lingual"]},
    {"queries": ["认证考试没过，重考能报销百分之多少？", "retake fee 公司承担多少比例？"], "as_of": "2025-07-01", "region": "CN", "employee": "full_time", "doc": "learning_cn_2025", "key": "learning.retake_percent", "value": "50", "tags": ["alias", "cross_lingual"]},
    {"queries": ["2024 年多少钱以上必须开发票？", "旧报销规则单笔达到多少要凭证？"], "as_of": "2024-03-01", "region": "CN", "employee": "full_time", "doc": "expense_cn_2024", "key": "expense.receipt_threshold", "value": "100", "tags": ["temporal"]},
    {"queries": ["2025 年单笔费用多少元起要发票？", "新规多少钱的小票必须上传？"], "as_of": "2025-03-01", "region": "CN", "employee": "full_time", "doc": "expense_cn_2025", "key": "expense.receipt_threshold", "value": "50", "tags": ["temporal", "alias"]},
    {"queries": ["2024 年费用发生后多少天内报销？", "旧规则 expense claim deadline 多久？"], "as_of": "2024-03-01", "region": "CN", "employee": "full_time", "doc": "expense_cn_2024", "key": "expense.submission_days", "value": "30", "tags": ["temporal"]},
    {"queries": ["2025 年报销最晚几天提交？", "新规费用发生后多久过期？"], "as_of": "2025-03-01", "region": "CN", "employee": "full_time", "doc": "expense_cn_2025", "key": "expense.submission_days", "value": "15", "tags": ["temporal"]},
    {"queries": ["2024 年普通员工离职后几小时撤权？", "旧标准 offboarding 多久锁账号？"], "as_of": "2024-02-01", "region": "CN", "employee": "full_time", "doc": "access_global_2024", "key": "access.offboarding_hours", "value": "4", "tags": ["temporal", "cross_lingual"]},
    {"queries": ["2025 年员工离职后多久回收权限？", "新版账号回收 SLA 是几小时？"], "as_of": "2025-02-01", "region": "CN", "employee": "full_time", "doc": "access_global_2025", "key": "access.offboarding_hours", "value": "1", "tags": ["temporal", "alias"]},
    {"queries": ["外包人员合同结束后几分钟要封账号？", "contractor offboarding 的权限撤销 SLA？"], "as_of": "2025-02-01", "region": "CN", "employee": "contractor", "doc": "access_contractor_2025", "key": "access.offboarding_hours", "value": "0.5", "tags": ["scope", "hard_negative"]},
    {"queries": ["生产写权限需要几个人审批？", "prod access 要几个 approver？"], "as_of": "2025-02-01", "region": "CN", "employee": "full_time", "doc": "access_global_2025", "key": "access.production_approvers", "value": "2", "tags": ["cross_lingual"]},
    {"queries": ["2024 年采购多少钱开始要经理批？", "旧采购矩阵 manager approval threshold？"], "as_of": "2024-04-01", "region": "CN", "employee": "full_time", "doc": "procurement_2024", "key": "procurement.manager_threshold", "value": "5000", "tags": ["temporal"]},
    {"queries": ["2025 年买设备超过多少钱找经理审批？", "新版采购经理审批门槛是多少？"], "as_of": "2025-04-01", "region": "CN", "employee": "full_time", "doc": "procurement_2025", "key": "procurement.manager_threshold", "value": "3000", "tags": ["temporal", "alias"]},
    {"queries": ["2024 年大额采购多少钱需要财务复核？", "旧版 finance review threshold 是多少？"], "as_of": "2024-04-01", "region": "CN", "employee": "full_time", "doc": "procurement_2024", "key": "procurement.finance_threshold", "value": "50000", "tags": ["temporal"]},
    {"queries": ["2025 年采购金额多少会进财务复核？", "新矩阵大额采购的财务门槛？"], "as_of": "2025-04-01", "region": "CN", "employee": "full_time", "doc": "procurement_2025", "key": "procurement.finance_threshold", "value": "30000", "tags": ["temporal"]},
    {"queries": ["中国正式员工公司额外给几天育儿假？", "陪护孩子的 company paid leave 是多少天？"], "as_of": "2025-06-01", "region": "CN", "employee": "full_time", "doc": "parental_cn_2025", "key": "parental.company_paid_days", "value": "10", "tags": ["scope", "cross_lingual"]},
    {"queries": ["How many weeks of enhanced parental leave do UK employees get?", "英国公司额外带薪育儿假有几周？"], "as_of": "2025-06-01", "region": "GB", "employee": "full_time", "doc": "parental_gb_2025", "key": "parental.company_paid_weeks", "value": "6", "tags": ["scope", "cross_lingual"]},
]


UNANSWERABLE = [
    ("公司给员工报销宠物保险吗？", "2025-06-01", "CN", "full_time", ["out_of_domain"]),
    ("办公室停车位每月多少钱？", "2025-06-01", "CN", "full_time", ["missing_policy"]),
    ("可以用学习预算买显示器吗，具体限额多少？", "2025-06-01", "CN", "full_time", ["missing_rule"]),
    ("美国区出差餐补是多少美元？", "2025-06-01", "US", "full_time", ["missing_scope"]),
    ("2022 年年假有多少天？", "2022-06-01", "CN", "full_time", ["missing_time"]),
    ("公司股票期权归属周期是什么？", "2025-06-01", "CN", "full_time", ["out_of_domain"]),
    ("办公室咖啡机坏了找谁？", "2025-06-01", "GB", "full_time", ["out_of_domain"]),
    ("合同工能否申请育儿假，额度多少？", "2025-06-01", "CN", "contractor", ["missing_scope"]),
    ("数据备份应该保留多少年？", "2025-06-01", "CN", "full_time", ["missing_rule"]),
    ("海外远程办公最多连续多少天？", "2026-06-01", "CN", "full_time", ["missing_rule"]),
    ("客户礼品单人单次上限到底是多少？", "2025-06-01", "CN", "full_time", ["conflict"]),
    ("销售送客户礼物最多能花多少钱？", "2025-06-01", "CN", "full_time", ["conflict"]),
]


def render_document(doc: dict[str, Any]) -> str:
    metadata = [
        "---",
        f"doc_id: {doc['doc_id']}",
        f"title: {doc['title']}",
        f"policy_family: {doc['family']}",
        f"version: \"{doc['version']}\"",
        f"effective_from: {doc['start']}",
        f"effective_to: {doc['end'] if doc['end'] else 'null'}",
        f"regions: {json.dumps(doc['regions'], ensure_ascii=False)}",
        f"employee_types: {json.dumps(doc['employees'], ensure_ascii=False)}",
        f"authority: {doc['authority']}",
        "---",
        "",
        f"# {doc['title']}",
        "",
        "本文件属于 VeriPolicy-RAG 的虚构企业制度基准语料，仅用于工程演示与评测。",
    ]
    for item in doc["sections"]:
        metadata.extend(["", f"## {item['title']}", ""])
        for item_rule in item["rules"]:
            metadata.append(f"<!-- rule: {json.dumps(item_rule, ensure_ascii=False)} -->")
        metadata.extend(["", item["prose"]])
    return "\n".join(metadata).strip() + "\n"


def build_queries() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    counter = 1
    for case_index, case in enumerate(CASES):
        for variant_index, query in enumerate(case["queries"]):
            # One phrasing per rule calibrates thresholds; the held-out paraphrase is the test item.
            split = "dev" if variant_index == 0 else "test"
            rows.append(
                {
                    "query_id": f"q{counter:03d}",
                    "split": split,
                    "query": query,
                    "as_of": case["as_of"],
                    "region": case["region"],
                    "employee_type": case["employee"],
                    "answerable": True,
                    "relevant_doc_ids": [case["doc"]],
                    "relevant_rule_key": case["key"],
                    "expected_value": case["value"],
                    "tags": case["tags"],
                }
            )
            counter += 1
    for index, (query, as_of, region, employee, tags) in enumerate(UNANSWERABLE):
        rows.append(
            {
                "query_id": f"q{counter:03d}",
                "split": "dev" if index % 2 == 0 else "test",
                "query": query,
                "as_of": as_of,
                "region": region,
                "employee_type": employee,
                "answerable": False,
                "relevant_doc_ids": [],
                "relevant_rule_key": "expense.client_gift_limit" if "conflict" in tags else None,
                "expected_value": None,
                "tags": tags,
            }
        )
        counter += 1
    return rows


def main() -> None:
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    EVAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    expected_paths = {CORPUS_DIR / f"{doc['doc_id']}.md" for doc in DOCS}
    unknown_paths = set(CORPUS_DIR.glob("*.md")) - expected_paths
    if unknown_paths:
        names = ", ".join(sorted(path.name for path in unknown_paths))
        raise RuntimeError(
            "Refusing to regenerate because data/corpus contains non-sample Markdown files: " + names
        )
    for doc in DOCS:
        path = CORPUS_DIR / f"{doc['doc_id']}.md"
        path.write_text(render_document(doc), encoding="utf-8")
    queries = build_queries()
    with EVAL_PATH.open("w", encoding="utf-8") as handle:
        for row in queries:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {
                "documents": len(DOCS),
                "queries": len(queries),
                "dev": sum(row["split"] == "dev" for row in queries),
                "test": sum(row["split"] == "test" for row in queries),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
