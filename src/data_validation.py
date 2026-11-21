# -*- coding: utf-8 -*-
"""
B2B SaaS 客户使用与服务运营分析平台 - 数据质量校验模块
Phase 1：数据库与模拟数据开发

实现自动化数据质量检查。任何校验失败都会明确报告，不静默忽略。
"""

import sqlite3
from typing import List, Optional
from pathlib import Path

from src.config import DB_PATH, START_DATE, END_DATE, TARGET_USAGE_WEEKLY


class ValidationError(Exception):
    """数据质量校验失败时抛出。"""
    pass

def validate_customer_ids_unique(conn: sqlite3.Connection) -> None:
    """客户 ID 不得重复。"""
    cur = conn.execute("""
        SELECT customer_id, COUNT(*) AS cnt
        FROM customers
        GROUP BY customer_id
        HAVING cnt > 1
    """)
    dups = cur.fetchall()
    if dups:
        raise ValidationError(f"客户 ID 重复：{[dict(d) for d in dups]}")


def validate_usage_unique_per_customer_week(conn: sqlite3.Connection) -> None:
    """每个客户每周最多一条使用记录。"""
    cur = conn.execute("""
        SELECT customer_id, week_start, COUNT(*) AS cnt
        FROM usage_weekly
        GROUP BY customer_id, week_start
        HAVING cnt > 1
    """)
    dups = cur.fetchall()
    if dups:
        raise ValidationError(f"存在重复的客户-周使用记录：{[dict(d) for d in dups]}")


def validate_usage_count(conn: sqlite3.Connection, expected: int = TARGET_USAGE_WEEKLY) -> None:
    """默认情况下使用记录应恰好等于目标数量。"""
    cur = conn.execute("SELECT COUNT(*) AS cnt FROM usage_weekly")
    row = cur.fetchone()
    actual = row["cnt"] if row else 0
    if actual != expected:
        raise ValidationError(
            f"usage_weekly 记录数量不符：期望 {expected}，实际 {actual}"
        )


def validate_foreign_keys(conn: sqlite3.Connection) -> None:
    """四张表的客户外键必须有效（PRAGMA foreign_key_check 无错误）。"""
    violations = conn.execute("PRAGMA foreign_key_check;").fetchall()
    if violations:
        raise ValidationError(f"外键约束违规：{[dict(v) for v in violations]}")


def validate_active_days_range(conn: sqlite3.Connection) -> None:
    """active_days 在 0 到 7 之间。"""
    cur = conn.execute("""
        SELECT usage_id, customer_id, week_start, active_days
        FROM usage_weekly
        WHERE active_days < 0 OR active_days > 7
    """)
    bad = cur.fetchall()
    if bad:
        raise ValidationError(f"active_days 超出 0-7 范围：{[dict(b) for b in bad]}")


def validate_active_users_vs_licensed(conn: sqlite3.Connection) -> None:
    """active_users 不超过授权用户数。"""
    cur = conn.execute("""
        SELECT u.usage_id, u.customer_id, u.week_start,
               u.active_users, c.licensed_users
        FROM usage_weekly u
        JOIN customers c ON u.customer_id = c.customer_id
        WHERE u.active_users > c.licensed_users
    """)
    bad = cur.fetchall()
    if bad:
        raise ValidationError(f"active_users 超过 licensed_users：{[dict(b) for b in bad]}")


def validate_core_feature_users_vs_active_users(conn: sqlite3.Connection) -> None:
    """core_feature_users 不超过 active_users。"""
    cur = conn.execute("""
        SELECT usage_id, customer_id, week_start,
               core_feature_users, active_users
        FROM usage_weekly
        WHERE core_feature_users > active_users
    """)
    bad = cur.fetchall()
    if bad:
        raise ValidationError(f"core_feature_users 超过 active_users：{[dict(b) for b in bad]}")


def validate_no_negative_counts(conn: sqlite3.Connection) -> None:
    """所有计数和时长不得为负数。"""
    tables_fields = {
        "usage_weekly": ["login_count", "active_days", "active_users",
                         "core_feature_users", "core_feature_uses", "usage_minutes"],
    }
    bad = []
    for table, fields in tables_fields.items():
        for field in fields:
            cur = conn.execute(f"SELECT COUNT(*) AS cnt FROM {table} WHERE {field} < 0")
            row = cur.fetchone()
            cnt = row["cnt"] if row else 0
            if cnt > 0:
                bad.append(f"{table}.{field}: {cnt} 条负值记录")
    if bad:
        raise ValidationError("存在负值计数/时长：" + "; ".join(bad))


def validate_all(
    conn: Optional[sqlite3.Connection] = None,
    db_path: Optional[Path] = None,
    expected_usage: int = TARGET_USAGE_WEEKLY,
) -> dict:
    """
    运行所有数据质量校验。

    :param conn: 已打开的 sqlite3.Connection（优先使用）
    :param db_path: 如果 conn 未提供，则使用此路径打开新连接
    :param expected_usage: 期望的 usage_weekly 记录数
    :return: 校验结果字典，包含 "passed" (bool) 和 "errors" (List[str])
    """
    errors: List[str] = []
    close_conn = False

    try:
        if conn is None:
            from src.database import get_connection
            conn = get_connection(db_path)
            close_conn = True

        checks = [
            ("customer_ids_unique", validate_customer_ids_unique),
            ("usage_unique_per_customer_week", validate_usage_unique_per_customer_week),
            ("usage_count_exact", lambda c: validate_usage_count(c, expected_usage)),
            ("foreign_keys_valid", validate_foreign_keys),
            ("active_days_range", validate_active_days_range),
            ("active_users_vs_licensed", validate_active_users_vs_licensed),
            ("core_feature_users_vs_active_users", validate_core_feature_users_vs_active_users),
            ("no_negative_counts", validate_no_negative_counts),
            ("ticket_response_time", validate_ticket_response_time),
            ("ticket_resolved_time", validate_ticket_resolved_time),
            ("unresolved_tickets_resolved_at_null", validate_unresolved_tickets_resolved_at_null),
            ("satisfaction_score_valid", validate_satisfaction_score),
            ("followup_date_in_range", lambda c: validate_followup_date_range(c, START_DATE, END_DATE)),
        ]

        for name, check_fn in checks:
            try:
                check_fn(conn)
            except ValidationError as e:
                errors.append(f"[{name}] {e}")

    finally:
        if close_conn and conn is not None:
            conn.close()

    return {
        "passed": len(errors) == 0,
        "errors": errors,
    }


def validate_ticket_response_time(conn: sqlite3.Connection) -> None:
    """工单首次响应时间不得早于创建时间。"""
    cur = conn.execute("""
        SELECT ticket_id, customer_id, created_at, first_response_at
        FROM support_tickets
        WHERE first_response_at IS NOT NULL
          AND first_response_at < created_at
    """)
    bad = cur.fetchall()
    if bad:
        raise ValidationError(f"first_response_at 早于 created_at：{[dict(b) for b in bad]}")


def validate_ticket_resolved_time(conn: sqlite3.Connection) -> None:
    """工单解决时间不得早于创建时间。"""
    cur = conn.execute("""
        SELECT ticket_id, customer_id, created_at, resolved_at
        FROM support_tickets
        WHERE resolved_at IS NOT NULL
          AND resolved_at < created_at
    """)
    bad = cur.fetchall()
    if bad:
        raise ValidationError(f"resolved_at 早于 created_at：{[dict(b) for b in bad]}")


def validate_unresolved_tickets_resolved_at_null(conn: sqlite3.Connection) -> None:
    """未解决工单（open/in_progress）的 resolved_at 必须为空。"""
    cur = conn.execute("""
        SELECT ticket_id, customer_id, status, resolved_at
        FROM support_tickets
        WHERE status IN ('open', 'in_progress')
          AND resolved_at IS NOT NULL
    """)
    bad = cur.fetchall()
    if bad:
        raise ValidationError(f"未解决工单 resolved_at 非空：{[dict(b) for b in bad]}")


def validate_satisfaction_score(conn: sqlite3.Connection) -> None:
    """满意度只能为 NULL 或 1 到 5。"""
    cur = conn.execute("""
        SELECT ticket_id, customer_id, satisfaction_score
        FROM support_tickets
        WHERE satisfaction_score IS NOT NULL
          AND (satisfaction_score < 1 OR satisfaction_score > 5)
    """)
    bad = cur.fetchall()
    if bad:
        raise ValidationError(f"satisfaction_score 非法：{[dict(b) for b in bad]}")


def validate_followup_date_range(conn: sqlite3.Connection, start_date: str, end_date: str) -> None:
    """跟进日期必须在模拟时间范围内。"""
    cur = conn.execute("""
        SELECT followup_id, customer_id, followup_date
        FROM followup_records
        WHERE followup_date < ? OR followup_date > ?
    """, (start_date, end_date))
    bad = cur.fetchall()
    if bad:
        raise ValidationError(f"跟进日期超出模拟时间范围：{[dict(b) for b in bad]}")