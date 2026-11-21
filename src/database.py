# -*- coding: utf-8 -*-
"""B2B SaaS 客户使用与服务运营分析平台 - 数据库模块
Phase 1：数据库与模拟数据开发

提供 SQLite 连接、数据库初始化、建表和基础数据库操作。
每次连接时启用 PRAGMA foreign_keys = ON。
"""

import sqlite3
from pathlib import Path
from typing import Optional, List, Tuple

from src.config import DB_PATH

# ---------------------------------------------------------------------------
# 建表 DDL
# ---------------------------------------------------------------------------

CREATE_CUSTOMERS_TABLE = """CREATE TABLE IF NOT EXISTS customers (
    customer_id         TEXT PRIMARY KEY,
    company_name        TEXT NOT NULL,
    industry            TEXT NOT NULL,
    company_size        TEXT NOT NULL,
    region              TEXT NOT NULL,
    plan_type           TEXT NOT NULL,
    licensed_users      INTEGER NOT NULL CHECK (licensed_users > 0),
    signup_date         TEXT NOT NULL,
    contract_start_date TEXT NOT NULL,
    contract_end_date   TEXT NOT NULL,
    monthly_fee         REAL NOT NULL CHECK (monthly_fee >= 0),
    account_owner       TEXT NOT NULL,
    created_at          TEXT NOT NULL,
    customer_status     TEXT NOT NULL DEFAULT '活跃',
    contact_person      TEXT NOT NULL DEFAULT '',
    contact_info        TEXT,
    notes               TEXT
);"""

CREATE_USAGE_WEEKLY_TABLE = """CREATE TABLE IF NOT EXISTS usage_weekly (
    usage_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id      TEXT NOT NULL,
    week_start       TEXT NOT NULL,
    login_count      INTEGER NOT NULL CHECK (login_count >= 0),
    active_days      INTEGER NOT NULL CHECK (active_days BETWEEN 0 AND 7),
    active_users     INTEGER NOT NULL CHECK (active_users >= 0),
    core_feature_users INTEGER NOT NULL CHECK (core_feature_users >= 0),
    core_feature_uses INTEGER NOT NULL CHECK (core_feature_uses >= 0),
    usage_minutes    INTEGER NOT NULL CHECK (usage_minutes >= 0),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    UNIQUE (customer_id, week_start)
);"""

CREATE_SUPPORT_TICKETS_TABLE = """CREATE TABLE IF NOT EXISTS support_tickets (
    ticket_id          TEXT PRIMARY KEY,
    customer_id        TEXT NOT NULL,
    created_at         TEXT NOT NULL,
    category           TEXT NOT NULL,
    priority           TEXT NOT NULL,
    status             TEXT NOT NULL,
    channel            TEXT NOT NULL,
    subject            TEXT NOT NULL,
    first_response_at  TEXT,
    resolved_at        TEXT,
    satisfaction_score INTEGER CHECK (satisfaction_score IS NULL OR satisfaction_score BETWEEN 1 AND 5),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);"""

CREATE_FOLLOWUP_RECORDS_TABLE = """CREATE TABLE IF NOT EXISTS followup_records (
    followup_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id       TEXT NOT NULL,
    followup_date     TEXT NOT NULL,
    followup_type     TEXT NOT NULL,
    trigger_reason    TEXT NOT NULL,
    action_description TEXT NOT NULL,
    result_status     TEXT NOT NULL,
    result_note       TEXT,
    created_at        TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);"""
# ---------------------------------------------------------------------------
# 索引
# ---------------------------------------------------------------------------

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_usage_weekly_week_start ON usage_weekly(week_start);",
    "CREATE INDEX IF NOT EXISTS idx_support_tickets_customer_created ON support_tickets(customer_id, created_at);",
    "CREATE INDEX IF NOT EXISTS idx_support_tickets_status_created ON support_tickets(status, created_at);",
    "CREATE INDEX IF NOT EXISTS idx_followup_customer_date ON followup_records(customer_id, followup_date);",
    # usage_weekly(customer_id, week_start) 已由 UNIQUE 约束覆盖，不重复创建
]

ALL_TABLES = ["customers", "usage_weekly", "support_tickets", "followup_records"]

# ---------------------------------------------------------------------------
# 连接与初始化
# ---------------------------------------------------------------------------

def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """创建 SQLite 连接并启用外键约束。

    :return: 已打开的 sqlite3.Connection
    """
    if db_path is None:
        db_path = DB_PATH
    # 确保数据目录存在
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_database(db_path: Optional[Path] = None, reset: bool = False) -> sqlite3.Connection:
    """初始化数据库结构。

    :param db_path: 数据库文件路径，默认使用 config.DB_PATH
    :param reset: 如果为 True，先删除已有表再重建；否则仅在表不存在时创建
    :return: 已打开的 sqlite3.Connection
    """
    if db_path is None:
        db_path = DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row  # 启用字典-style access
    conn.execute("PRAGMA foreign_keys = ON")  # 启用外键约束

    if reset:
        # 删除已有表（按依赖逆序，避免外键约束阻碍）
        for table in reversed(ALL_TABLES):
            conn.execute(f"DROP TABLE IF EXISTS {table}")

    # 创建表
    conn.execute(CREATE_CUSTOMERS_TABLE)
    conn.execute(CREATE_USAGE_WEEKLY_TABLE)
    conn.execute(CREATE_SUPPORT_TICKETS_TABLE)
    conn.execute(CREATE_FOLLOWUP_RECORDS_TABLE)

    # 创建索引
    for idx_sql in CREATE_INDEXES:
        conn.execute(idx_sql)

    conn.commit()
    return conn


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    """检查指定表是否已存在。

    :return: 如果表存在返回 True
    """
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    return cur.fetchone() is not None


def get_table_count(conn: sqlite3.Connection, table_name: str) -> int:
    """获取指定表的记录数量。

    :return: 记录数量
    """
    cur = conn.execute(f"SELECT COUNT(*) AS cnt FROM {table_name}")
    row = cur.fetchone()
    return row["cnt"] if row else 0


def get_all_table_counts(conn: sqlite3.Connection) -> dict:
    """获取所有核心表的记录数量。

    :return: 以表名为键的记录数量字典
    """
    return {table: get_table_count(conn, table) for table in ALL_TABLES}


def foreign_key_check(conn: sqlite3.Connection) -> List[Tuple]:
    """执行 PRAGMA foreign_key_check，返回违规记录列表。

    :return: 违规记录列表，无违规返回空列表
    """
    cur = conn.execute("PRAGMA foreign_key_check")
    return cur.fetchall()