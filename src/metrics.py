# -*- coding: utf-8 -*-
"""B2B SaaS 客户使用与服务运营分析平台 - 经营指标分析模块。

Phase 2：数据分析与客户风险诊断。

本模块使用 SQLite SQL 和 Pandas 集中计算业务指标。核心计算逻辑与
Streamlit 页面分离，供后续页面直接调用。
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Union

import pandas as pd

try:
    # 作为 src.metrics 导入时使用包内导入
    from .config import DB_PATH, DATE_FORMAT, DATETIME_FORMAT
except ImportError:
    # 兼容将 src 目录加入 sys.path 后直接导入 metrics
    from config import DB_PATH, DATE_FORMAT, DATETIME_FORMAT


# 模拟数据观察窗口结束日，保证分析结果可复现
OBSERVATION_BASE_DATE = "2026-11-01"

# 允许动态选择的客户分组字段
_ALLOWED_GROUP_FIELDS = {"industry", "region", "plan_type"}


# ---------------------------------------------------------------------------
# 数据库与通用辅助函数
# ---------------------------------------------------------------------------

def get_connection(
    db_path: Optional[Union[str, Path]] = None,
) -> sqlite3.Connection:
    """创建 SQLite 连接并启用外键约束。"""
    target = Path(db_path if db_path is not None else DB_PATH)

    if str(target) != ":memory:":
        target.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(target))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row

    return conn


def _parse_date(date_str: Optional[str]) -> Optional[str]:
    """校验日期字符串并统一返回 YYYY-MM-DD。"""
    if date_str is None or date_str == "":
        return None

    try:
        parsed = datetime.strptime(str(date_str), DATE_FORMAT)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"日期格式错误：{date_str!r}，应使用 YYYY-MM-DD"
        ) from exc

    return parsed.strftime(DATE_FORMAT)


def _normalize_date_range(
    start_date: Optional[str],
    end_date: Optional[str],
) -> tuple[Optional[str], Optional[str]]:
    """校验并规范化日期范围。"""
    start = _parse_date(start_date)
    end = _parse_date(end_date)

    if start is not None and end is not None and start > end:
        raise ValueError("start_date 不能晚于 end_date")

    return start, end


def _parse_datetime(
    dt_str: Optional[str],
) -> Optional[datetime]:
    """解析项目使用的 ISO 日期时间字符串。"""
    if dt_str is None or dt_str == "":
        return None

    try:
        return datetime.strptime(str(dt_str), DATETIME_FORMAT)
    except (TypeError, ValueError):
        return None


def _safe_divide(
    numerator: Union[int, float],
    denominator: Union[int, float, None],
    digits: int = 4,
) -> Optional[float]:
    """安全除法，分母为 0 或 None 时返回 None。"""
    if denominator is None or denominator == 0:
        return None

    return round(float(numerator) / float(denominator), digits)


def _to_dataframe(
    conn: sqlite3.Connection,
    query: str,
    params: Optional[tuple[Any, ...]] = None,
) -> pd.DataFrame:
    """执行参数化 SQL 并返回 DataFrame。"""
    return pd.read_sql_query(
        query,
        conn,
        params=params or (),
    )


def _append_week_filter(
    query: str,
    params: list[Any],
    column: str,
    start_date: Optional[str],
    end_date: Optional[str],
) -> str:
    """追加周日期过滤条件。"""
    if start_date:
        query += f" AND {column} >= ?"
        params.append(start_date)

    if end_date:
        query += f" AND {column} <= ?"
        params.append(end_date)

    return query


def _append_datetime_filter(
    query: str,
    params: list[Any],
    column: str,
    start_date: Optional[str],
    end_date: Optional[str],
) -> str:
    """追加 datetime 字段的日期过滤条件。"""
    if start_date:
        query += f" AND date({column}) >= ?"
        params.append(start_date)

    if end_date:
        query += f" AND date({column}) <= ?"
        params.append(end_date)

    return query


def _hours_between(
    frame: pd.DataFrame,
    start_column: str,
    end_column: str,
) -> pd.Series:
    """计算两个 datetime 字段之间的小时数。"""
    if frame.empty:
        return pd.Series(dtype="float64")

    start_values = pd.to_datetime(
        frame[start_column],
        format=DATETIME_FORMAT,
        errors="coerce",
    )

    end_values = pd.to_datetime(
        frame[end_column],
        format=DATETIME_FORMAT,
        errors="coerce",
    )

    hours = (
        end_values - start_values
    ).dt.total_seconds() / 3600.0

    return hours[hours.notna() & (hours >= 0)]


def _average_or_none(
    values: pd.Series,
) -> Optional[float]:
    """计算平均值，没有有效样本时返回 None。"""
    if values.empty:
        return None

    return round(float(values.mean()), 2)


def _percentage(
    value: Optional[float],
) -> Optional[float]:
    """将比例转换为百分数。"""
    if value is None:
        return None

    return round(value * 100, 2)


# ---------------------------------------------------------------------------
# 1. 客户经营总览指标
# ---------------------------------------------------------------------------

def get_business_overview(
    conn: sqlite3.Connection,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> dict[str, Any]:
    """获取客户经营总览 KPI。

    指标：
    - total_customers：企业客户总数
    - active_customers：活跃客户数
    - active_rate：客户活跃率
    - core_feature_customers：核心功能使用客户数
    - core_adoption_rate：核心功能采用率
    - total_tickets：工单总量
    - unresolved_tickets：未解决工单数
    - resolution_rate：工单解决率
    - avg_first_response_hours：平均首次响应时间
    - avg_resolve_hours：平均解决时间
    - avg_satisfaction：平均满意度
    """
    start_date, end_date = _normalize_date_range(
        start_date,
        end_date,
    )

    # 企业客户总数
    total_customers = int(
        conn.execute(
            "SELECT COUNT(*) AS cnt FROM customers"
        ).fetchone()["cnt"]
    )

    # 活跃客户数
    active_query = """
        SELECT COUNT(DISTINCT customer_id) AS cnt
        FROM usage_weekly
        WHERE active_users > 0
    """

    active_params: list[Any] = []

    active_query = _append_week_filter(
        active_query,
        active_params,
        "week_start",
        start_date,
        end_date,
    )

    active_customers = int(
        conn.execute(
            active_query,
            tuple(active_params),
        ).fetchone()["cnt"]
    )

    # 核心功能使用客户数
    core_query = """
        SELECT COUNT(DISTINCT customer_id) AS cnt
        FROM usage_weekly
        WHERE core_feature_uses > 0
    """

    core_params: list[Any] = []

    core_query = _append_week_filter(
        core_query,
        core_params,
        "week_start",
        start_date,
        end_date,
    )

    core_feature_customers = int(
        conn.execute(
            core_query,
            tuple(core_params),
        ).fetchone()["cnt"]
    )

    # 工单数据
    tickets_query = """
        SELECT
            ticket_id,
            created_at,
            status,
            first_response_at,
            resolved_at,
            satisfaction_score
        FROM support_tickets
        WHERE 1 = 1
    """

    ticket_params: list[Any] = []

    tickets_query = _append_datetime_filter(
        tickets_query,
        ticket_params,
        "created_at",
        start_date,
        end_date,
    )

    tickets_df = _to_dataframe(
        conn,
        tickets_query,
        tuple(ticket_params),
    )

    total_tickets = int(len(tickets_df))

    if tickets_df.empty:
        unresolved_tickets = 0
        resolved_tickets = 0
    else:
        unresolved_tickets = int(
            tickets_df["status"].isin(
                ["open", "in_progress"]
            ).sum()
        )

        resolved_tickets = int(
            tickets_df["status"].isin(
                ["resolved", "closed"]
            ).sum()
        )

    resolution_rate = _safe_divide(
        resolved_tickets,
        total_tickets,
    )

    # 平均首次响应时间
    responded_df = tickets_df[
        tickets_df["first_response_at"].notna()
    ].copy()

    response_hours = _hours_between(
        responded_df,
        "created_at",
        "first_response_at",
    )

    # 平均解决时间
    resolved_df = tickets_df[
        tickets_df["resolved_at"].notna()
    ].copy()

    resolve_hours = _hours_between(
        resolved_df,
        "created_at",
        "resolved_at",
    )

    # 平均满意度
    if tickets_df.empty:
        avg_satisfaction = None
    else:
        satisfaction = pd.to_numeric(
            tickets_df["satisfaction_score"],
            errors="coerce",
        ).dropna()

        avg_satisfaction = _average_or_none(
            satisfaction
        )

    return {
        "total_customers": total_customers,
        "active_customers": active_customers,
        "active_rate": _percentage(
            _safe_divide(active_customers, total_customers)
        ),
        "core_feature_customers": core_feature_customers,
        "core_adoption_rate": _percentage(
            _safe_divide(
                core_feature_customers,
                total_customers,
            )
        ),
        "total_tickets": total_tickets,
        "unresolved_tickets": unresolved_tickets,
        "resolution_rate": _percentage(resolution_rate),
        "avg_first_response_hours": _average_or_none(
            response_hours
        ),
        "avg_resolve_hours": _average_or_none(
            resolve_hours
        ),
        "avg_satisfaction": avg_satisfaction,
    }


# ---------------------------------------------------------------------------
# 2. 客户产品使用分析
# ---------------------------------------------------------------------------

def get_weekly_activity_trend(
    conn: sqlite3.Connection,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """获取每周活跃客户数趋势。

    返回：
    week_start、active_customer_count。
    """
    start_date, end_date = _normalize_date_range(
        start_date,
        end_date,
    )

    query = """
        SELECT
            week_start,
            COUNT(
                DISTINCT CASE
                    WHEN active_users > 0 THEN customer_id
                END
            ) AS active_customer_count
        FROM usage_weekly
        WHERE 1 = 1
    """

    params: list[Any] = []

    query = _append_week_filter(
        query,
        params,
        "week_start",
        start_date,
        end_date,
    )

    query += """
        GROUP BY week_start
        ORDER BY week_start
    """

    return _to_dataframe(
        conn,
        query,
        tuple(params),
    )


def get_avg_active_days_trend(
    conn: sqlite3.Connection,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """获取每周平均活跃天数趋势。

    包含 active_days 为 0 的客户周记录。
    """
    start_date, end_date = _normalize_date_range(
        start_date,
        end_date,
    )

    query = """
        SELECT
            week_start,
            ROUND(AVG(active_days), 2) AS avg_active_days
        FROM usage_weekly
        WHERE 1 = 1
    """

    params: list[Any] = []

    query = _append_week_filter(
        query,
        params,
        "week_start",
        start_date,
        end_date,
    )

    query += """
        GROUP BY week_start
        ORDER BY week_start
    """

    return _to_dataframe(
        conn,
        query,
        tuple(params),
    )


def get_login_count_stats(
    conn: sqlite3.Connection,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> dict[str, Any]:
    """获取登录次数统计，平均值按客户周记录计算。"""
    start_date, end_date = _normalize_date_range(
        start_date,
        end_date,
    )

    query = """
        SELECT
            COUNT(*) AS record_count,
            SUM(login_count) AS total_login,
            AVG(login_count) AS avg_login,
            MAX(login_count) AS max_login,
            MIN(login_count) AS min_login
        FROM usage_weekly
        WHERE 1 = 1
    """

    params: list[Any] = []

    query = _append_week_filter(
        query,
        params,
        "week_start",
        start_date,
        end_date,
    )

    row = conn.execute(
        query,
        tuple(params),
    ).fetchone()

    return {
        "record_count": int(row["record_count"] or 0),
        "total_login_count": int(row["total_login"] or 0),
        "avg_login_count": (
            round(float(row["avg_login"]), 2)
            if row["avg_login"] is not None
            else None
        ),
        "max_login_count": int(row["max_login"] or 0),
        "min_login_count": int(row["min_login"] or 0),
    }


def get_core_feature_usage_stats(
    conn: sqlite3.Connection,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> dict[str, Any]:
    """获取核心功能使用次数统计。"""
    start_date, end_date = _normalize_date_range(
        start_date,
        end_date,
    )

    query = """
        SELECT
            COUNT(*) AS record_count,
            SUM(core_feature_uses) AS total_uses,
            AVG(core_feature_uses) AS avg_uses,
            MAX(core_feature_uses) AS max_uses,
            MIN(core_feature_uses) AS min_uses
        FROM usage_weekly
        WHERE 1 = 1
    """

    params: list[Any] = []

    query = _append_week_filter(
        query,
        params,
        "week_start",
        start_date,
        end_date,
    )

    row = conn.execute(
        query,
        tuple(params),
    ).fetchone()

    return {
        "record_count": int(row["record_count"] or 0),
        "total_core_feature_uses": int(row["total_uses"] or 0),
        "avg_core_feature_uses": (
            round(float(row["avg_uses"]), 2)
            if row["avg_uses"] is not None
            else None
        ),
        "max_core_feature_uses": int(row["max_uses"] or 0),
        "min_core_feature_uses": int(row["min_uses"] or 0),
    }


def _get_activity_by_dimension(
    conn: sqlite3.Connection,
    dimension: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """按行业或套餐汇总客户活跃情况。"""
    if dimension not in {"industry", "plan_type"}:
        raise ValueError(
            "dimension 仅支持 industry 或 plan_type"
        )

    start_date, end_date = _normalize_date_range(
        start_date,
        end_date,
    )

    query = f"""
        SELECT
            c.{dimension} AS {dimension},
            COUNT(DISTINCT c.customer_id) AS customer_count,
            COUNT(
                DISTINCT CASE
                    WHEN u.active_users > 0 THEN c.customer_id
                END
            ) AS active_customer_count,
            ROUND(AVG(u.active_days), 2) AS avg_active_days
        FROM customers AS c
        LEFT JOIN usage_weekly AS u
            ON c.customer_id = u.customer_id
    """

    params: list[Any] = []

    if start_date:
        query += " AND u.week_start >= ?"
        params.append(start_date)

    if end_date:
        query += " AND u.week_start <= ?"
        params.append(end_date)

    query += f"""
        GROUP BY c.{dimension}
        ORDER BY c.{dimension}
    """

    frame = _to_dataframe(
        conn,
        query,
        tuple(params),
    )

    if not frame.empty:
        frame["active_rate"] = frame.apply(
            lambda row: _percentage(
                _safe_divide(
                    row["active_customer_count"],
                    row["customer_count"],
                )
            ),
            axis=1,
        )
    else:
        frame["active_rate"] = pd.Series(dtype="float64")

    return frame[
        [
            dimension,
            "customer_count",
            "active_customer_count",
            "active_rate",
            "avg_active_days",
        ]
    ]


def get_activity_by_plan(
    conn: sqlite3.Connection,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """不同套餐客户的活跃情况对比。"""
    return _get_activity_by_dimension(
        conn,
        "plan_type",
        start_date,
        end_date,
    )


def get_activity_by_industry(
    conn: sqlite3.Connection,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """不同行业客户的活跃情况对比。"""
    return _get_activity_by_dimension(
        conn,
        "industry",
        start_date,
        end_date,
    )


def get_customer_usage_trend(
    conn: sqlite3.Connection,
    customer_id: str,
) -> pd.DataFrame:
    """获取单个客户的产品使用趋势。"""
    query = """
        SELECT
            week_start,
            login_count,
            active_days,
            active_users,
            core_feature_users,
            core_feature_uses,
            usage_minutes
        FROM usage_weekly
        WHERE customer_id = ?
        ORDER BY week_start
    """

    return _to_dataframe(
        conn,
        query,
        (customer_id,),
    )


def get_customer_active_days_comparison(
    conn: sqlite3.Connection,
    customer_id: str,
) -> dict[str, Any]:
    """比较客户最早 4 周与最近 4 周的平均活跃天数。

    至少需要 8 条周记录，保证两个窗口完整且互不重叠。
    """
    query = """
        SELECT
            week_start,
            active_days
        FROM usage_weekly
        WHERE customer_id = ?
        ORDER BY week_start
    """

    frame = _to_dataframe(
        conn,
        query,
        (customer_id,),
    )

    empty_result = {
        "first_4weeks_avg": 0.0,
        "last_4weeks_avg": 0.0,
        "change_pct": None,
        "comparable": False,
    }

    if frame.empty:
        return {
            **empty_result,
            "reason": "无使用记录",
        }

    if len(frame) < 8:
        return {
            **empty_result,
            "reason": "周记录不足 8 周，无法进行前后窗口比较",
        }

    first_avg = float(
        frame.head(4)["active_days"].mean()
    )

    last_avg = float(
        frame.tail(4)["active_days"].mean()
    )

    if first_avg <= 0:
        return {
            "first_4weeks_avg": round(first_avg, 2),
            "last_4weeks_avg": round(last_avg, 2),
            "change_pct": None,
            "comparable": False,
            "reason": "最早 4 周平均活跃天数为 0，无可比基线",
        }

    change_pct = round(
        (first_avg - last_avg) / first_avg * 100,
        2,
    )

    return {
        "first_4weeks_avg": round(first_avg, 2),
        "last_4weeks_avg": round(last_avg, 2),
        "change_pct": change_pct,
        "comparable": True,
        "reason": "",
    }


# ---------------------------------------------------------------------------
# 3. 客户服务工单分析
# ---------------------------------------------------------------------------

def get_ticket_category_distribution(
    conn: sqlite3.Connection,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """获取工单类别分布。"""
    start_date, end_date = _normalize_date_range(
        start_date,
        end_date,
    )

    query = """
        SELECT
            category,
            COUNT(*) AS ticket_count
        FROM support_tickets
        WHERE 1 = 1
    """

    params: list[Any] = []

    query = _append_datetime_filter(
        query,
        params,
        "created_at",
        start_date,
        end_date,
    )

    query += """
        GROUP BY category
        ORDER BY ticket_count DESC, category
    """

    return _to_dataframe(
        conn,
        query,
        tuple(params),
    )


def get_ticket_priority_distribution(
    conn: sqlite3.Connection,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """获取工单优先级分布。"""
    start_date, end_date = _normalize_date_range(
        start_date,
        end_date,
    )

    query = """
        SELECT
            priority,
            COUNT(*) AS ticket_count
        FROM support_tickets
        WHERE 1 = 1
    """

    params: list[Any] = []

    query = _append_datetime_filter(
        query,
        params,
        "created_at",
        start_date,
        end_date,
    )

    query += """
        GROUP BY priority
        ORDER BY ticket_count DESC, priority
    """

    return _to_dataframe(
        conn,
        query,
        tuple(params),
    )


def get_ticket_status_distribution(
    conn: sqlite3.Connection,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """获取工单状态分布。"""
    start_date, end_date = _normalize_date_range(
        start_date,
        end_date,
    )

    query = """
        SELECT
            status,
            COUNT(*) AS ticket_count
        FROM support_tickets
        WHERE 1 = 1
    """

    params: list[Any] = []

    query = _append_datetime_filter(
        query,
        params,
        "created_at",
        start_date,
        end_date,
    )

    query += """
        GROUP BY status
        ORDER BY ticket_count DESC, status
    """

    return _to_dataframe(
        conn,
        query,
        tuple(params),
    )


def get_weekly_ticket_creation_trend(
    conn: sqlite3.Connection,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """获取每周工单创建量趋势，按周一作为周起始日。"""
    start_date, end_date = _normalize_date_range(
        start_date,
        end_date,
    )

    query = """
        SELECT
            date(
                created_at,
                '-' || (
                    (CAST(strftime('%w', created_at) AS INTEGER) + 6) % 7
                ) || ' days'
            ) AS week_start,
            COUNT(*) AS created_count
        FROM support_tickets
        WHERE 1 = 1
    """

    params: list[Any] = []

    query = _append_datetime_filter(
        query,
        params,
        "created_at",
        start_date,
        end_date,
    )

    query += """
        GROUP BY week_start
        ORDER BY week_start
    """

    return _to_dataframe(
        conn,
        query,
        tuple(params),
    )


def get_weekly_ticket_resolved_trend(
    conn: sqlite3.Connection,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """获取每周已解决工单数量趋势。

    日期筛选基于 resolved_at。
    """
    start_date, end_date = _normalize_date_range(
        start_date,
        end_date,
    )

    query = """
        SELECT
            date(
                resolved_at,
                '-' || (
                    (CAST(strftime('%w', resolved_at) AS INTEGER) + 6) % 7
                ) || ' days'
            ) AS week_start,
            COUNT(*) AS resolved_count
        FROM support_tickets
        WHERE resolved_at IS NOT NULL
    """

    params: list[Any] = []

    query = _append_datetime_filter(
        query,
        params,
        "resolved_at",
        start_date,
        end_date,
    )

    query += """
        GROUP BY week_start
        ORDER BY week_start
    """

    return _to_dataframe(
        conn,
        query,
        tuple(params),
    )


def get_avg_resolve_time_by_category(
    conn: sqlite3.Connection,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """获取不同工单类别的平均解决时间，单位为小时。"""
    start_date, end_date = _normalize_date_range(
        start_date,
        end_date,
    )

    query = """
        SELECT
            category,
            created_at,
            resolved_at
        FROM support_tickets
        WHERE resolved_at IS NOT NULL
    """

    params: list[Any] = []

    query = _append_datetime_filter(
        query,
        params,
        "created_at",
        start_date,
        end_date,
    )

    frame = _to_dataframe(
        conn,
        query,
        tuple(params),
    )

    if frame.empty:
        return pd.DataFrame(
            columns=[
                "category",
                "avg_resolve_hours",
                "resolved_count",
            ]
        )

    frame["resolve_hours"] = _hours_between(
        frame,
        "created_at",
        "resolved_at",
    )

    frame = frame.dropna(
        subset=["resolve_hours"]
    )

    if frame.empty:
        return pd.DataFrame(
            columns=[
                "category",
                "avg_resolve_hours",
                "resolved_count",
            ]
        )

    result = (
        frame.groupby("category", as_index=False)
        .agg(
            avg_resolve_hours=("resolve_hours", "mean"),
            resolved_count=("resolve_hours", "count"),
        )
        .sort_values(
            ["resolved_count", "category"],
            ascending=[False, True],
        )
        .reset_index(drop=True)
    )

    result["avg_resolve_hours"] = (
        result["avg_resolve_hours"].round(2)
    )

    result["resolved_count"] = (
        result["resolved_count"].astype(int)
    )

    return result[
        [
            "category",
            "avg_resolve_hours",
            "resolved_count",
        ]
    ]


def get_unresolved_ticket_details(
    conn: sqlite3.Connection,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    observation_date: str = OBSERVATION_BASE_DATE,
) -> pd.DataFrame:
    """获取未解决工单明细及等待时长。

    等待时长以观察基准日当天 23:59:59 计算。
    """
    start_date, end_date = _normalize_date_range(
        start_date,
        end_date,
    )

    observation_date = _parse_date(
        observation_date
    )

    if observation_date is None:
        raise ValueError(
            "observation_date 不能为空"
        )

    query = """
        SELECT
            t.ticket_id,
            t.customer_id,
            c.company_name,
            t.category,
            t.priority,
            t.created_at,
            t.status
        FROM support_tickets AS t
        INNER JOIN customers AS c
            ON t.customer_id = c.customer_id
        WHERE t.status IN ('open', 'in_progress')
    """

    params: list[Any] = []

    query = _append_datetime_filter(
        query,
        params,
        "t.created_at",
        start_date,
        end_date,
    )

    query += """
        ORDER BY t.created_at
    """

    frame = _to_dataframe(
        conn,
        query,
        tuple(params),
    )

    columns = [
        "ticket_id",
        "customer_id",
        "company_name",
        "category",
        "priority",
        "created_at",
        "status",
        "wait_hours",
    ]

    if frame.empty:
        return pd.DataFrame(columns=columns)

    observation_end = datetime.strptime(
        f"{observation_date}T23:59:59",
        f"{DATE_FORMAT}T%H:%M:%S",
    )

    created_at = pd.to_datetime(
        frame["created_at"],
        format=DATETIME_FORMAT,
        errors="coerce",
    )

    frame["wait_hours"] = (
        observation_end - created_at
    ).dt.total_seconds().div(3600).round(2)

    # 超出观察基准日的记录不应产生负等待时长
    frame.loc[
        frame["wait_hours"] < 0,
        "wait_hours",
    ] = 0.0

    return frame[columns]


def get_ticket_wait_time_stats(
    conn: sqlite3.Connection,
    observation_date: str = OBSERVATION_BASE_DATE,
) -> dict[str, Any]:
    """获取未解决工单等待时长和已解决工单处理时长统计。"""
    unresolved = get_unresolved_ticket_details(
        conn,
        observation_date=observation_date,
    )

    unresolved_values = (
        unresolved["wait_hours"].dropna()
        if not unresolved.empty
        else pd.Series(dtype="float64")
    )

    resolved_query = """
        SELECT
            created_at,
            resolved_at
        FROM support_tickets
        WHERE resolved_at IS NOT NULL
    """

    resolved_frame = _to_dataframe(
        conn,
        resolved_query,
    )

    resolved_values = _hours_between(
        resolved_frame,
        "created_at",
        "resolved_at",
    )

    def summarize(
        values: pd.Series,
    ) -> dict[str, Any]:
        if values.empty:
            return {
                "count": 0,
                "max": None,
                "avg": None,
                "median": None,
            }

        return {
            "count": int(values.count()),
            "max": round(float(values.max()), 2),
            "avg": round(float(values.mean()), 2),
            "median": round(float(values.median()), 2),
        }

    return {
        "unresolved_wait_stats": summarize(
            unresolved_values
        ),
        "resolved_duration_stats": summarize(
            resolved_values
        ),
    }


# ---------------------------------------------------------------------------
# 4. 客户群体分析
# ---------------------------------------------------------------------------

def get_group_analysis(
    conn: sqlite3.Connection,
    group_by: str = "industry",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """按行业、区域或套餐统计客户活跃及服务情况。

    支持分组字段：
    industry、region、plan_type。

    返回：
    group_value、
    customer_count、
    active_customer_count、
    active_rate、
    core_feature_customer_count、
    core_adoption_rate、
    total_tickets、
    unresolved_tickets。
    """
    if group_by not in _ALLOWED_GROUP_FIELDS:
        allowed = ", ".join(
            sorted(_ALLOWED_GROUP_FIELDS)
        )

        raise ValueError(
            f"不支持的分组字段：{group_by!r}。可选值：{allowed}"
        )

    start_date, end_date = _normalize_date_range(
        start_date,
        end_date,
    )

    # 产品使用数据筛选
    usage_conditions = []
    usage_params: list[Any] = []

    if start_date:
        usage_conditions.append(
            "week_start >= ?"
        )
        usage_params.append(start_date)

    if end_date:
        usage_conditions.append(
            "week_start <= ?"
        )
        usage_params.append(end_date)

    usage_where = (
        "WHERE " + " AND ".join(usage_conditions)
        if usage_conditions
        else ""
    )

    # 工单数据筛选
    ticket_conditions = []
    ticket_params: list[Any] = []

    if start_date:
        ticket_conditions.append(
            "date(created_at) >= ?"
        )
        ticket_params.append(start_date)

    if end_date:
        ticket_conditions.append(
            "date(created_at) <= ?"
        )
        ticket_params.append(end_date)

    ticket_where = (
        "WHERE " + " AND ".join(ticket_conditions)
        if ticket_conditions
        else ""
    )

    query = f"""
        WITH usage_agg AS (
            SELECT
                customer_id,
                MAX(
                    CASE
                        WHEN active_users > 0 THEN 1
                        ELSE 0
                    END
                ) AS is_active,
                MAX(
                    CASE
                        WHEN core_feature_uses > 0 THEN 1
                        ELSE 0
                    END
                ) AS uses_core_feature
            FROM usage_weekly
            {usage_where}
            GROUP BY customer_id
        ),
        ticket_agg AS (
            SELECT
                customer_id,
                COUNT(*) AS total_tickets,
                SUM(
                    CASE
                        WHEN status IN ('open', 'in_progress')
                        THEN 1
                        ELSE 0
                    END
                ) AS unresolved_tickets
            FROM support_tickets
            {ticket_where}
            GROUP BY customer_id
        )
        SELECT
            c.{group_by} AS group_value,
            COUNT(*) AS customer_count,
            SUM(COALESCE(u.is_active, 0))
                AS active_customer_count,
            SUM(COALESCE(u.uses_core_feature, 0))
                AS core_feature_customer_count,
            SUM(COALESCE(t.total_tickets, 0))
                AS total_tickets,
            SUM(COALESCE(t.unresolved_tickets, 0))
                AS unresolved_tickets
        FROM customers AS c
        LEFT JOIN usage_agg AS u
            ON c.customer_id = u.customer_id
        LEFT JOIN ticket_agg AS t
            ON c.customer_id = t.customer_id
        GROUP BY c.{group_by}
        ORDER BY c.{group_by}
    """

    frame = _to_dataframe(
        conn,
        query,
        tuple(usage_params + ticket_params),
    )

    if frame.empty:
        return pd.DataFrame(
            columns=[
                "group_value",
                "customer_count",
                "active_customer_count",
                "active_rate",
                "core_feature_customer_count",
                "core_adoption_rate",
                "total_tickets",
                "unresolved_tickets",
            ]
        )

    integer_columns = [
        "customer_count",
        "active_customer_count",
        "core_feature_customer_count",
        "total_tickets",
        "unresolved_tickets",
    ]

    frame[integer_columns] = (
        frame[integer_columns]
        .fillna(0)
        .astype(int)
    )

    # 客户活跃率
    frame["active_rate"] = frame.apply(
        lambda row: _percentage(
            _safe_divide(
                row["active_customer_count"],
                row["customer_count"],
            )
        ),
        axis=1,
    )

    # 核心功能采用率
    frame["core_adoption_rate"] = frame.apply(
        lambda row: _percentage(
            _safe_divide(
                row["core_feature_customer_count"],
                row["customer_count"],
            )
        ),
        axis=1,
    )

    columns = [
        "group_value",
        "customer_count",
        "active_customer_count",
        "active_rate",
        "core_feature_customer_count",
        "core_adoption_rate",
        "total_tickets",
        "unresolved_tickets",
    ]

    return frame[columns]