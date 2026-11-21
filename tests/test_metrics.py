# -*- coding: utf-8 -*-
"""
Phase 2 测试：经营指标分析测试

使用临时 SQLite 数据库和独立测试数据，不修改原始 app.db。
"""

import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database import init_database
from src.metrics import (
    get_connection,
    get_business_overview,
    get_weekly_activity_trend,
    get_avg_active_days_trend,
    get_login_count_stats,
    get_core_feature_usage_stats,
    get_activity_by_plan,
    get_activity_by_industry,
    get_customer_usage_trend,
    get_customer_active_days_comparison,
    get_ticket_category_distribution,
    get_ticket_priority_distribution,
    get_ticket_status_distribution,
    get_weekly_ticket_creation_trend,
    get_weekly_ticket_resolved_trend,
    get_avg_resolve_time_by_category,
    get_unresolved_ticket_details,
    get_ticket_wait_time_stats,
    get_group_analysis,
    OBSERVATION_BASE_DATE,
)

START = "2026-08-10"
END = "2026-11-01"


def _make_temp_conn():
    """创建临时数据库连接并插入独立测试数据。"""
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(tmp_fd)
    tmp_path_obj = Path(tmp_path)
    conn = init_database(tmp_path_obj, reset=True)
    _seed_test_data(conn)
    return conn, tmp_path_obj


def _seed_test_data(conn):
    """插入用于指标测试的独立数据。"""
    conn.executemany(
        """INSERT INTO customers
           (customer_id, company_name, industry, company_size, region, plan_type,
            licensed_users, signup_date, contract_start_date, contract_end_date,
            monthly_fee, account_owner, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        [
            ("CUST0001", "测试企业 A", "制造业", "small", "华东", "basic", 10,
             "2026-01-01", "2026-01-01", "2026-12-01", 1000.0, "专员1", "2026-01-01T00:00:00"),
            ("CUST0002", "测试企业 B", "零售", "medium", "华南", "professional", 50,
             "2026-01-01", "2026-01-01", "2026-11-15", 5000.0, "专员2", "2026-01-01T00:00:00"),
            ("CUST0003", "测试企业 C", "制造业", "large", "华东", "enterprise", 100,
             "2026-01-01", "2026-01-01", "2026-10-01", 20000.0, "专员3", "2026-01-01T00:00:00"),
        ],
    )
    base = datetime(2026, 8, 10)
    week_starts = [(base + timedelta(weeks=i)).strftime("%Y-%m-%d") for i in range(12)]
    usage_rows = []
    for cid in ["CUST0001", "CUST0002", "CUST0003"]:
        for ws in week_starts:
            usage_rows.append((cid, ws, 10, 5, 8, 3, 5, 300))
    conn.executemany(
        """INSERT INTO usage_weekly
           (customer_id, week_start, login_count, active_days, active_users,
            core_feature_users, core_feature_uses, usage_minutes)
           VALUES (?,?,?,?,?,?,?,?)""",
        usage_rows,
    )
    ticket_rows = [
        ("TKT00001", "CUST0001", "2026-08-15T10:00:00", "login_access", "high", "resolved",
         "email", "无法登录", "2026-08-15T12:00:00", "2026-08-16T10:00:00", 4),
        ("TKT00002", "CUST0002", "2026-08-20T09:00:00", "billing", "medium", "open",
         "chat", "账单问题", None, None, None),
        ("TKT00003", "CUST0003", "2026-08-25T08:00:00", "feature_usage", "urgent", "in_progress",
         "phone", "功能异常", "2026-08-25T10:00:00", None, None),
        ("TKT00004", "CUST0001", "2026-09-01T10:00:00", "data_issue", "low", "closed",
         "portal", "数据丢失", "2026-09-01T11:00:00", "2026-09-02T10:00:00", 5),
    ]
    conn.executemany(
        """INSERT INTO support_tickets
           (ticket_id, customer_id, created_at, category, priority, status, channel,
            subject, first_response_at, resolved_at, satisfaction_score)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        ticket_rows,
    )

# ==================== 经营总览指标测试 ====================

def test_business_overview_basic():
    """客户活跃率、核心功能采用率、工单解决率计算正确。"""
    conn, tmp_path = _make_temp_conn()
    try:
        result = get_business_overview(conn, START, END)
        assert result["total_customers"] == 3
        assert result["active_customers"] == 3
        assert result["active_rate"] == 100.0
        assert result["core_feature_customers"] == 3
        assert result["core_adoption_rate"] == 100.0
        assert result["total_tickets"] == 4
        assert result["unresolved_tickets"] == 2
        assert result["resolution_rate"] == 50.0
    finally:
        conn.close()
        tmp_path.unlink(missing_ok=True)


def test_avg_first_response_time():
    """平均首次响应时间正确（仅计算有 first_response_at 的工单）。"""
    conn, tmp_path = _make_temp_conn()
    try:
        result = get_business_overview(conn, START, END)
        assert result["avg_first_response_hours"] == 1.67
    finally:
        conn.close()
        tmp_path.unlink(missing_ok=True)


def test_avg_resolve_time_ignores_unresolved():
    """平均解决时间忽略未解决工单。"""
    conn, tmp_path = _make_temp_conn()
    try:
        result = get_business_overview(conn, START, END)
        assert result["avg_resolve_hours"] == 24.0
    finally:
        conn.close()
        tmp_path.unlink(missing_ok=True)


def test_avg_satisfaction_ignores_null():
    """平均满意度忽略 NULL。"""
    conn, tmp_path = _make_temp_conn()
    try:
        result = get_business_overview(conn, START, END)
        assert result["avg_satisfaction"] == 4.5
    finally:
        conn.close()
        tmp_path.unlink(missing_ok=True)


def test_zero_denominator_no_error():
    """分母为 0 时不会报错。"""
    conn, tmp_path = _make_temp_conn()
    try:

# ==================== 产品使用分析测试 ====================

def test_weekly_activity_trend():
    """每周活跃客户数趋势正确。"""
    conn, tmp_path = _make_temp_conn()
    try:
        df = get_weekly_activity_trend(conn, START, END)
        assert len(df) == 12
        assert (df["active_customer_count"] == 3).all()
    finally:
        conn.close()
        tmp_path.unlink(missing_ok=True)


def test_customer_active_days_comparison():
    """前后 4 周比较窗口正确。"""
    conn, tmp_path = _make_temp_conn()
    try:
        result = get_customer_active_days_comparison(conn, "CUST0001")
        assert result["first_4weeks_avg"] == 5.0
        assert result["last_4weeks_avg"] == 5.0
        assert result["comparable"] is True
        assert result["change_pct"] == 0.0
    finally:
        conn.close()
        tmp_path.unlink(missing_ok=True)


def test_customer_active_days_no_baseline():
    """前 4 周没有基线时不触发下降规则（change_pct 为 None）。"""
    conn, tmp_path = _make_temp_conn()
    try:
        conn.execute(
            """INSERT INTO customers
               (customer_id, company_name, industry, company_size, region, plan_type,
                licensed_users, signup_date, contract_start_date, contract_end_date,
                monthly_fee, account_owner, created_at)
               VALUES ('CUST0010', '测试企业 J', '制造业', 'small', '华东', 'basic', 10,
                       '2026-01-01', '2026-01-01', '2026-12-01', 1000.0, '专员1', '2026-01-01T00:00:00')"""
        )
        base = datetime(2026, 8, 10)
        for i in range(12):
            ws = (base + timedelta(weeks=i)).strftime("%Y-%m-%d")
            conn.execute(
                """INSERT INTO usage_weekly
                   (customer_id, week_start, login_count, active_days, active_users,
                    core_feature_users, core_feature_uses, usage_minutes)
                   VALUES (?,?,0,0,0,0,0,0)""",
                ("CUST0010", ws),
            )
        conn.commit()
        result = get_customer_active_days_comparison(conn, "CUST0010")
        assert result["first_4weeks_avg"] == 0.0
        assert result["comparable"] is False
        assert result["change_pct"] is None
    finally:
        conn.close()
        tmp_path.unlink(missing_ok=True)


# ==================== 工单分析测试 ====================

def test_ticket_category_distribution():
    """工单类别分布正确。"""
    conn, tmp_path = _make_temp_conn()
    try:
        df = get_ticket_category_distribution(conn, START, END)
        assert len(df) == 4
        assert df.loc[df["category"] == "login_access", "ticket_count"].iloc[0] == 1
    finally:
        conn.close()
        tmp_path.unlink(missing_ok=True)


def test_unresolved_ticket_details():
    """未解决工单明细正确。"""
    conn, tmp_path = _make_temp_conn()
    try:
        df = get_unresolved_ticket_details(conn)
        assert len(df) == 2
        assert set(df["status"].tolist()) == {"open", "in_progress"}
    finally:
        conn.close()
        tmp_path.unlink(missing_ok=True)


# ==================== 客户群体分析测试 ====================

def test_group_analysis_by_industry():
    """按行业分组统计正确。"""
    conn, tmp_path = _make_temp_conn()
    try:
        df = get_group_analysis(conn, "industry", START, END)
        mfg = df[df["group_value"] == "制造业"].iloc[0]
        assert mfg["customer_count"] == 2
        retail = df[df["group_value"] == "零售"].iloc[0]
        assert retail["customer_count"] == 1
    finally:
        conn.close()
        tmp_path.unlink(missing_ok=True)


def test_group_analysis_invalid_field():
    """不支持的分组字段应抛出错误。"""
    conn, tmp_path = _make_temp_conn()
    try:
        try:
            get_group_analysis(conn, "invalid_field")
            assert False, "应抛出 ValueError"
        except ValueError:
            pass
    finally:
        conn.close()
        tmp_path.unlink(missing_ok=True)
        result = get_business_overview(conn, "2025-01-01", "2025-01-02")
        assert result["total_tickets"] == 0
        assert result["resolution_rate"] == 0.0
        assert result["avg_first_response_hours"] == 0.0
        assert result["avg_resolve_hours"] == 0.0
        assert result["avg_satisfaction"] == 0.0
    finally:
        conn.close()
        tmp_path.unlink(missing_ok=True)


def test_date_filter_works():
    """时间筛选可以正常生效。"""
    conn, tmp_path = _make_temp_conn()
    try:
        result = get_business_overview(conn, "2026-08-10", "2026-08-16")
        assert result["active_customers"] == 3
    finally:
        conn.close()
        tmp_path.unlink(missing_ok=True)
    conn.executemany(
        """INSERT INTO support_tickets
           (ticket_id, customer_id, created_at, category, priority, status, channel,
            subject, first_response_at, resolved_at, satisfaction_score)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        ticket_rows,
    )
    conn.commit()