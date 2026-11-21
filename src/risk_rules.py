
# src/risk_rules.py

import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from src.config import DB_PATH


# =========================
# 基础配置
# =========================

LOW_RISK_MAX = 29
MEDIUM_RISK_MAX = 59

RISK_LEVELS = {
    "低风险": (0, LOW_RISK_MAX),
    "中风险": (LOW_RISK_MAX + 1, MEDIUM_RISK_MAX),
    "高风险": (MEDIUM_RISK_MAX + 1, 100),
}


# =========================
# 数据库连接
# =========================

def get_connection(db_path=None):
    """创建 SQLite 数据库连接。"""

    path = db_path or DB_PATH

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


def _table_exists(conn, table_name):
    result = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,)
    ).fetchone()

    return result is not None


def _get_columns(conn, table_name):
    if not _table_exists(conn, table_name):
        return []

    rows = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return [row["name"] for row in rows]


def _find_column(columns, candidates):
    """从字段列表中查找兼容字段。"""

    for candidate in candidates:
        if candidate in columns:
            return candidate

    return None


def _safe_date(value):
    """将日期字符串转换为 date 对象。"""

    if value is None:
        return None

    if isinstance(value, date):
        return value

    value = str(value).strip()

    if not value:
        return None

    formats = [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value[:19], fmt).date()
        except ValueError:
            pass

    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _safe_datetime(value):
    """将日期时间字符串转换为 datetime 对象。"""

    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    value = str(value).strip()

    if not value:
        return None

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value[:19], fmt)
        except ValueError:
            pass

    return None


def _get_observation_date(conn):
    """
    优先使用 usage_weekly 中最新日期作为数据观察日期，
    避免模拟数据与真实系统当前日期产生不一致。
    """

    if _table_exists(conn, "usage_weekly"):
        columns = _get_columns(conn, "usage_weekly")

        date_column = _find_column(
            columns,
            ["week_start", "week_date", "date", "stat_date"]
        )

        if date_column:
            row = conn.execute(
                f"""
                SELECT MAX("{date_column}")
                FROM usage_weekly
                """
            ).fetchone()

            if row and row[0]:
                parsed = _safe_date(row[0])

                if parsed:
                    return parsed

    return date.today()


# =========================
# 客户基础信息
# =========================

def _get_all_customer_ids(conn):
    """获取全部客户ID。"""

    if not _table_exists(conn, "customers"):
        return []

    columns = _get_columns(conn, "customers")

    customer_id_column = _find_column(
        columns,
        ["customer_id", "id"]
    )

    if not customer_id_column:
        return []

    rows = conn.execute(
        f"""
        SELECT "{customer_id_column}"
        FROM customers
        """
    ).fetchall()

    return [row[0] for row in rows]


def _get_customer_contract_end(conn, customer_id):
    """获取客户合同到期日期。"""

    if not _table_exists(conn, "customers"):
        return None

    columns = _get_columns(conn, "customers")

    id_column = _find_column(
        columns,
        ["customer_id", "id"]
    )

    contract_column = _find_column(
        columns,
        [
            "contract_end_date",
            "contract_end",
            "end_date",
            "expiration_date",
        ]
    )

    if not id_column or not contract_column:
        return None

    row = conn.execute(
        f"""
        SELECT "{contract_column}"
        FROM customers
        WHERE "{id_column}" = ?
        LIMIT 1
        """,
        (customer_id,)
    ).fetchone()

    if not row:
        return None

    return _safe_date(row[0])


# =========================
# 使用数据分析
# =========================

def _get_customer_weekly_active_days(conn, customer_id):
    """获取客户每周活跃天数，按时间排序。"""

    if not _table_exists(conn, "usage_weekly"):
        return []

    columns = _get_columns(conn, "usage_weekly")

    id_column = _find_column(
        columns,
        ["customer_id"]
    )

    active_column = _find_column(
        columns,
        ["active_days", "weekly_active_days", "activity_days"]
    )

    date_column = _find_column(
        columns,
        ["week_start", "week_date", "date", "stat_date"]
    )

    if not id_column or not active_column:
        return []

    if date_column:
        rows = conn.execute(
            f"""
            SELECT "{date_column}", "{active_column}"
            FROM usage_weekly
            WHERE "{id_column}" = ?
            ORDER BY "{date_column}" ASC
            """,
            (customer_id,)
        ).fetchall()
    else:
        rows = conn.execute(
            f"""
            SELECT "{active_column}"
            FROM usage_weekly
            WHERE "{id_column}" = ?
            """,
            (customer_id,)
        ).fetchall()

    result = []

    for row in rows:
        if date_column:
            result.append({
                "date": row[0],
                "active_days": row[1],
            })
        else:
            result.append({
                "date": None,
                "active_days": row[0],
            })

    return result


def _get_recent_average(active_days_list, weeks=4):
    """计算最近N周平均活跃天数。"""

    if not active_days_list:
        return 0.0

    values = [
        float(item["active_days"] or 0)
        for item in active_days_list
    ]

    recent_values = values[-weeks:]

    if not recent_values:
        return 0.0

    return round(sum(recent_values) / len(recent_values), 2)


def _get_early_average(active_days_list, weeks=4):
    """计算最早N周平均活跃天数。"""

    if not active_days_list:
        return 0.0

    values = [
        float(item["active_days"] or 0)
        for item in active_days_list
    ]

    early_values = values[:weeks]

    if not early_values:
        return 0.0

    return round(sum(early_values) / len(early_values), 2)


# =========================
# 客服工单分析
# =========================

def _get_customer_tickets(conn, customer_id):
    """获取指定客户的客服工单。"""

    if not _table_exists(conn, "support_tickets"):
        return []

    columns = _get_columns(conn, "support_tickets")

    customer_column = _find_column(
        columns,
        ["customer_id"]
    )

    if not customer_column:
        return []

    rows = conn.execute(
        f"""
        SELECT *
        FROM support_tickets
        WHERE "{customer_column}" = ?
        """,
        (customer_id,)
    ).fetchall()

    return [dict(row) for row in rows]


def _is_unresolved(status):
    """判断工单是否尚未解决。"""

    if status is None:
        return True

    status = str(status).strip().lower()

    resolved_statuses = {
        "已解决",
        "已关闭",
        "关闭",
        "解决",
        "resolved",
        "closed",
        "complete",
        "completed",
        "done",
    }

    return status not in resolved_statuses


def _get_customer_unresolved_tickets(conn, customer_id):
    """统计客户未解决工单。"""

    tickets = _get_customer_tickets(conn, customer_id)

    if not tickets:
        return []

    status_candidates = [
        "status",
        "ticket_status",
        "处理状态",
    ]

    unresolved = []

    for ticket in tickets:
        status = None

        for column in status_candidates:
            if column in ticket:
                status = ticket[column]
                break

        if _is_unresolved(status):
            unresolved.append(ticket)

    return unresolved


def _get_oldest_unresolved_ticket_hours(conn, customer_id):
    """计算最久未解决工单的等待时间（小时）。"""

    unresolved_tickets = _get_customer_unresolved_tickets(
        conn,
        customer_id
    )

    if not unresolved_tickets:
        return 0.0

    observation_date = _get_observation_date(conn)

    observation_datetime = datetime.combine(
        observation_date,
        datetime.max.time()
    )

    date_candidates = [
        "created_at",
        "create_time",
        "ticket_date",
        "created_date",
        "提交时间",
    ]

    hours_list = []

    for ticket in unresolved_tickets:
        created_at = None

        for column in date_candidates:
            if column in ticket:
                created_at = _safe_datetime(ticket[column])
                break

        if created_at is None:
            continue

        hours = (
            observation_datetime - created_at
        ).total_seconds() / 3600

        if hours >= 0:
            hours_list.append(hours)

    if not hours_list:
        return 0.0

    return round(max(hours_list), 2)


# =========================
# 风险等级
# =========================

def _classify_risk_level(score):
    """根据风险分值划分风险等级。"""

    if score <= LOW_RISK_MAX:
        return "低风险"

    if score <= MEDIUM_RISK_MAX:
        return "中风险"

    return "高风险"


# =========================
# 单客户风险计算
# =========================

def calculate_customer_risk(conn, customer_id):
    """
    计算单个客户风险。

    返回：
    customer_id
    risk_score
    risk_level
    triggered_rules
    supporting_values
    """

    risk_score = 0

    triggered_rules = []

    active_days_list = _get_customer_weekly_active_days(
        conn,
        customer_id
    )

    recent_avg = _get_recent_average(
        active_days_list,
        weeks=4
    )

    early_avg = _get_early_average(
        active_days_list,
        weeks=4
    )

    # ---------------------------------
    # 规则1：近期活跃度偏低
    # ---------------------------------

    if recent_avg < 2:

        score = 25

        risk_score += score

        triggered_rules.append({
            "rule": "近期活跃度偏低",
            "description": "最近4周平均每周活跃天数低于2天",
            "score": score,
            "value": recent_avg,
        })

    # ---------------------------------
    # 规则2：活跃度明显下降
    # ---------------------------------

    decline_rate = 0.0

    if early_avg > 0:

        decline_rate = (
            (early_avg - recent_avg) / early_avg
        )

    if early_avg > 0 and decline_rate >= 0.30:

        score = 30

        risk_score += score

        triggered_rules.append({
            "rule": "使用活跃度下降",
            "description": "近期活跃度相比早期下降30%以上",
            "score": score,
            "value": round(decline_rate * 100, 2),
        })

    # ---------------------------------
    # 规则3：未解决工单数量较多
    # ---------------------------------

    unresolved_tickets = _get_customer_unresolved_tickets(
        conn,
        customer_id
    )

    unresolved_count = len(unresolved_tickets)

    if unresolved_count >= 2:

        score = 20

        risk_score += score

        triggered_rules.append({
            "rule": "未解决工单较多",
            "description": "当前存在2个或以上未解决工单",
            "score": score,
            "value": unresolved_count,
        })

    # ---------------------------------
    # 规则4：存在长期未解决工单
    # ---------------------------------

    oldest_ticket_hours = (
        _get_oldest_unresolved_ticket_hours(
            conn,
            customer_id
        )
    )

    if oldest_ticket_hours > 72:

        score = 15

        risk_score += score

        triggered_rules.append({
            "rule": "工单处理超时",
            "description": "存在超过72小时未解决的工单",
            "score": score,
            "value": oldest_ticket_hours,
        })

    # ---------------------------------
    # 规则5：合同即将到期
    # ---------------------------------

    contract_end = _get_customer_contract_end(
        conn,
        customer_id
    )

    observation_date = _get_observation_date(conn)

    days_to_contract_end = None

    if contract_end:

        days_to_contract_end = (
            contract_end - observation_date
        ).days

        if 0 <= days_to_contract_end <= 30:

            score = 10

            risk_score += score

            triggered_rules.append({
                "rule": "合同即将到期",
                "description": "客户合同将在30天内到期",
                "score": score,
                "value": days_to_contract_end,
            })

    # 风险分值最高100
    risk_score = min(risk_score, 100)

    risk_level = _classify_risk_level(
        risk_score
    )

    supporting_values = {
        "recent_avg_active_days": recent_avg,
        "early_avg_active_days": early_avg,
        "activity_decline_rate": round(
            decline_rate * 100,
            2
        ),
        "unresolved_ticket_count": unresolved_count,
        "oldest_unresolved_ticket_hours": oldest_ticket_hours,
        "contract_end_date": (
            contract_end.isoformat()
            if contract_end else None
        ),
        "days_to_contract_end": days_to_contract_end,
        "observation_date": observation_date.isoformat(),
    }

    return {
        "customer_id": customer_id,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "triggered_rules": triggered_rules,
        "supporting_values": supporting_values,
    }


# =========================
# 全量客户风险分析
# =========================

def calculate_all_customers_risk(conn):
    """计算所有客户风险并按风险分值降序排列。"""

    customer_ids = _get_all_customer_ids(conn)

    results = []

    for customer_id in customer_ids:

        risk = calculate_customer_risk(
            conn,
            customer_id
        )

        results.append(risk)

    results.sort(
        key=lambda item: item["risk_score"],
        reverse=True
    )

    return results


# =========================
# 风险筛选
# =========================

def filter_by_risk_level(risks, risk_level):
    """根据风险等级筛选客户。"""

    return [
        item
        for item in risks
        if item["risk_level"] == risk_level
    ]


def get_risk_level_distribution(risks):
    """统计不同风险等级的客户数量。"""

    distribution = {
        "低风险": 0,
        "中风险": 0,
        "高风险": 0,
    }

    for item in risks:

        level = item.get("risk_level")

        if level in distribution:
            distribution[level] += 1

    return distribution


# =========================
# 模块自检
# =========================

if __name__ == "__main__":

    conn = get_connection()

    try:

        risks = calculate_all_customers_risk(conn)

        print(f"风险分析客户数量：{len(risks)}")

        print("风险等级分布：")
        print(get_risk_level_distribution(risks))

        print("\n风险最高的5名客户：")

        for item in risks[:5]:

            print(
                item["customer_id"],
                item["risk_score"],
                item["risk_level"],
                item["triggered_rules"],
            )

    finally:

        conn.close()
