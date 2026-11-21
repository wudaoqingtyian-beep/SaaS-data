# -*- coding: utf-8 -*-
"""
Phase 1 测试：模拟数据生成测试

使用临时 SQLite 数据库，避免污染正式 data/app.db。
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import DB_PATH, SEED, START_DATE, END_DATE, TARGET_CUSTOMERS, TARGET_USAGE_WEEKLY
from src.database import init_database, get_all_table_counts
from src.data_generator import generate_all_data
from src.data_validation import validate_all


def _make_temp_conn():
    """创建一个临时 SQLite 连接用于测试，避免污染正式数据库。"""
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(tmp_fd)
    tmp_path_obj = Path(tmp_path)
    conn = init_database(tmp_path_obj, reset=True)
    return conn, tmp_path_obj


def _insert_customers(conn, customers):
    conn.executemany("""
        INSERT OR IGNORE INTO customers
        (customer_id, company_name, industry, company_size, region, plan_type,
         licensed_users, signup_date, contract_start_date, contract_end_date,
         monthly_fee, account_owner, created_at)
        VALUES (:customer_id, :company_name, :industry, :company_size, :region, :plan_type,
                :licensed_users, :signup_date, :contract_start_date, :contract_end_date,
                :monthly_fee, :account_owner, :created_at)
    """, customers)


def _insert_support_tickets(conn, tickets):
    conn.executemany("""
        INSERT OR IGNORE INTO support_tickets
        (ticket_id, customer_id, created_at, category, priority, status, channel,
         subject, first_response_at, resolved_at, satisfaction_score)
        VALUES (:ticket_id, :customer_id, :created_at, :category, :priority, :status,
                :channel, :subject, :first_response_at, :resolved_at, :satisfaction_score)
    """, tickets)


def _insert_followup_records(conn, followups):
    conn.executemany("""
        INSERT OR IGNORE INTO followup_records
        (followup_id, customer_id, followup_date, followup_type, trigger_reason,
         action_description, result_status, result_note, created_at)
        VALUES (:followup_id, :customer_id, :followup_date, :followup_type, :trigger_reason,
                :action_description, :result_status, :result_note, :created_at)
    """, followups)
def _insert_usage_weekly(conn, usage):
    conn.executemany("""
        INSERT OR IGNORE INTO usage_weekly
        (customer_id, week_start, login_count, active_days, active_users,
         core_feature_users, core_feature_uses, usage_minutes)
        VALUES (:customer_id, :week_start, :login_count, :active_days, :active_users,
                :core_feature_users, :core_feature_uses, :usage_minutes)
    """, usage)


def test_database_creates_all_tables():
    """测试 1：数据库能够正常创建四张表及其字段。"""
    conn, tmp_path = _make_temp_conn()
    try:
        tables = ["customers", "usage_weekly", "support_tickets", "followup_records"]
        for table in tables:
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            )
            assert cur.fetchone() is not None, f"表 {table} 不存在"

        cur = conn.execute("PRAGMA table_info(customers)")
        cols = {row["name"] for row in cur.fetchall()}
        required = {"customer_id", "company_name", "industry", "company_size",
                    "region", "plan_type", "licensed_users", "signup_date",
                    "contract_start_date", "contract_end_date", "monthly_fee",
                    "account_owner", "created_at"}
        assert required.issubset(cols), f"customers 缺少字段：{required - cols}"

        cur = conn.execute("PRAGMA table_info(usage_weekly)")
        cols = {row["name"] for row in cur.fetchall()}
        required = {"usage_id", "customer_id", "week_start", "login_count",
                    "active_days", "active_users", "core_feature_users",
                    "core_feature_uses", "usage_minutes"}
        assert required.issubset(cols), f"usage_weekly 缺少字段：{required - cols}"

        cur = conn.execute("PRAGMA table_info(support_tickets)")
        cols = {row["name"] for row in cur.fetchall()}
        required = {"ticket_id", "customer_id", "created_at", "category",
                    "priority", "status", "channel", "subject",
                    "first_response_at", "resolved_at", "satisfaction_score"}
        assert required.issubset(cols), f"support_tickets 缺少字段：{required - cols}"

        cur = conn.execute("PRAGMA table_info(followup_records)")
        cols = {row["name"] for row in cur.fetchall()}
        required = {"followup_id", "customer_id", "followup_date", "followup_type",
                    "trigger_reason", "action_description", "result_status",
                    "result_note", "created_at"}
        assert required.issubset(cols), f"followup_records 缺少字段：{required - cols}"

        cur = conn.execute("PRAGMA foreign_keys")
        assert cur.fetchone()[0] == 1, "外键约束未启用"
    finally:
        conn.close()
        tmp_path.unlink(missing_ok=True)


def test_mock_data_counts():
    """测试 3：模拟数据数量符合预期。"""
    conn, tmp_path = _make_temp_conn()
    try:
        data = generate_all_data(seed=SEED)
        _insert_customers(conn, data["customers_clean"])
        _insert_usage_weekly(conn, data["usage_weekly"])
        _insert_support_tickets(conn, data["support_tickets"])
        _insert_followup_records(conn, data["followup_records"])
        conn.commit()

        counts = get_all_table_counts(conn)
        assert counts["customers"] == TARGET_CUSTOMERS, f"customers 数量：{counts['customers']}"
        assert counts["usage_weekly"] == TARGET_USAGE_WEEKLY, f"usage_weekly 数量：{counts['usage_weekly']}"
        assert 300 <= counts["support_tickets"] <= 500, f"support_tickets 数量：{counts['support_tickets']}"
        assert 40 <= counts["followup_records"] <= 60, f"followup_records 数量：{counts['followup_records']}"
    finally:
        conn.close()
        tmp_path.unlink(missing_ok=True)

def test_seed_reproducibility():
    """测试 4：固定随机种子生成结果具有可重复性。"""
    data1 = generate_all_data(seed=SEED)
    data2 = generate_all_data(seed=SEED)
    assert data1["customers_clean"] == data2["customers_clean"], "客户数据不可重复"
    assert data1["usage_weekly"] == data2["usage_weekly"], "使用数据不可重复"
    assert data1["support_tickets"] == data2["support_tickets"], "工单数据不可重复"
    assert data1["followup_records"] == data2["followup_records"], "跟进数据不可重复"


def test_persona_distribution():
    """测试：四类客户数量符合比例。"""
    data = generate_all_data(seed=SEED)
    counts = data["persona_counts"]
    total = sum(counts.values())
    assert total == TARGET_CUSTOMERS, f"客户总数不符：{total}"
    assert counts.get("healthy", 0) == 60, f"healthy 数量：{counts.get('healthy', 0)}"
    assert counts.get("declining_usage", 0) == 18, f"declining_usage 数量：{counts.get('declining_usage', 0)}"
    assert counts.get("low_adoption", 0) == 12, f"low_adoption 数量：{counts.get('low_adoption', 0)}"
    assert counts.get("service_friction", 0) == 10, f"service_friction 数量：{counts.get('service_friction', 0)}"


def test_usage_data_constraints():
    """测试 5：客户使用数据满足字段约束。"""
    conn, tmp_path = _make_temp_conn()
    try:
        data = generate_all_data(seed=SEED)
        _insert_customers(conn, data["customers_clean"])
        _insert_usage_weekly(conn, data["usage_weekly"])
        conn.commit()

        cur = conn.execute("SELECT COUNT(*) AS cnt FROM usage_weekly WHERE active_days < 0 OR active_days > 7")
        assert cur.fetchone()["cnt"] == 0

        cur = conn.execute("""
            SELECT COUNT(*) AS cnt FROM usage_weekly u
            JOIN customers c ON u.customer_id = c.customer_id
            WHERE u.active_users > c.licensed_users
        """)
        assert cur.fetchone()["cnt"] == 0

        cur = conn.execute("SELECT COUNT(*) AS cnt FROM usage_weekly WHERE core_feature_users > active_users")
        assert cur.fetchone()["cnt"] == 0

        cur = conn.execute("""
            SELECT COUNT(*) AS cnt FROM usage_weekly
            WHERE login_count < 0 OR active_users < 0 OR core_feature_users < 0
               OR core_feature_uses < 0 OR usage_minutes < 0
        """)
        assert cur.fetchone()["cnt"] == 0

        cur = conn.execute("""
            SELECT COUNT(*) AS cnt FROM usage_weekly
            WHERE active_days = 0
              AND (active_users != 0 OR login_count != 0 OR core_feature_uses != 0 OR usage_minutes != 0)
        """)
        assert cur.fetchone()["cnt"] == 0
    finally:
        conn.close()
        tmp_path.unlink(missing_ok=True)

def test_ticket_time_logic():
    """测试 6：工单时间和状态符合业务逻辑。"""
    conn, tmp_path = _make_temp_conn()
    try:
        data = generate_all_data(seed=SEED)
        _insert_customers(conn, data["customers_clean"])
        _insert_support_tickets(conn, data["support_tickets"])
        conn.commit()

        cur = conn.execute("""
            SELECT COUNT(*) AS cnt FROM support_tickets
            WHERE first_response_at IS NOT NULL AND first_response_at < created_at
        """)
        assert cur.fetchone()["cnt"] == 0

        cur = conn.execute("""
            SELECT COUNT(*) AS cnt FROM support_tickets
            WHERE resolved_at IS NOT NULL AND resolved_at < created_at
        """)
        assert cur.fetchone()["cnt"] == 0

        cur = conn.execute("""
            SELECT COUNT(*) AS cnt FROM support_tickets
            WHERE status IN ('open', 'in_progress') AND resolved_at IS NOT NULL
        """)
        assert cur.fetchone()["cnt"] == 0

        cur = conn.execute("""
            SELECT COUNT(*) AS cnt FROM support_tickets
            WHERE satisfaction_score IS NOT NULL AND (satisfaction_score < 1 OR satisfaction_score > 5)
        """)
        assert cur.fetchone()["cnt"] == 0
    finally:
        conn.close()
        tmp_path.unlink(missing_ok=True)


def test_foreign_key_relationships():
    """测试 7：外键关系正确。"""
    conn, tmp_path = _make_temp_conn()
    try:
        data = generate_all_data(seed=SEED)
        _insert_customers(conn, data["customers_clean"])
        _insert_usage_weekly(conn, data["usage_weekly"])
        _insert_support_tickets(conn, data["support_tickets"])
        _insert_followup_records(conn, data["followup_records"])
        conn.commit()

        violations = conn.execute("PRAGMA foreign_key_check").fetchall()
        assert len(violations) == 0, f"外键违规：{violations}"
    finally:
        conn.close()
        tmp_path.unlink(missing_ok=True)

def test_data_validation_catches_anomalies():
    """测试 8：数据质量检查能够识别异常数据。"""
    conn, tmp_path = _make_temp_conn()
    try:
        conn.execute("""
            INSERT INTO customers (customer_id, company_name, industry, company_size, region,
                                   plan_type, licensed_users, signup_date, contract_start_date,
                                   contract_end_date, monthly_fee, account_owner, created_at)
            VALUES ('CUST9999', '测试企业', '制造业', 'small', '华东', 'basic', 10,
                    '2026-01-01', '2026-01-01', '2027-01-01', 1000.0, '测试专员', '2026-01-01T00:00:00')
        """)
        # active_users = 15 > licensed_users = 10，违反业务规则但不违反数据库 CHECK 约束
        conn.execute("""
            INSERT INTO usage_weekly (customer_id, week_start, login_count, active_days,
                                      active_users, core_feature_users, core_feature_uses, usage_minutes)
            VALUES ('CUST9999', '2026-08-10', 5, 3, 15, 2, 3, 100)
        """)
        conn.commit()

        result = validate_all(conn)
        assert not result["passed"], "应该检测到 active_users 超过 licensed_users 的异常"
        assert any("licensed_users" in e for e in result["errors"]), "应报告 active_users 超过 licensed_users 错误"
    finally:
        conn.close()
        tmp_path.unlink(missing_ok=True)


def test_existing_db_not_overwritten_without_reset():
    """测试 9：已存在数据库不会被意外覆盖（不带 --reset 时不会删除表）。"""
    conn, tmp_path = _make_temp_conn()
    try:
        conn2 = init_database(tmp_path, reset=False)
        counts_after = get_all_table_counts(conn2)
        assert counts_after["customers"] == 0
        conn2.close()
    finally:
        conn.close()
        tmp_path.unlink(missing_ok=True)