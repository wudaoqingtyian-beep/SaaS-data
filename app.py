# -*- coding: utf-8 -*-
"""B2B SaaS 客户使用与服务运营分析平台 - Streamlit 应用入口。"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from src.config import DB_PATH, DATE_FORMAT, DATETIME_FORMAT
from src.metrics import (
    get_connection,
    get_business_overview,
    get_weekly_activity_trend,
    get_avg_active_days_trend,
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
)


# ============================================================
# 页面配置
# ============================================================

st.set_page_config(
    page_title="B2B SaaS 客户分析平台",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.8rem;
            padding-bottom: 2.2rem;
        }
        [data-testid="stSidebar"] {
            background-color: #f7f9fc;
        }
        h1, h2, h3 {
            color: #24364b;
        }
        div[data-testid="stMetric"] {
            background-color: #f7f9fc;
            border: 1px solid #e8edf3;
            padding: 12px 14px;
            border-radius: 10px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

OBSERVATION_BASE_DATE = "2026-11-01"

RISK_COLORS = {
    "低风险": "#2e9d68",
    "中风险": "#e3a12f",
    "高风险": "#d9534f",
}

FOLLOWUP_TYPE_LABELS = {
    "training": "产品培训",
    "check_in": "日常回访",
    "issue_resolution": "问题处理",
    "product_guidance": "功能使用指导",
    "renewal_communication": "续费沟通",
}

FOLLOWUP_REASON_LABELS = {
    "usage_decline": "使用活跃度下降",
    "low_adoption": "核心功能采用不足",
    "repeated_tickets": "重复工单较多",
    "overdue_ticket": "工单处理超时",
    "upcoming_renewal": "合同即将到期",
    "manual": "人工安排",
}

FOLLOWUP_STATUS_LABELS = {
    "planned": "计划中",
    "completed": "已完成",
    "cancelled": "已取消",
}

TICKET_CATEGORY_LABELS = {
    "login_access": "登录与账号权限",
    "integration_api": "系统集成与 API",
    "feature_usage": "功能使用咨询",
    "data_issue": "数据导入或数据异常",
    "billing": "订阅或账单咨询",
    "performance": "性能或响应速度",
    "other": "其他问题",
}

TICKET_PRIORITY_LABELS = {
    "low": "低",
    "medium": "中",
    "high": "高",
    "urgent": "紧急",
}

TICKET_STATUS_LABELS = {
    "open": "待处理",
    "in_progress": "处理中",
    "resolved": "已解决",
    "closed": "已关闭",
}


# ============================================================
# 通用辅助函数
# ============================================================

def format_number(value: Any, suffix: str = "") -> str:
    """格式化数值，缺失值显示为暂无数据。"""
    if value is None or pd.isna(value):
        return "暂无数据"

    if isinstance(value, float):
        return f"{value:,.2f}{suffix}"

    if isinstance(value, (int, float)):
        return f"{value:,}{suffix}"

    return f"{value}{suffix}"


def format_percent(value: Any) -> str:
    if value is None or pd.isna(value):
        return "暂无数据"

    return f"{float(value):.2f}%"


def show_empty(message: str = "当前筛选条件下暂无数据") -> None:
    st.info(message)


def load_customers(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query(
        """
        SELECT customer_id, company_name, industry, region,
               plan_type, licensed_users,
               contract_start_date, contract_end_date
        FROM customers
        ORDER BY company_name
        """,
        conn,
    )


def load_followups(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query(
        """
        SELECT
            f.followup_id,
            f.customer_id,
            c.company_name,
            f.followup_date,
            f.followup_type,
            f.trigger_reason,
            f.action_description,
            f.result_status,
            f.result_note,
            f.created_at
        FROM followup_records AS f
        INNER JOIN customers AS c
            ON c.customer_id = f.customer_id
        ORDER BY f.followup_date DESC, f.followup_id DESC
        """,
        conn,
    )


def get_date_bounds(
    conn: sqlite3.Connection,
) -> tuple[date, date]:

    row = conn.execute(
        "SELECT MIN(week_start), MAX(week_start) FROM usage_weekly"
    ).fetchone()

    if not row or not row[0] or not row[1]:
        return date(2026, 8, 10), date(2026, 11, 1)

    return (
        datetime.strptime(row[0], DATE_FORMAT).date(),
        datetime.strptime(row[1], DATE_FORMAT).date(),
    )


def render_date_filter(
    conn: sqlite3.Connection,
) -> tuple[str, str]:

    min_date, max_date = get_date_bounds(conn)

    st.sidebar.subheader("📅 日期筛选")

    start_value = st.sidebar.date_input(
        "开始日期",
        value=min_date,
        min_value=min_date,
        max_value=max_date,
        key="global_start_date",
    )

    end_value = st.sidebar.date_input(
        "结束日期",
        value=max_date,
        min_value=min_date,
        max_value=max_date,
        key="global_end_date",
    )

    if start_value > end_value:
        st.sidebar.error("开始日期不能晚于结束日期")
        st.stop()

    return (
        start_value.strftime(DATE_FORMAT),
        end_value.strftime(DATE_FORMAT),
    )


def render_kpi(
    label: str,
    value: Any,
    suffix: str = "",
) -> None:
    st.metric(label, format_number(value, suffix))


def get_risk_api():
    """延迟导入风险模块。"""
    from src.risk_rules import (
        calculate_customer_risk,
        calculate_all_customers_risk,
    )

    return calculate_customer_risk, calculate_all_customers_risk


def risk_reason_text(risk: dict[str, Any]) -> str:

    reasons = risk.get("triggered_rules", []) or []
    descriptions = []

    for item in reasons:
        if isinstance(item, dict):
            descriptions.append(
                str(item.get("description", item))
            )
        else:
            descriptions.append(str(item))

    return (
        "；".join(descriptions)
        if descriptions
        else "暂无触发规则"
    )


def plot_line(
    frame: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    y_label: str,
) -> None:

    if frame.empty:
        show_empty()
        return

    fig = px.line(
        frame,
        x=x,
        y=y,
        title=title,
        markers=True,
        labels={
            x: "日期",
            y: y_label,
        },
    )

    fig.update_layout(
        margin=dict(l=10, r=10, t=55, b=10)
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )


def plot_bar(
    frame: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    x_label: str = "",
    y_label: str = "",
) -> None:

    if frame.empty:
        show_empty()
        return

    fig = px.bar(
        frame,
        x=x,
        y=y,
        title=title,
        labels={
            x: x_label or x,
            y: y_label or y,
        },
        text_auto=True,
    )

    fig.update_layout(
        margin=dict(l=10, r=10, t=55, b=10)
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )


# ============================================================
# 页面一：经营数据总览
# ============================================================

def render_overview_page(
    conn: sqlite3.Connection,
    start_date: str,
    end_date: str,
) -> None:

    st.title("📊 客户经营数据总览")
    st.caption("快速了解企业客户的整体使用情况和服务表现")

    overview = get_business_overview(
        conn,
        start_date,
        end_date,
    )

    # 核心 KPI
    st.subheader("核心经营指标")

    cols = st.columns(4)

    metrics = [
        ("企业客户总数", overview.get("total_customers"), " 家"),
        ("近期活跃客户数", overview.get("active_customers"), " 家"),
        ("客户活跃率", overview.get("active_rate"), "%"),
        ("核心功能采用率", overview.get("core_adoption_rate"), "%"),
    ]

    for col, (label, value, suffix) in zip(cols, metrics):
        with col:
            if suffix == "%":
                st.metric(label, format_percent(value))
            else:
                render_kpi(label, value, suffix)

    cols = st.columns(4)

    metrics = [
        ("工单总量", overview.get("total_tickets"), " 个"),
        ("未解决工单", overview.get("unresolved_tickets"), " 个"),
        ("工单解决率", overview.get("resolution_rate"), "%"),
        ("平均满意度", overview.get("avg_satisfaction"), " 分"),
    ]

    for col, (label, value, suffix) in zip(cols, metrics):
        with col:
            if suffix == "%":
                st.metric(label, format_percent(value))
            else:
                render_kpi(label, value, suffix)

    cols = st.columns(2)

    with cols[0]:
        render_kpi(
            "平均首次响应时间",
            overview.get("avg_first_response_hours"),
            " 小时",
        )

    with cols[1]:
        render_kpi(
            "平均解决时间",
            overview.get("avg_resolve_hours"),
            " 小时",
        )

    # 产品使用趋势
    st.divider()
    st.subheader("📈 产品使用趋势")

    left, right = st.columns(2)

    with left:
        activity = get_weekly_activity_trend(
            conn,
            start_date,
            end_date,
        )

        plot_line(
            activity,
            "week_start",
            "active_customer_count",
            "每周活跃客户数",
            "活跃客户数",
        )

    with right:
        active_days = get_avg_active_days_trend(
            conn,
            start_date,
            end_date,
        )

        plot_line(
            active_days,
            "week_start",
            "avg_active_days",
            "每周平均活跃天数",
            "平均活跃天数",
        )

    # 客户群体对比
    st.divider()
    st.subheader("不同客户群体对比")

    tab_plan, tab_industry = st.tabs(
        ["按套餐类型", "按行业"]
    )

    with tab_plan:
        plan_data = get_activity_by_plan(
            conn,
            start_date,
            end_date,
        )

        if not plan_data.empty:
            plot_bar(
                plan_data,
                "plan_type",
                "active_rate",
                "不同套餐客户活跃率",
                "套餐类型",
                "活跃率（%）",
            )

            st.dataframe(
                plan_data,
                use_container_width=True,
                hide_index=True,
            )
        else:
            show_empty()

    with tab_industry:
        industry_data = get_activity_by_industry(
            conn,
            start_date,
            end_date,
        )

        if not industry_data.empty:
            plot_bar(
                industry_data,
                "industry",
                "active_rate",
                "不同行业客户活跃率",
                "行业",
                "活跃率（%）",
            )

            st.dataframe(
                industry_data,
                use_container_width=True,
                hide_index=True,
            )
        else:
            show_empty()


# ============================================================
# 页面二：客户使用与风险分析
# ============================================================

def render_customer_page(
    conn: sqlite3.Connection,
    start_date: str,
    end_date: str,
) -> None:

    st.title("👥 客户使用与风险分析")
    st.caption("分析客户产品使用情况，识别需要优先关注的企业客户")

    customers = load_customers(conn)

    if customers.empty:
        show_empty("客户表中暂无数据，请先运行模拟数据初始化脚本。")
        return

    try:
        (
            calculate_customer_risk,
            calculate_all_customers_risk,
        ) = get_risk_api()

        all_risks = calculate_all_customers_risk(conn)

    except Exception as exc:
        st.error(f"客户风险模块加载失败：{exc}")
        st.info(
            "请确认 src/risk_rules.py 已完成，"
            "且风险函数能够正常导入。"
        )
        return

    risk_frame = pd.DataFrame(all_risks)

    if risk_frame.empty:
        risk_frame = pd.DataFrame(
            columns=[
                "customer_id",
                "risk_score",
                "risk_level",
            ]
        )

    if not risk_frame.empty:
        risk_frame = risk_frame.merge(
            customers[
                [
                    "customer_id",
                    "company_name",
                    "industry",
                    "region",
                    "plan_type",
                ]
            ],
            on="customer_id",
            how="left",
        )

    # 风险等级概览
    st.subheader("客户风险概览")

    counts = {
        "低风险": 0,
        "中风险": 0,
        "高风险": 0,
    }

    if (
        not risk_frame.empty
        and "risk_level" in risk_frame.columns
    ):
        counts.update(
            risk_frame["risk_level"]
            .value_counts()
            .to_dict()
        )

    c1, c2, c3 = st.columns(3)

    c1.metric("低风险客户", f"{counts['低风险']} 家")
    c2.metric("中风险客户", f"{counts['中风险']} 家")
    c3.metric("高风险客户", f"{counts['高风险']} 家")

    st.caption(
        "风险等级是人工排查优先级，不代表客户一定会流失，"
        "也不是客户流失概率。"
    )

    # 风险客户筛选
    st.subheader("客户风险清单")

    filter_col1, filter_col2 = st.columns([1, 2])

    with filter_col1:
        selected_level = st.selectbox(
            "风险等级",
            ["全部", "高风险", "中风险", "低风险"],
            key="customer_risk_level_filter",
        )

    with filter_col2:
        search_text = st.text_input(
            "搜索客户名称或编号",
            key="customer_search_text",
        ).strip()

    filtered = risk_frame.copy()

    if selected_level != "全部" and not filtered.empty:
        filtered = filtered[
            filtered["risk_level"] == selected_level
        ]

    if search_text and not filtered.empty:
        mask = (
            filtered["customer_id"]
            .astype(str)
            .str.contains(search_text, case=False, na=False)
            |
            filtered["company_name"]
            .astype(str)
            .str.contains(search_text, case=False, na=False)
        )

        filtered = filtered[mask]

    if not filtered.empty:
        filtered = filtered.sort_values(
            "risk_score",
            ascending=False,
        )

        display_columns = [
            col
            for col in [
                "customer_id",
                "company_name",
                "industry",
                "region",
                "plan_type",
                "risk_score",
                "risk_level",
            ]
            if col in filtered.columns
        ]

        st.dataframe(
            filtered[display_columns],
            use_container_width=True,
            hide_index=True,
        )
    else:
        show_empty("没有符合当前筛选条件的客户。")

    # 客户详细诊断
    st.divider()
    st.subheader("客户详细诊断")

    customer_options = {
        f"{row.customer_id} - {row.company_name}": row.customer_id
        for row in customers.itertuples(index=False)
    }

    selected_customer_label = st.selectbox(
        "选择需要查看的客户",
        list(customer_options.keys()),
        key="customer_detail_select",
    )

    customer_id = customer_options[selected_customer_label]

    customer_info = customers[
        customers["customer_id"] == customer_id
    ].iloc[0]

    detail_cols = st.columns(3)

    detail_cols[0].write(
        f"**行业：** {customer_info['industry']}"
    )
    detail_cols[1].write(
        f"**地区：** {customer_info['region']}"
    )
    detail_cols[2].write(
        f"**套餐：** {customer_info['plan_type']}"
    )

    # 客户使用趋势
    usage = get_customer_usage_trend(
        conn,
        customer_id,
    )

    if not usage.empty:
        usage_chart = px.line(
            usage,
            x="week_start",
            y="active_days",
            markers=True,
            title="客户每周活跃天数",
            labels={
                "week_start": "周起始日",
                "active_days": "活跃天数",
            },
        )

        st.plotly_chart(
            usage_chart,
            use_container_width=True,
        )

        m1, m2, m3 = st.columns(3)

        m1.metric(
            "平均活跃天数",
            f"{usage['active_days'].mean():.1f} 天",
        )
        m2.metric(
            "平均登录次数",
            f"{usage['login_count'].mean():.1f} 次",
        )
        m3.metric(
            "平均核心功能使用次数",
            f"{usage['core_feature_uses'].mean():.1f} 次",
        )

    else:
        show_empty("该客户暂无产品使用记录。")

    # 前后四周活跃度对比
    comparison = get_customer_active_days_comparison(
        conn,
        customer_id,
    )

    with st.expander("查看前后 4 周活跃度对比"):
        c1, c2, c3 = st.columns(3)

        c1.metric(
            "最早 4 周平均活跃天数",
            format_number(
                comparison.get("first_4weeks_avg"),
                " 天",
            ),
        )

        c2.metric(
            "最近 4 周平均活跃天数",
            format_number(
                comparison.get("last_4weeks_avg"),
                " 天",
            ),
        )

        change = comparison.get("change_pct")

        c3.metric(
            "活跃天数下降幅度",
            format_percent(change)
            if change is not None
            else "无可比基线",
        )

        if not comparison.get("comparable", False):
            st.info(
                comparison.get(
                    "reason",
                    "当前数据不足，无法比较。",
                )
            )

    # 客户风险诊断
    st.markdown("#### 风险评分及触发原因")

    try:
        risk = calculate_customer_risk(
            conn,
            customer_id,
        )
    except Exception as exc:
        st.error(f"无法计算该客户风险：{exc}")
        return

    risk_level = risk.get("risk_level", "未知")
    risk_score = risk.get("risk_score", 0)

    risk_color = RISK_COLORS.get(
        risk_level,
        "#64748b",
    )

    st.markdown(
        f"<h3 style='color:{risk_color};'>风险等级：{risk_level}</h3>",
        unsafe_allow_html=True,
    )

    st.metric(
        "风险分数",
        f"{risk_score} / 100",
    )

    triggered = risk.get("triggered_rules", []) or []

    if triggered:
        for rule in triggered:
            if isinstance(rule, dict):
                description = rule.get(
                    "description",
                    str(rule),
                )
            else:
                description = str(rule)

            st.warning(f"触发规则：{description}")

    else:
        st.success("当前没有触发风险规则。")

    supporting = risk.get(
        "supporting_values",
        {},
    ) or {}

    # 将英文键名转换为中文显示
    chinese_supporting = {}
    key_map = {
        "recent_avg_active_days": "最近4周平均活跃天数",
        "early_avg_active_days": "最早4周平均活跃天数",
        "activity_decline_rate": "活跃度下降率(%)",
        "unresolved_ticket_count": "未解决工单数",
        "oldest_unresolved_ticket_hours": "最长未解决工单等待小时数",
        "contract_end_date": "合同结束日期",
        "days_to_contract_end": "距合同结束剩余天数",
        "observation_date": "观察基准日期",
    }
    for key, value in supporting.items():
        chinese_key = key_map.get(key, key)
        chinese_supporting[chinese_key] = value

    if supporting:
        st.markdown("#### 风险判断依据")
        st.json(chinese_supporting)


# ============================================================
# 页面三：服务运营与客户跟进
# ============================================================

def render_service_page(
    conn: sqlite3.Connection,
    start_date: str,
    end_date: str,
) -> None:

    st.title("🎧 服务运营与客户跟进")
    st.caption(
        "监控客户服务工单表现，记录运营动作并观察后续指标变化"
    )

    overview = get_business_overview(
        conn,
        start_date,
        end_date,
    )

    # 工单 KPI
    st.subheader("工单服务指标")

    cols = st.columns(4)

    cols[0].metric(
        "工单总量",
        format_number(
            overview.get("total_tickets"),
            " 个",
        ),
    )

    cols[1].metric(
        "未解决工单",
        format_number(
            overview.get("unresolved_tickets"),
            " 个",
        ),
    )

    cols[2].metric(
        "工单解决率",
        format_percent(
            overview.get("resolution_rate")
        ),
    )

    cols[3].metric(
        "平均首次响应时间",
        format_number(
            overview.get("avg_first_response_hours"),
            " 小时",
        ),
    )

    st.divider()
    st.subheader("工单结构与处理趋势")

    category_data = get_ticket_category_distribution(
        conn,
        start_date,
        end_date,
    )

    priority_data = get_ticket_priority_distribution(
        conn,
        start_date,
        end_date,
    )

    status_data = get_ticket_status_distribution(
        conn,
        start_date,
        end_date,
    )

    col1, col2 = st.columns(2)

    with col1:
        if not category_data.empty:
            category_data = category_data.copy()

            category_data["category_label"] = (
                category_data["category"]
                .map(TICKET_CATEGORY_LABELS)
                .fillna(category_data["category"])
            )

            plot_bar(
                category_data,
                "category_label",
                "ticket_count",
                "工单类别分布",
                "工单类别",
                "工单数量",
            )
        else:
            show_empty("暂无工单类别数据。")

    with col2:
        if not priority_data.empty:
            priority_data = priority_data.copy()

            priority_data["priority_label"] = (
                priority_data["priority"]
                .map(TICKET_PRIORITY_LABELS)
                .fillna(priority_data["priority"])
            )

            plot_bar(
                priority_data,
                "priority_label",
                "ticket_count",
                "工单优先级分布",
                "优先级",
                "工单数量",
            )
        else:
            show_empty("暂无工单优先级数据。")

    col3, col4 = st.columns(2)

    with col3:
        if not status_data.empty:
            status_data = status_data.copy()

            status_data["status_label"] = (
                status_data["status"]
                .map(TICKET_STATUS_LABELS)
                .fillna(status_data["status"])
            )

            plot_bar(
                status_data,
                "status_label",
                "ticket_count",
                "工单状态分布",
                "工单状态",
                "工单数量",
            )
        else:
            show_empty("暂无工单状态数据。")

    with col4:
        resolve_by_category = get_avg_resolve_time_by_category(
            conn,
            start_date,
            end_date,
        )

        if not resolve_by_category.empty:
            resolve_by_category = resolve_by_category.copy()

            resolve_by_category["category_label"] = (
                resolve_by_category["category"]
                .map(TICKET_CATEGORY_LABELS)
                .fillna(resolve_by_category["category"])
            )

            plot_bar(
                resolve_by_category,
                "category_label",
                "avg_resolve_hours",
                "不同类别平均解决时间",
                "工单类别",
                "平均解决时间（小时）",
            )
        else:
            show_empty("暂无已解决工单数据。")

    # 工单趋势
    col5, col6 = st.columns(2)

    with col5:
        created_trend = get_weekly_ticket_creation_trend(
            conn,
            start_date,
            end_date,
        )

        plot_line(
            created_trend,
            "week_start",
            "created_count",
            "每周工单创建量",
            "创建工单数",
        )

    with col6:
        resolved_trend = get_weekly_ticket_resolved_trend(
            conn,
            start_date,
            end_date,
        )

        plot_line(
            resolved_trend,
            "week_start",
            "resolved_count",
            "每周工单解决量",
            "解决工单数",
        )

    # 未解决工单明细
    st.divider()
    st.subheader("未解决工单明细")

    unresolved = get_unresolved_ticket_details(
        conn,
        start_date,
        end_date,
        observation_date=OBSERVATION_BASE_DATE,
    )

    if not unresolved.empty:
        f1, f2 = st.columns(2)

        with f1:
            priorities = sorted(
                unresolved["priority"].dropna().unique().tolist()
            )

            selected_priorities = st.multiselect(
                "按优先级筛选",
                priorities,
                default=priorities,
            )

        with f2:
            statuses = sorted(
                unresolved["status"].dropna().unique().tolist()
            )

            selected_statuses = st.multiselect(
                "按状态筛选",
                statuses,
                default=statuses,
            )

        filtered_unresolved = unresolved[
            unresolved["priority"].isin(selected_priorities)
            & unresolved["status"].isin(selected_statuses)
        ].copy()

        filtered_unresolved = filtered_unresolved.sort_values(
            "wait_hours",
            ascending=False,
        )

        filtered_unresolved["priority"] = (
            filtered_unresolved["priority"]
            .map(TICKET_PRIORITY_LABELS)
            .fillna(filtered_unresolved["priority"])
        )

        filtered_unresolved["status"] = (
            filtered_unresolved["status"]
            .map(TICKET_STATUS_LABELS)
            .fillna(filtered_unresolved["status"])
        )

        st.dataframe(
            filtered_unresolved,
            use_container_width=True,
            hide_index=True,
        )

    else:
        show_empty("当前日期范围内没有未解决工单。")

    # 新增客户跟进记录
    st.divider()
    st.subheader("新增客户跟进记录")

    customers = load_customers(conn)

    if customers.empty:
        show_empty("暂无客户，不能新增跟进记录。")
        return

    customer_labels = {
        f"{row.customer_id} - {row.company_name}": row.customer_id
        for row in customers.itertuples(index=False)
    }

    min_date, max_date = get_date_bounds(conn)

    with st.form(
        "add_followup_form",
        clear_on_submit=True,
    ):
        c1, c2 = st.columns(2)

        with c1:
            selected_label = st.selectbox(
                "选择客户",
                list(customer_labels.keys()),
            )

            followup_date = st.date_input(
                "跟进日期",
                value=max_date,
                min_value=min_date,
                max_value=max_date,
            )

            followup_type = st.selectbox(
                "跟进类型",
                list(FOLLOWUP_TYPE_LABELS.keys()),
                format_func=lambda value: FOLLOWUP_TYPE_LABELS[value],
            )

        with c2:
            trigger_reason = st.selectbox(
                "跟进触发原因",
                list(FOLLOWUP_REASON_LABELS.keys()),
                format_func=lambda value: FOLLOWUP_REASON_LABELS[value],
            )

            result_status = st.selectbox(
                "跟进状态",
                list(FOLLOWUP_STATUS_LABELS.keys()),
                format_func=lambda value: FOLLOWUP_STATUS_LABELS[value],
            )

            result_note = st.text_input(
                "跟进结果备注（选填）"
            )

        action_description = st.text_area(
            "采取的具体措施",
            placeholder="例如：安排产品培训，指导客户使用核心功能……",
            max_chars=500,
        )

        submitted = st.form_submit_button(
            "保存跟进记录",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if not action_description.strip():
            st.error("请填写采取的具体措施。")

        else:
            customer_id = customer_labels[selected_label]

            created_at = datetime.now().strftime(
                DATETIME_FORMAT
            )

            try:
                conn.execute(
                    """
                    INSERT INTO followup_records (
                        customer_id,
                        followup_date,
                        followup_type,
                        trigger_reason,
                        action_description,
                        result_status,
                        result_note,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        customer_id,
                        followup_date.strftime(DATE_FORMAT),
                        followup_type,
                        trigger_reason,
                        action_description.strip(),
                        result_status,
                        result_note.strip() or None,
                        created_at,
                    ),
                )

                conn.commit()

                st.success("跟进记录已成功保存。")
                st.rerun()

            except sqlite3.Error as exc:
                conn.rollback()
                st.error(f"保存失败：{exc}")

    # 跟进记录列表
    st.divider()
    st.subheader("客户跟进记录")

    followups = load_followups(conn)

    if followups.empty:
        show_empty("暂无客户跟进记录。")

    else:
        display_followups = followups.copy()

        display_followups["followup_type"] = (
            display_followups["followup_type"]
            .map(FOLLOWUP_TYPE_LABELS)
            .fillna(display_followups["followup_type"])
        )

        display_followups["trigger_reason"] = (
            display_followups["trigger_reason"]
            .map(FOLLOWUP_REASON_LABELS)
            .fillna(display_followups["trigger_reason"])
        )

        display_followups["result_status"] = (
            display_followups["result_status"]
            .map(FOLLOWUP_STATUS_LABELS)
            .fillna(display_followups["result_status"])
        )

        st.dataframe(
            display_followups[
                [
                    "followup_id",
                    "customer_id",
                    "company_name",
                    "followup_date",
                    "followup_type",
                    "trigger_reason",
                    "action_description",
                    "result_status",
                    "result_note",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

        # 跟进前后效果对比
        completed = followups[
            followups["result_status"] == "completed"
        ]

        if not completed.empty:
            st.markdown("#### 跟进前后使用指标对比")

            followup_options = {
                (
                    f"#{row.followup_id} | "
                    f"{row.company_name} | "
                    f"{row.followup_date}"
                ): int(row.followup_id)
                for row in completed.itertuples(index=False)
            }

            selected_followup_label = st.selectbox(
                "选择已完成的跟进记录",
                list(followup_options.keys()),
                key="followup_effect_select",
            )

            selected_followup_id = followup_options[
                selected_followup_label
            ]

            selected_record = completed[
                completed["followup_id"] == selected_followup_id
            ].iloc[0]

            followup_customer_id = selected_record["customer_id"]
            followup_day = selected_record["followup_date"]

            usage = get_customer_usage_trend(
                conn,
                followup_customer_id,
            )

            if usage.empty:
                st.info(
                    "该客户没有产品使用记录，暂无法评估跟进前后变化。"
                )

            else:
                before = usage[
                    usage["week_start"] < followup_day
                ].tail(4)

                after = usage[
                    usage["week_start"] >= followup_day
                ].head(4)

                st.caption(
                    f"跟进日期：{followup_day}；"
                    "前后窗口分别取跟进日期之前和之后最多 4 条周记录。"
                )

                if len(before) < 4 or len(after) < 4:
                    st.info(
                        "跟进前或跟进后数据不足 4 周，"
                        "暂无法进行完整窗口对比。"
                    )

                else:
                    before_active = float(
                        before["active_days"].mean()
                    )

                    after_active = float(
                        after["active_days"].mean()
                    )

                    before_core = float(
                        before["core_feature_uses"].mean()
                    )

                    after_core = float(
                        after["core_feature_uses"].mean()
                    )

                    e1, e2 = st.columns(2)

                    with e1:
                        st.metric(
                            "平均活跃天数（前 → 后）",
                            f"{after_active:.2f} 天",
                            delta=f"{after_active - before_active:+.2f} 天",
                        )

                    with e2:
                        st.metric(
                            "平均核心功能使用次数（前 → 后）",
                            f"{after_core:.2f} 次",
                            delta=f"{after_core - before_core:+.2f} 次",
                        )

                    st.caption(
                        f"跟进前窗口：{before.iloc[0]['week_start']} "
                        f"至 {before.iloc[-1]['week_start']}；"
                        f"跟进后窗口：{after.iloc[0]['week_start']} "
                        f"至 {after.iloc[-1]['week_start']}。"
                    )

                    st.caption(
                        "以上仅展示跟进前后指标变化，"
                        "不代表变化由该运营措施直接导致。"
                    )


# ============================================================
# 应用入口与页面路由
# ============================================================

# ============================================================
# 应用入口与页面路由
# ============================================================

def main() -> None:

    st.sidebar.title("📊 导航菜单")

    page = st.sidebar.radio(
        "选择模块",
        [
            "经营数据总览",
            "客户使用与风险分析",
            "服务运营与跟进",
            "客户管理",
            "使用数据管理",
            "工单管理",
            "客户跟进管理",
        ],
        label_visibility="collapsed",
    )

    # ========================================================
    # 数据库检查
    # ========================================================

    if not Path(DB_PATH).exists():
        st.error(f"未找到数据库文件：{DB_PATH}")
        st.info(
            "请先在项目根目录运行："
            "python scripts/init_demo_data.py"
        )
        st.stop()

    conn = get_connection(DB_PATH)

    try:

        # 检查必要的数据表
        required_tables = {
            "customers",
            "usage_weekly",
            "support_tickets",
            "followup_records",
        }

        existing_tables = {
            row[0]
            for row in conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            ).fetchall()
        }

        missing_tables = required_tables - existing_tables

        if missing_tables:
            st.error(
                "数据库缺少必要的数据表："
                + "、".join(sorted(missing_tables))
            )

            st.info(
                "请检查数据库初始化是否成功，"
                "不要在应用启动时自动重建数据库。"
            )

            st.stop()

        # ====================================================
        # 页面路由
        # ====================================================

        if page == "经营数据总览":

            start_date, end_date = render_date_filter(conn)

            render_overview_page(
                conn,
                start_date,
                end_date,
            )

        elif page == "客户使用与风险分析":

            start_date, end_date = render_date_filter(conn)

            render_customer_page(
                conn,
                start_date,
                end_date,
            )

        elif page == "服务运营与跟进":

            start_date, end_date = render_date_filter(conn)

            render_service_page(
                conn,
                start_date,
                end_date,
            )

        elif page == "客户管理":

            from src.customer_management import main as customer_main

            customer_main()

        elif page == "使用数据管理":

            from src.usage_management import main as usage_main

            usage_main()

        elif page == "工单管理":

            from src.ticket_management import main as ticket_main

            ticket_main()

        elif page == "客户跟进管理":

            from src.followup_management import main as followup_main

            followup_main()

    finally:

        conn.close()


if __name__ == "__main__":
    main()