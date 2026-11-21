#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B2B SaaS 客户使用与服务运营分析平台 - 数据库初始化与模拟数据生成入口
Phase 1：数据库与模拟数据开发

用法：
    python scripts/init_demo_data.py          # 创建/使用现有数据库并生成数据（若不存在则新建）
    python scripts/init_demo_data.py --reset  # 删除已有表并重新生成全部模拟数据

安全规则：
- 如果数据库文件已存在且未传入 --reset，不会删除或覆盖已有数据。
- 只有显式传入 --reset 时才会重建数据库。
- 使用事务处理，生成或校验失败时回滚，避免留下不完整数据集。
"""

import argparse
import sys
import sqlite3
from pathlib import Path

# 确保可以导入 src 模块
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import DB_PATH
from src.database import init_database, get_table_count, get_all_table_counts, foreign_key_check
from src.data_generator import generate_all_data
from src.data_validation import validate_all


def insert_customers(conn: sqlite3.Connection, customers: list) -> None:
    conn.executemany("""
        INSERT OR IGNORE INTO customers
        (customer_id, company_name, industry, company_size, region, plan_type,
         licensed_users, signup_date, contract_start_date, contract_end_date,
         monthly_fee, account_owner, created_at)
        VALUES (:customer_id, :company_name, :industry, :company_size, :region, :plan_type,
                :licensed_users, :signup_date, :contract_start_date, :contract_end_date,
                :monthly_fee, :account_owner, :created_at)
    """, customers)


def insert_usage_weekly(conn: sqlite3.Connection, usage: list) -> None:
    conn.executemany("""
        INSERT OR IGNORE INTO usage_weekly
        (customer_id, week_start, login_count, active_days, active_users,
         core_feature_users, core_feature_uses, usage_minutes)
        VALUES (:customer_id, :week_start, :login_count, :active_days, :active_users,
                :core_feature_users, :core_feature_uses, :usage_minutes)
    """, usage)


def insert_support_tickets(conn: sqlite3.Connection, tickets: list) -> None:
    conn.executemany("""
        INSERT OR IGNORE INTO support_tickets
        (ticket_id, customer_id, created_at, category, priority, status, channel,
         subject, first_response_at, resolved_at, satisfaction_score)
        VALUES (:ticket_id, :customer_id, :created_at, :category, :priority, :status,
                :channel, :subject, :first_response_at, :resolved_at, :satisfaction_score)
    """, tickets)


def insert_followup_records(conn: sqlite3.Connection, followups: list) -> None:
    conn.executemany("""
        INSERT OR IGNORE INTO followup_records
        (followup_id, customer_id, followup_date, followup_type, trigger_reason,
         action_description, result_status, result_note, created_at)
        VALUES (:followup_id, :customer_id, :followup_date, :followup_type, :trigger_reason,
                :action_description, :result_status, :result_note, :created_at)
    """, followups)


def main() -> None:
    parser = argparse.ArgumentParser(description="初始化 SQLite 数据库并生成模拟数据")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="显式重建数据库（删除已有表并重新生成）。不加此参数时不会覆盖已有数据库。",
    )
    args = parser.parse_args()

    db_exists = DB_PATH.exists()

    if db_exists and not args.reset:
        print(f"[INFO] 数据库文件已存在：{DB_PATH}")
        print("[INFO] 未使用 --reset，将在现有数据库上插入缺失数据（INSERT OR IGNORE）。")
    elif args.reset:
        print(f"[INFO] 使用 --reset，将重建数据库：{DB_PATH}")
    else:
        print(f"[INFO] 数据库文件不存在，将新建：{DB_PATH}")

    try:
        # 1. 初始化数据库结构
        conn = init_database(DB_PATH, reset=args.reset)

        # 2. 生成模拟数据
        print("[INFO] 正在生成模拟数据（SEED=42）...")
        data = generate_all_data(seed=42)

        # 3. 在事务中写入数据
        try:
            insert_customers(conn, data["customers_clean"])
            insert_usage_weekly(conn, data["usage_weekly"])
            insert_support_tickets(conn, data["support_tickets"])
            insert_followup_records(conn, data["followup_records"])
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"[ERROR] 数据写入失败，已回滚：{e}")
            sys.exit(1)

        # 4. 输出每张表的实际数据数量
        counts = get_all_table_counts(conn)
        print("\n===== 数据生成结果 =====")
        for table in ["customers", "usage_weekly", "support_tickets", "followup_records"]:
            print(f"  {table}: {counts[table]} 条")

        # 5. 输出画像分布
        print("\n===== 客户画像分布 =====")
        for persona, cnt in sorted(data["persona_counts"].items(), key=lambda x: -x[1]):
            print(f"  {persona}: {cnt} 家")

        # 6. 执行数据质量校验
        print("\n===== 数据质量校验 =====")
        result = validate_all(conn)
        if result["passed"]:
            print("  [PASS] 所有数据质量校验通过。")
        else:
            print("  [FAIL] 数据质量校验失败：")
            for err in result["errors"]:
                print(f"    - {err}")
            sys.exit(1)

        # 7. 外键检查
        fk_violations = foreign_key_check(conn)
        if fk_violations:
            print(f"  [FAIL] PRAGMA foreign_key_check 发现 {len(fk_violations)} 条违规：")
            for v in fk_violations:
                print(f"    - {dict(v)}")
            sys.exit(1)
        else:
            print("  [PASS] PRAGMA foreign_key_check 无错误。")

        print("\n[INFO] 数据库初始化和模拟数据生成完成。")

    except Exception as e:
        print(f"[ERROR] 初始化失败：{e}")
        sys.exit(1)
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()