
# -*- coding: utf-8 -*-
"""Usage Data Management Page"""

import streamlit as st
import pandas as pd
from datetime import date, datetime

from src.database import get_connection, search_customers
from src.config import DB_PATH


# ============================================================
# 页面配置
# ============================================================

st.title("📊 Usage Data Management")
st.markdown("---")


# ============================================================
# 数据库连接
# ============================================================

conn = get_connection(DB_PATH)


try:

    # ========================================================
    # 选择客户
    # ========================================================

    st.subheader("Select Customer")

    col1, col2 = st.columns(2)

    with col1:
        customer_search = st.text_input(
            "Search customer name",
            "",
        )

    with col2:
        customers = search_customers(
            conn,
            name=customer_search if customer_search else "",
        )

        customer_ids = [
            c[0] for c in customers
        ] if customers else []

        selected_customer_id = (
            st.selectbox(
                "Select customer",
                customer_ids,
            )
            if customer_ids
            else None
        )

    # ========================================================
    # 客户使用数据管理
    # ========================================================

    if selected_customer_id:

        st.subheader("Input / Edit Weekly Usage Data")

        # 获取当前客户历史数据
        records = conn.execute(
            """
            SELECT
                usage_id,
                week_start,
                login_count,
                active_days,
                active_users,
                core_feature_users,
                core_feature_uses,
                usage_minutes
            FROM usage_weekly
            WHERE customer_id = ?
            ORDER BY week_start DESC
            """,
            (selected_customer_id,),
        ).fetchall()

        # 选择需要编辑的历史记录
        record_options = {
            "New Record": None
        }

        for record in records:
            record_options[
                f"{record[1]} (ID: {record[0]})"
            ] = record[0]

        selected_record_label = st.selectbox(
            "Select a record to edit (or create new)",
            list(record_options.keys()),
            key="usage_record_select",
        )

        selected_usage_id = record_options[
            selected_record_label
        ]

        selected_record = None

        if selected_usage_id is not None:

            selected_record = next(
                (
                    record
                    for record in records
                    if record[0] == selected_usage_id
                ),
                None,
            )

        # ====================================================
        # 数据输入表单
        # ====================================================

        with st.form(
            key="usage_data_form",
        ):

            col1, col2 = st.columns(2)

            with col1:

                week_start = st.date_input(
                    "Week start date",
                    value=(
                        datetime.strptime(
                            selected_record[1],
                            "%Y-%m-%d",
                        ).date()
                        if selected_record
                        else date(2026, 8, 10)
                    ),
                )

                login_count = st.number_input(
                    "Login count",
                    min_value=0,
                    value=(
                        int(selected_record[2])
                        if selected_record
                        else 10
                    ),
                )

                active_days = st.number_input(
                    "Active days (0-7)",
                    min_value=0,
                    max_value=7,
                    value=(
                        int(selected_record[3])
                        if selected_record
                        else 5
                    ),
                )

            with col2:

                active_users = st.number_input(
                    "Active users",
                    min_value=0,
                    value=(
                        int(selected_record[4])
                        if selected_record
                        else 8
                    ),
                )

                core_feature_users = st.number_input(
                    "Core feature users",
                    min_value=0,
                    value=(
                        int(selected_record[5])
                        if selected_record
                        else 3
                    ),
                )

                core_feature_uses = st.number_input(
                    "Core feature uses",
                    min_value=0,
                    value=(
                        int(selected_record[6])
                        if selected_record
                        else 5
                    ),
                )

                usage_minutes = st.number_input(
                    "Usage minutes",
                    min_value=0,
                    value=(
                        int(selected_record[7])
                        if selected_record
                        else 100
                    ),
                )

            submit_btn = st.form_submit_button(
                "Save Usage Data",
                type="primary",
            )

        # ====================================================
        # 保存数据
        # ====================================================

        if submit_btn:

            if active_days < 0 or active_days > 7:

                st.error(
                    "Active days must be between 0 and 7"
                )

            elif any(
                value < 0
                for value in [
                    login_count,
                    active_users,
                    core_feature_users,
                    core_feature_uses,
                    usage_minutes,
                ]
            ):

                st.error(
                    "Usage data cannot contain negative values"
                )

            elif core_feature_users > active_users:

                st.error(
                    "Core feature users cannot exceed active users"
                )

            else:

                week_start_str = week_start.strftime(
                    "%Y-%m-%d"
                )

                try:

                    # 编辑已有记录
                    if selected_usage_id is not None:

                        conn.execute(
                            """
                            UPDATE usage_weekly
                            SET
                                week_start = ?,
                                login_count = ?,
                                active_days = ?,
                                active_users = ?,
                                core_feature_users = ?,
                                core_feature_uses = ?,
                                usage_minutes = ?
                            WHERE usage_id = ?
                            """,
                            (
                                week_start_str,
                                login_count,
                                active_days,
                                active_users,
                                core_feature_users,
                                core_feature_uses,
                                usage_minutes,
                                selected_usage_id,
                            ),
                        )

                        conn.commit()

                        st.success(
                            "Usage data updated successfully"
                        )

                    else:

                        # 检查客户该周是否已有记录
                        existing = conn.execute(
                            """
                            SELECT usage_id
                            FROM usage_weekly
                            WHERE customer_id = ?
                              AND week_start = ?
                            """,
                            (
                                selected_customer_id,
                                week_start_str,
                            ),
                        ).fetchone()

                        if existing:

                            # 更新已有记录
                            conn.execute(
                                """
                                UPDATE usage_weekly
                                SET
                                    login_count = ?,
                                    active_days = ?,
                                    active_users = ?,
                                    core_feature_users = ?,
                                    core_feature_uses = ?,
                                    usage_minutes = ?
                                WHERE usage_id = ?
                                """,
                                (
                                    login_count,
                                    active_days,
                                    active_users,
                                    core_feature_users,
                                    core_feature_uses,
                                    usage_minutes,
                                    existing[0],
                                ),
                            )

                            conn.commit()

                            st.success(
                                "Existing weekly record updated successfully"
                            )

                        else:

                            # 新增记录
                            conn.execute(
                                """
                                INSERT INTO usage_weekly (
                                    customer_id,
                                    week_start,
                                    login_count,
                                    active_days,
                                    active_users,
                                    core_feature_users,
                                    core_feature_uses,
                                    usage_minutes
                                )
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    selected_customer_id,
                                    week_start_str,
                                    login_count,
                                    active_days,
                                    active_users,
                                    core_feature_users,
                                    core_feature_uses,
                                    usage_minutes,
                                ),
                            )

                            conn.commit()

                            st.success(
                                "Usage data saved successfully"
                            )

                    st.rerun()

                except Exception as exc:

                    conn.rollback()

                    st.error(
                        f"Save failed: {exc}"
                    )

    # ========================================================
    # 历史记录
    # ========================================================

    st.subheader("Historical Records for This Customer")

    if selected_customer_id:

        records = conn.execute(
            """
            SELECT
                usage_id,
                week_start,
                login_count,
                active_days,
                active_users,
                core_feature_users,
                core_feature_uses,
                usage_minutes
            FROM usage_weekly
            WHERE customer_id = ?
            ORDER BY week_start DESC
            """,
            (selected_customer_id,),
        ).fetchall()

        if records:

            df = pd.DataFrame(
                records,
                columns=[
                    "Usage ID",
                    "Week Start",
                    "Login Count",
                    "Active Days",
                    "Active Users",
                    "Core Feature Users",
                    "Core Feature Uses",
                    "Usage Minutes",
                ],
            )

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
            )

            # =================================================
            # 删除记录
            # =================================================

            st.subheader("Delete Usage Record")

            delete_options = {
                (
                    f"ID: {record[0]} | "
                    f"Week: {record[1]}"
                ): record[0]
                for record in records
            }

            selected_delete_label = st.selectbox(
                "Select record to delete",
                list(delete_options.keys()),
                key="delete_usage_select",
            )

            selected_delete_id = delete_options[
                selected_delete_label
            ]

            confirm_delete = st.checkbox(
                "I confirm that I want to delete this record",
                key="confirm_usage_delete",
            )

            if st.button(
                "Delete Selected Record",
                type="secondary",
            ):

                if not confirm_delete:

                    st.warning(
                        "Please confirm deletion first"
                    )

                else:

                    try:

                        conn.execute(
                            """
                            DELETE FROM usage_weekly
                            WHERE usage_id = ?
                            """,
                            (selected_delete_id,),
                        )

                        conn.commit()

                        st.success(
                            "Usage record deleted successfully"
                        )

                        st.rerun()

                    except Exception as exc:

                        conn.rollback()

                        st.error(
                            f"Delete failed: {exc}"
                        )

        else:

            st.info(
                "No historical records found for this customer"
            )

    else:

        st.info(
            "Select a customer to view usage data"
        )


finally:

    conn.close()
