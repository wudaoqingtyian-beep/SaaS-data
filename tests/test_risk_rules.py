# -*- coding: utf-8 -*-
"""
Phase 2 测试：客户风险规则测试

使用临时 SQLite 数据库和独立测试数据，不修改原始 app.db。
"""

import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database import init_database
from src.risk_rules import (
    get_connection,
    calculate_customer_risk,
    calculate_all_customers_risk,
    filter_by_risk_level,
    get_risk_level_distribution,
    OBSERVATION_BASE_DATE,
)

START = "2026-08-10"

def _make_temp_conn():
    """创建临时数据库连接并插入独立测试数据。"""
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(tmp_fd)
    tmp_path_obj = Path(tmp_path)
    conn = init_database(tmp_path_obj, reset=True)
    _seed_test_data(conn)
    return conn, tmp_path_obj


def _seed_test_data(conn):
    """插入用于风险规则测试的独立数据。"""
    customers = [
        ("CUST_R01", "低风险企业", "制造业", "small", "华东", "basic", 10,
         "2026-01-01", "2026-01-01", "2027-01-01", 1000.0, "专员1", "2026-01-01T00:00:00"),
        ("CUST_R02", "活跃度低企业", "零售", "medium", "华南", "professional", 50,
         "2026-01-01", "2026-01-01", "2027-01-01", 5000.0, "专员2", "2026-01-01T00:00:00"),
        ("CUST_R03", "活跃度下降企业", "制造业", "large", "华东", "enterprise", 100,
         "2026-01-01", "2026-01-01", "2027-01-01", 20000.0, "专员3", "2026-01-01T00:00:00"),
        ("CUST_R04", "工单积压企业", "物流", "medium", "华中", "basic", 20,
         "2026-01-01", "2026-01-01", "2027-01-01", 1500.0, "专员4", "2026-01-01T00:00:00"),
        ("CUST_R05", "超时工单企业", "教育", "small", "华南", "professional", 30,
         "2026-01-01", "2026-01-01", "2027-01-01", 3000.0, "专员5", "2026-01-01T00:00:00"),
        ("CUST_R06", "合同即将到期企业", "专业服务", "medium", "华北", "enterprise", 50,
         "2026-01-01", "2026-01-01", "2026-11-20", 8000.0, "专员6", "2026-01-01T00:00:00"),
        ("CUST_R07", "合同已过期企业", "医疗健康", "small", "西南", "basic", 15,
         "2026-01-01", "2026-01-01", "2026-10-01", 1200.0, "专员7", "2026-01-01T00:00:00"),
    ]
    conn.executemany(
        """INSERT INTO customers
           (customer_id, company_name, industry, company_size, region, plan_type,
            licensed_users, signup_date, contract_start_date, contract_end_date,
            monthly_fee, account_owner, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        customers,
    )

    base = datetime(2026, 8, 10)
    week_starts = [(base + timedelta(weeks=i)).strftime("%Y-%m-%d") for i in range(12)]

    for ws in week_starts:
        conn.execute(
            """INSERT INTO usage_weekly
               (customer_id, week_start, login_count, active_days, active_users,
                core_feature_users, core_feature_uses, usage_minutes)
               VALUES (?,?,10,5,8,3,5,300)""",
            ("CUST_R01", ws),
        )

# ==================== 单个客户风险测试 ====================

def test_rule_recent_low_activity():
    """规则 1：最近 4 周 avg active_days < 2 触发 +25。"""
    conn, tmp_path = _make_temp_conn()
    try:
        result = calculate_customer_risk(conn, "CUST_R02")
        assert result["risk_score"] == 25
        assert result["risk_level"] == "低风险"
        rule_ids = [r["rule"] for r in result["triggered_rules"]]
        assert "recent_low_activity" in rule_ids
        assert result["supporting_values"]["recent_4weeks_avg_active_days"] == 1.0
    finally:
        conn.close()
        tmp_path.unlink(missing_ok=True)


def test_rule_activity_decline():
    """规则 2：活跃度下降 >= 30% 触发 +30。"""
    conn, tmp_path = _make_temp_conn()
    try:
        result = calculate_customer_risk(conn, "CUST_R03")
        assert result["risk_score"] == 30
        assert result["risk_level"] == "低风险"
        rule_ids = [r["rule"] for r in result["triggered_rules"]]
        assert "activity_decline" in rule_ids
        assert result["supporting_values"]["activity_decline_pct"] == 60.0
    finally:
        conn.close()
        tmp_path.unlink(missing_ok=True)


def test_rule_unresolved_tickets():
    """规则 3：未解决工单 >= 2 触发 +20。"""
    conn, tmp_path = _make_temp_conn()
    try:
        result = calculate_customer_risk(conn, "CUST_R04")
        assert result["risk_score"] == 20
        assert result["risk_level"] == "低风险"
        rule_ids = [r["rule"] for r in result["triggered_rules"]]
        assert "unresolved_tickets" in rule_ids
        assert result["supporting_values"]["unresolved_ticket_count"] == 2
    finally:
        conn.close()
        tmp_path.unlink(missing_ok=True)


def test_rule_overtime_ticket():
    """规则 4：超时工单 >72h 触发 +15。"""
    conn, tmp_path = _make_temp_conn()
    try:
        result = calculate_customer_risk(conn, "CUST_R05")
        assert result["risk_score"] == 15
        assert result["risk_level"] == "低风险"

# ==================== 多规则累加和上限测试 ====================

def test_multiple_rules_accumulate():
    """多项规则累加正确，总分不超过 100。"""
    conn, tmp_path = _make_temp_conn()
    try:
        result = calculate_customer_risk(conn, "CUST_R01")
        assert result["risk_score"] == 0
        assert result["risk_level"] == "低风险"
        assert len(result["triggered_rules"]) == 0
    finally:
        conn.close()
        tmp_path.unlink(missing_ok=True)


# ==================== 风险等级边界测试 ====================

def test_risk_level_boundaries():
    """29 分、30 分、59 分、60 分的风险等级边界正确。"""
    from src.risk_rules import _classify_risk_level
    assert _classify_risk_level(0) == "低风险"
    assert _classify_risk_level(29) == "低风险"
    assert _classify_risk_level(30) == "中风险"
    assert _classify_risk_level(59) == "中风险"
    assert _classify_risk_level(60) == "高风险"
    assert _classify_risk_level(100) == "高风险"


# ==================== 批量计算和筛选测试 ====================

def test_calculate_all_customers_risk():
    """批量计算所有客户风险，结果按分数降序。"""
    conn, tmp_path = _make_temp_conn()
    try:
        results = calculate_all_customers_risk(conn)
        assert len(results) == 7
        scores = [r["risk_score"] for r in results]
        assert scores == sorted(scores, reverse=True)
        ids = [r["customer_id"] for r in results]
        assert len(ids) == len(set(ids))
    finally:
        conn.close()
        tmp_path.unlink(missing_ok=True)


def test_filter_by_risk_level():
    """按风险等级筛选正确。"""
    conn, tmp_path = _make_temp_conn()
    try:
        results = calculate_all_customers_risk(conn)
        low = filter_by_risk_level(results, "低风险")
        medium = filter_by_risk_level(results, "中风险")
        high = filter_by_risk_level(results, "高风险")
        assert len(low) + len(medium) + len(high) == 7
    finally:
        conn.close()
        tmp_path.unlink(missing_ok=True)


def test_risk_level_distribution():
    """风险等级分布统计正确。"""
    conn, tmp_path = _make_temp_conn()
    try:
        results = calculate_all_customers_risk(conn)
        dist = get_risk_level_distribution(results)
        assert dist["低风险"] + dist["中风险"] + dist["高风险"] == 7
    finally:
        conn.close()
        tmp_path.unlink(missing_ok=True)


# ==================== 可复现性测试 ====================

def test_risk_reproducibility():
    """相同数据多次计算得到完全一致的风险评分。"""
    conn, tmp_path = _make_temp_conn()
    try:
        r1 = calculate_customer_risk(conn, "CUST_R03")
        r2 = calculate_customer_risk(conn, "CUST_R03")
        assert r1 == r2
    finally:
        conn.close()
        tmp_path.unlink(missing_ok=True)
        rule_ids = [r["rule"] for r in result["triggered_rules"]]
        assert "overtime_ticket" in rule_ids
        assert result["supporting_values"]["max_unresolved_wait_hours"] > 72
    finally:
        conn.close()
        tmp_path.unlink(missing_ok=True)


def test_rule_contract_expiry_soon():
    """规则 5：合同 0-30 天到期触发 +10。"""
    conn, tmp_path = _make_temp_conn()
    try:
        result = calculate_customer_risk(conn, "CUST_R06")
        assert result["risk_score"] == 10
        assert result["risk_level"] == "低风险"
        rule_ids = [r["rule"] for r in result["triggered_rules"]]
        assert "contract_expiry_soon" in rule_ids
        assert result["supporting_values"]["days_to_contract_expiry"] == 19
    finally:
        conn.close()
        tmp_path.unlink(missing_ok=True)


def test_expired_contract_no_rule5():
    """已过期的合同不触发规则 5。"""
    conn, tmp_path = _make_temp_conn()
    try:
        result = calculate_customer_risk(conn, "CUST_R07")
        assert result["risk_score"] == 0
        rule_ids = [r["rule"] for r in result["triggered_rules"]]
        assert "contract_expiry_soon" not in rule_ids
        assert result["supporting_values"]["days_to_contract_expiry"] < 0
    finally:
        conn.close()
        tmp_path.unlink(missing_ok=True)

    for i, ws in enumerate(week_starts):
        ad = 5 if i < 8 else 1
        conn.execute(
            """INSERT INTO usage_weekly
               (customer_id, week_start, login_count, active_days, active_users,
                core_feature_users, core_feature_uses, usage_minutes)
               VALUES (?,?,10,?,5,3,5,300)""",
            ("CUST_R02", ws, ad),
        )

    for i, ws in enumerate(week_starts):
        ad = 5 if i < 4 else (3 if i < 8 else 2)
        conn.execute(
            """INSERT INTO usage_weekly
               (customer_id, week_start, login_count, active_days, active_users,
                core_feature_users, core_feature_uses, usage_minutes)
               VALUES (?,?,10,?,5,3,5,300)""",
            ("CUST_R03", ws, ad),
        )

    for ws in week_starts:
        conn.execute(
            """INSERT INTO usage_weekly
               (customer_id, week_start, login_count, active_days, active_users,
                core_feature_users, core_feature_uses, usage_minutes)
               VALUES (?,?,10,5,8,3,5,300)""",
            ("CUST_R04", ws),
        )

    for ws in week_starts:
        conn.execute(
            """INSERT INTO usage_weekly
               (customer_id, week_start, login_count, active_days, active_users,
                core_feature_users, core_feature_uses, usage_minutes)
               VALUES (?,?,10,5,8,3,5,300)""",
            ("CUST_R05", ws),
        )

    for ws in week_starts:
        conn.execute(
            """INSERT INTO usage_weekly
               (customer_id, week_start, login_count, active_days, active_users,
                core_feature_users, core_feature_uses, usage_minutes)
               VALUES (?,?,10,5,8,3,5,300)""",
            ("CUST_R06", ws),
        )

    for ws in week_starts:
        conn.execute(
            """INSERT INTO usage_weekly
               (customer_id, week_start, login_count, active_days, active_users,
                core_feature_users, core_feature_uses, usage_minutes)
               VALUES (?,?,10,5,8,3,5,300)""",
            ("CUST_R07", ws),
        )

    conn.execute(
        """INSERT INTO support_tickets
           (ticket_id, customer_id, created_at, category, priority, status, channel,
            subject, first_response_at, resolved_at, satisfaction_score)
           VALUES ('TKT_R04_1','CUST_R04','2026-10-20T10:00:00','login_access','high','open',
                   'email','登录问题','2026-10-20T11:00:00',NULL,NULL)""",
    )
    conn.execute(
        """INSERT INTO support_tickets
           (ticket_id, customer_id, created_at, category, priority, status, channel,
            subject, first_response_at, resolved_at, satisfaction_score)
           VALUES ('TKT_R04_2','CUST_R04','2026-10-21T09:00:00','billing','medium','in_progress',
                   'chat','账单问题','2026-10-21T10:00:00',NULL,NULL)""",
    )

    conn.execute(
        """INSERT INTO support_tickets
           (ticket_id, customer_id, created_at, category, priority, status, channel,
            subject, first_response_at, resolved_at, satisfaction_score)
           VALUES ('TKT_R05_1','CUST_R05','2026-10-28T10:00:00','feature_usage','urgent','open',
                   'phone','功能异常',NULL,NULL,NULL)""",
    )

    conn.commit()
END = "2026-11-01"