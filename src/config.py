# -*- coding: utf-8 -*-
"""
B2B SaaS 客户使用与服务运营分析平台 - 配置模块
Phase 1：数据库与模拟数据开发

集中管理模拟数据配置、随机种子、日期范围和枚举值。
所有字段和变量使用英文 snake_case，供后续 SQL、Python、Streamlit 使用。
"""

from pathlib import Path

# ---------------- 项目基础路径 ----------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "app.db"

# ---------------- 随机种子 ----------------
SEED = 42

# ---------------- 模拟时间窗口 ----------------
# 12 周：2026-08-10（周一）至 2026-11-01（周日）
START_DATE = "2026-08-10"
NUM_WEEKS = 12
END_DATE = "2026-11-01"

# 目标数据量
TARGET_CUSTOMERS = 100
TARGET_USAGE_WEEKLY = 1200  # 100 客户 × 12 周
TARGET_SUPPORT_TICKETS_MIN = 300
TARGET_SUPPORT_TICKETS_MAX = 500
TARGET_FOLLOWUP_RECORDS_MIN = 40
TARGET_FOLLOWUP_RECORDS_MAX = 60

# ---------------- 客户行为画像比例 ----------------
PERSONA_HEALTHY = "healthy"
PERSONA_DECLINING = "declining_usage"
PERSONA_LOW_ADOPTION = "low_adoption"
PERSONA_SERVICE_FRICTION = "service_friction"

PERSONA_RATIOS = {
    PERSONA_HEALTHY: 0.60,      # 60 家
    PERSONA_DECLINING: 0.18,    # 18 家
    PERSONA_LOW_ADOPTION: 0.12, # 12 家
    PERSONA_SERVICE_FRICTION: 0.10,  # 10 家
}

# ---------------- 枚举值 ----------------
INDUSTRIES = [
    "制造业", "零售", "物流", "教育", "专业服务", "互联网", "医疗健康", "金融服务"
]

REGIONS = ["华东", "华南", "华北", "华中", "西南", "西北", "东北"]

COMPANY_SIZES = ["small", "medium", "large"]

PLAN_TYPES = ["basic", "professional", "enterprise"]

TICKET_CATEGORIES = [
    "login_access", "integration_api", "feature_usage",
    "data_issue", "billing", "performance", "other",
]

TICKET_PRIORITIES = ["low", "medium", "high", "urgent"]

TICKET_STATUSES = ["open", "in_progress", "resolved", "closed"]

TICKET_CHANNELS = ["email", "chat", "phone", "portal"]

FOLLOWUP_TYPES = [
    "training", "check_in", "issue_resolution",
    "product_guidance", "renewal_communication",
]

TRIGGER_REASONS = [
    "usage_decline", "low_adoption", "repeated_tickets",
    "overdue_ticket", "upcoming_renewal", "manual",
]

FOLLOWUP_STATUSES = ["planned", "completed", "cancelled"]

# ---------------- 套餐对应的授权用户数范围 ----------------
PLAN_LICENSED_USERS_RANGE = {
    "basic": (5, 30),
    "professional": (20, 100),
    "enterprise": (50, 200),
}

# ---------------- 套餐对应的月费范围（元） ----------------
PLAN_MONTHLY_FEE_RANGE = {
    "basic": (500, 3000),
    "professional": (3000, 12000),
    "enterprise": (12000, 50000),
}

# ---------------- 工单每客户数量范围（按画像） ----------------
TICKETS_PER_CUSTOMER = {
    PERSONA_HEALTHY: (2, 4),
    PERSONA_DECLINING: (3, 6),
    PERSONA_LOW_ADOPTION: (2, 4),
    PERSONA_SERVICE_FRICTION: (5, 8),
}

# ---------------- 支持的日期/时间格式 ----------------
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"