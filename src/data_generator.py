# -*- coding: utf-8 -*-
"""
B2B SaaS 客户使用与服务运营分析平台 - 模拟数据生成模块
Phase 1：数据库与模拟数据开发

使用 Python 标准库 random 生成模拟业务数据。
固定随机种子 SEED = 42，保证可重复生成。
不调用外部 API，不使用真实企业数据。
"""

import random
import string
from datetime import date, datetime, timedelta
from typing import List, Dict, Tuple, Optional

from src.config import (
    SEED, START_DATE, NUM_WEEKS, END_DATE,
    TARGET_CUSTOMERS, TARGET_SUPPORT_TICKETS_MIN, TARGET_SUPPORT_TICKETS_MAX,
    TARGET_FOLLOWUP_RECORDS_MIN, TARGET_FOLLOWUP_RECORDS_MAX,
    PERSONA_HEALTHY, PERSONA_DECLINING, PERSONA_LOW_ADOPTION, PERSONA_SERVICE_FRICTION,
    PERSONA_RATIOS,
    INDUSTRIES, REGIONS, COMPANY_SIZES, PLAN_TYPES,
    TICKET_CATEGORIES, TICKET_PRIORITIES, TICKET_STATUSES, TICKET_CHANNELS,
    FOLLOWUP_TYPES, TRIGGER_REASONS, FOLLOWUP_STATUSES,
    PLAN_LICENSED_USERS_RANGE, PLAN_MONTHLY_FEE_RANGE,
    TICKETS_PER_CUSTOMER,
    DATE_FORMAT, DATETIME_FORMAT,
)

# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _random_date_in_window(start_date: date, end_date: date, rng: Optional[random.Random] = None) -> date:
    rnd = rng or random
    days = (end_date - start_date).days
    return start_date + timedelta(days=rnd.randint(0, days))


def _random_datetime_in_window(start_date: date, end_date: date, rng: Optional[random.Random] = None) -> str:
    rnd = rng or random
    d = _random_date_in_window(start_date, end_date, rnd)
    h = rnd.randint(8, 20)
    m = rnd.randint(0, 59)
    s = rnd.randint(0, 59)
    return datetime(d.year, d.month, d.day, h, m, s).strftime(DATETIME_FORMAT)


def _generate_week_starts(start_date_str: str, num_weeks: int) -> List[str]:
    """生成每周周一的日期列表（YYYY-MM-DD）。"""
    start = datetime.strptime(start_date_str, DATE_FORMAT).date()
    weekday = start.weekday()  # 0=周一
    if weekday != 0:
        start = start - timedelta(days=weekday)
    weeks = []
    for i in range(num_weeks):
        week_start = start + timedelta(weeks=i)
        weeks.append(week_start.strftime(DATE_FORMAT))
    return weeks

# ---------------------------------------------------------------------------
# 客户生成
# ---------------------------------------------------------------------------

def _assign_personas(num_customers: int, rng: random.Random) -> List[str]:
    """
    按 PERSONA_RATIOS 分配画像标签，返回长度为 num_customers 的列表。
    """
    counts = {}
    remaining = num_customers
    personas = list(PERSONA_RATIOS.keys())
    for i, p in enumerate(personas):
        if i == len(personas) - 1:
            counts[p] = remaining
        else:
            c = int(round(num_customers * PERSONA_RATIOS[p]))
            counts[p] = c
            remaining -= c

    labels = []
    for p, c in counts.items():
        labels.extend([p] * c)
    rng.shuffle(labels)
    return labels


def generate_customers(
    num_customers: int = TARGET_CUSTOMERS,
    seed: int = SEED,
) -> List[dict]:
    """
    生成客户基础数据。
    返回包含字典的列表，每个字典对应一行 customers 记录。
    """
    rng = random.Random(seed)
    personas = _assign_personas(num_customers, rng)

    customers = []
    start_date = datetime.strptime(START_DATE, DATE_FORMAT).date()

    for i in range(num_customers):
        customer_id = f"CUST{i+1:04d}"
        company_name = f"示例企业{i+1:03d}"
        industry = rng.choice(INDUSTRIES)
        company_size = rng.choice(COMPANY_SIZES)
        region = rng.choice(REGIONS)
        plan_type = rng.choice(PLAN_TYPES)

        lic_min, lic_max = PLAN_LICENSED_USERS_RANGE[plan_type]
        licensed_users = rng.randint(lic_min, lic_max)

        # 注册日期在观察窗口开始前 6 个月至观察窗口开始之间
        signup_start = start_date - timedelta(days=180)
        signup_date = _random_date_in_window(signup_start, start_date, rng).strftime(DATE_FORMAT)

        # 合同开始于注册日期或之后
        contract_start = _random_date_in_window(
            datetime.strptime(signup_date, DATE_FORMAT).date(),
            start_date,
            rng,
        ).strftime(DATE_FORMAT)

        # 合同到期：部分 0-30 天，部分 31-90 天，其余更晚
        end_of_window = datetime.strptime(END_DATE, DATE_FORMAT).date()
        expiry_choice = rng.random()
        if expiry_choice < 0.30:
            contract_end = _random_date_in_window(end_of_window, end_of_window + timedelta(days=30), rng).strftime(DATE_FORMAT)
        elif expiry_choice < 0.60:
            contract_end = _random_date_in_window(end_of_window + timedelta(days=31), end_of_window + timedelta(days=90), rng).strftime(DATE_FORMAT)
        else:
            contract_end = _random_date_in_window(end_of_window + timedelta(days=91), end_of_window + timedelta(days=365), rng).strftime(DATE_FORMAT)

        fee_min, fee_max = PLAN_MONTHLY_FEE_RANGE[plan_type]
        monthly_fee = round(rng.uniform(fee_min, fee_max), 2)

        account_owner = f"运营专员{rng.randint(1, 10)}"
        created_at = _random_datetime_in_window(signup_start, start_date, rng)

        customers.append({
            "customer_id": customer_id,
            "company_name": company_name,
            "industry": industry,
            "company_size": company_size,
            "region": region,
            "plan_type": plan_type,
            "licensed_users": licensed_users,
            "signup_date": signup_date,
            "contract_start_date": contract_start,
            "contract_end_date": contract_end,
            "monthly_fee": monthly_fee,
            "account_owner": account_owner,
            "created_at": created_at,
            "_persona": personas[i],
        })

    return customers

# ---------------------------------------------------------------------------
# usage_weekly 生成
# ---------------------------------------------------------------------------

def generate_usage_weekly(
    customers: List[dict],
    seed: int = SEED,
) -> List[dict]:
    """
    为每个客户每周生成一条使用记录，合计 TARGET_CUSTOMERS × NUM_WEEKS 条。
    根据客户画像生成不同的活跃度模式。
    """
    rng = random.Random(seed)
    week_starts = _generate_week_starts(START_DATE, NUM_WEEKS)

    records = []

    for cust in customers:
        customer_id = cust["customer_id"]
        licensed_users = cust["licensed_users"]
        persona = cust["_persona"]

        # 基准活跃度（按画像设定）
        if persona == PERSONA_HEALTHY:
            base_active_days = rng.randint(4, 6)
            base_active_ratio = rng.uniform(0.35, 0.80)
            decline = False
        elif persona == PERSONA_DECLINING:
            base_active_days = rng.randint(4, 6)
            base_active_ratio = rng.uniform(0.35, 0.80)
            decline = True
        elif persona == PERSONA_LOW_ADOPTION:
            base_active_days = rng.randint(0, 2)
            base_active_ratio = rng.uniform(0.10, 0.30)
            decline = False
        else:  # service_friction
            base_active_days = rng.randint(3, 5)
            base_active_ratio = rng.uniform(0.40, 0.70)
            decline = False

        for week_idx, week_start in enumerate(week_starts):
            # 计算本周 active_days（带随机波动）
            if decline:
                # 前 4 周接近 healthy，最后 4 周逐步下降
                if week_idx < 4:
                    active_days = base_active_days + rng.randint(-1, 1)
                else:
                    # 逐步下降：第 4-7 周（索引 4-7）逐渐降低
                    progress = (week_idx - 3) / 4.0  # 0.25, 0.5, 0.75, 1.0
                    drop = int(base_active_days * progress * rng.uniform(0.30, 0.60))
                    active_days = max(1, base_active_days - drop + rng.randint(-1, 1))
            else:
                active_days = max(0, min(7, base_active_days + rng.randint(-1, 1)))

            # active_days = 0 时，其他计数均为 0
            if active_days == 0:
                active_users = 0
                login_count = 0
                core_feature_users = 0
                core_feature_uses = 0
                usage_minutes = 0
            else:
                active_users = int(licensed_users * base_active_ratio * rng.uniform(0.8, 1.2))
                active_users = max(1, min(licensed_users, active_users))

                # 登录次数：active_days 的倍数，带波动
                login_count = active_days * rng.randint(1, 4) + rng.randint(0, 5)

                # 核心功能用户数
                core_ratio = rng.uniform(0.2, 0.7) if persona != PERSONA_LOW_ADOPTION else rng.uniform(0.05, 0.3)
                core_feature_users = int(active_users * core_ratio * rng.uniform(0.8, 1.2))
                core_feature_users = max(0, min(active_users, core_feature_users))

                # 核心功能使用次数
                core_feature_uses = core_feature_users * rng.randint(1, 5) + rng.randint(0, 10)

                # 总使用时长（分钟）
                usage_minutes = active_days * rng.randint(30, 120) + rng.randint(0, 100)

            records.append({
                "customer_id": customer_id,
                "week_start": week_start,
                "login_count": login_count,
                "active_days": active_days,
                "active_users": active_users,
                "core_feature_users": core_feature_users,
                "core_feature_uses": core_feature_uses,
                "usage_minutes": usage_minutes,
            })

    return records

# ---------------------------------------------------------------------------
# support_tickets 生成
# ---------------------------------------------------------------------------

def generate_support_tickets(
    customers: List[dict],
    seed: int = SEED,
) -> List[dict]:
    """
    生成技术支持工单，目标约 400 条。
    不同画像客户的工单数量和特征不同。
    """
    rng = random.Random(seed)
    start_date = datetime.strptime(START_DATE, DATE_FORMAT)
    end_date = datetime.strptime(END_DATE, DATE_FORMAT)

    tickets = []
    ticket_counter = 1

    for cust in customers:
        customer_id = cust["customer_id"]
        persona = cust["_persona"]

        tmin, tmax = TICKETS_PER_CUSTOMER[persona]
        num_tickets = rng.randint(tmin, tmax)

        for _ in range(num_tickets):
            ticket_id = f"TKT{ticket_counter:05d}"
            ticket_counter += 1

            created_at = _random_datetime_in_window(
                start_date.date(), end_date.date(), rng
            )

            category = rng.choice(TICKET_CATEGORIES)
            priority = rng.choice(TICKET_PRIORITIES)
            # service_friction 组高优先级比例略高
            if persona == PERSONA_SERVICE_FRICTION and rng.random() < 0.30:
                priority = rng.choice(["high", "urgent"])

            # 状态：resolved/closed 为主，open/in_progress 约 10%-20%
            status_rand = rng.random()
            if status_rand < 0.70:
                status = rng.choice(["resolved", "closed"])
            elif status_rand < 0.90:
                status = "in_progress"
            else:
                status = "open"

            channel = rng.choice(TICKET_CHANNELS)
            subject = f"虚构问题标题-{ticket_id}"

            # 首次响应时间
            first_response_at = None
            if status in ("in_progress", "resolved", "closed"):
                if rng.random() < 0.85:
                    # 响应时间在创建后 1-72 小时
                    resp_hours = rng.randint(1, 72)
                    resp_dt = datetime.strptime(created_at, DATETIME_FORMAT) + timedelta(hours=resp_hours)
                    # 不得超出观察窗口结束
                    max_dt = end_date + timedelta(days=1)
                    if resp_dt <= max_dt:
                        first_response_at = resp_dt.strftime(DATETIME_FORMAT)

            # 解决时间
            resolved_at = None
            satisfaction_score = None

            if status in ("resolved", "closed"):
                # 解决时间在首次响应后或创建后
                base_dt = first_response_at if first_response_at else created_at
                resolve_hours = rng.randint(2, 168)  # 2 小时到 7 天
                resolve_dt = datetime.strptime(base_dt, DATETIME_FORMAT) + timedelta(hours=resolve_hours)
                max_dt = end_date + timedelta(days=1)
                if resolve_dt <= max_dt:
                    resolved_at = resolve_dt.strftime(DATETIME_FORMAT)
                    status = "resolved" if status == "closed" and resolved_at else status
                    # 满意度：对 resolved/closed 抽样生成 1-5 分
                    if rng.random() < 0.70:
                        # service_friction 组评分偏低
                        if persona == PERSONA_SERVICE_FRICTION:
                            satisfaction_score = rng.choice([1, 2, 2, 3, 3, 4])
                        else:
                            satisfaction_score = rng.randint(1, 5)
                else:
                    # 超出观察窗口，设为未解决
                    resolved_at = None
                    status = "open"

            # 未解决工单 resolved_at 必须为 NULL，satisfaction_score 为 NULL
            if status in ("open", "in_progress"):
                resolved_at = None
                satisfaction_score = None

            tickets.append({
                "ticket_id": ticket_id,
                "customer_id": customer_id,
                "created_at": created_at,
                "category": category,
                "priority": priority,
                "status": status,
                "channel": channel,
                "subject": subject,
                "first_response_at": first_response_at,
                "resolved_at": resolved_at,
                "satisfaction_score": satisfaction_score,
            })

    return tickets

# ---------------------------------------------------------------------------
# followup_records 生成
# ---------------------------------------------------------------------------

def generate_followup_records(
    customers: List[dict],
    seed: int = SEED,
) -> List[dict]:
    """
    生成客户运营跟进记录，目标约 50 条。
    优先分配给 declining_usage、low_adoption、service_friction 客户。
    """
    rng = random.Random(seed)
    start_date = datetime.strptime(START_DATE, DATE_FORMAT)
    end_date = datetime.strptime(END_DATE, DATE_FORMAT)

    # 按画像筛选优先客户
    priority_personas = {PERSONA_DECLINING, PERSONA_LOW_ADOPTION, PERSONA_SERVICE_FRICTION}
    priority_customers = [c for c in customers if c["_persona"] in priority_personas]
    other_customers = [c for c in customers if c["_persona"] not in priority_personas]

    records = []
    followup_counter = 1

    # 为优先客户生成更多记录
    target_count = rng.randint(TARGET_FOLLOWUP_RECORDS_MIN, TARGET_FOLLOWUP_RECORDS_MAX)

    # 优先客户每人 0-2 条，普通客户每人 0-1 条
    all_candidates = priority_customers + other_customers
    rng.shuffle(all_candidates)

    action_templates = {
        "training": [
            "组织客户端核心功能产品培训，讲解常用操作流程。",
            "提供管理后台使用指南，重点介绍数据导出与报表功能。",
        ],
        "check_in": [
            "定期回访，了解客户近期产品使用情况和遇到的困难。",
            "电话回访，确认客户对当前服务的满意度。",
        ],
        "issue_resolution": [
            "协助客户处理反复出现的登录权限问题，已提交相关工单跟进。",
            "协调技术团队处理客户反馈的数据异常问题。",
        ],
        "product_guidance": [
            "指导客户使用核心功能模块，提升功能采用率。",
            "演示新版本功能，解答客户操作疑问。",
        ],
        "renewal_communication": [
            "就即将到期的合同与客户沟通续费事宜。",
            "介绍套餐升级方案和对应权益。",
        ],
    }

    reason_action_map = {
        "usage_decline": "training",
        "low_adoption": "product_guidance",
        "repeated_tickets": "issue_resolution",
        "overdue_ticket": "issue_resolution",
        "upcoming_renewal": "renewal_communication",
        "manual": "check_in",
    }

    for cust in all_candidates:
        if followup_counter > target_count:
            break

        if rng.random() < 0.75:  # 75% 概率生成跟进记录
            customer_id = cust["customer_id"]
            followup_date = _random_date_in_window(start_date.date(), end_date.date(), rng).strftime(DATE_FORMAT)
            followup_type = rng.choice(FOLLOWUP_TYPES)
            trigger_reason = rng.choice(TRIGGER_REASONS)

            # 根据触发原因建议跟进类型，但保留随机性
            if trigger_reason in reason_action_map and rng.random() < 0.6:
                followup_type = reason_action_map[trigger_reason]

            action_description = rng.choice(action_templates.get(followup_type, ["与客户进行沟通跟进。"]))
            result_status = rng.choice(FOLLOWUP_STATUSES)
            # completed 为主
            if rng.random() < 0.75:
                result_status = "completed"

            result_note = None
            if rng.random() < 0.5:
                result_note = "客户反馈积极，后续将继续跟踪。"

            created_at = _random_datetime_in_window(start_date.date(), end_date.date(), rng)

            records.append({
                "followup_id": followup_counter,
                "customer_id": customer_id,
                "followup_date": followup_date,
                "followup_type": followup_type,
                "trigger_reason": trigger_reason,
                "action_description": action_description,
                "result_status": result_status,
                "result_note": result_note,
                "created_at": created_at,
            })
            followup_counter += 1

    return records

# ---------------------------------------------------------------------------
# 总入口：生成所有数据（不含内部画像字段）
# ---------------------------------------------------------------------------

def generate_all_data(seed: int = SEED) -> dict:
    """
    生成所有模拟数据，返回字典：
    {
        "customers": [...],            # 内含 _persona 字段
        "customers_clean": [...],      # 去除 _persona，可写入数据库
        "usage_weekly": [...],
        "support_tickets": [...],
        "followup_records": [...],
        "persona_counts": {persona: count}
    }
    """
    customers = generate_customers(TARGET_CUSTOMERS, seed)

    persona_counts = {}
    for c in customers:
        p = c["_persona"]
        persona_counts[p] = persona_counts.get(p, 0) + 1

    customers_clean = [{k: v for k, v in c.items() if k != "_persona"} for c in customers]

    usage = generate_usage_weekly(customers, seed)
    tickets = generate_support_tickets(customers, seed)
    followups = generate_followup_records(customers, seed)

    return {
        "customers": customers,
        "customers_clean": customers_clean,
        "usage_weekly": usage,
        "support_tickets": tickets,
        "followup_records": followups,
        "persona_counts": persona_counts,
    }