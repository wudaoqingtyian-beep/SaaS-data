# -*- coding: utf-8 -*-
"""Customer Management Page"""

import streamlit as st
import pandas as pd
from datetime import date

from src.database import (
    get_connection,
    get_all_customers,
    get_customer_by_id,
    update_customer,
    delete_customer,
    customer_exists,
    search_customers,
    add_customer,
)
from src.config import DB_PATH

st.title("Customer Management")
conn = get_connection(DB_PATH)
customers = get_all_customers(conn)
st.write("Customers:", len(customers))

# Customer list
st.subheader("Customer List")
if customers:
    df = pd.DataFrame(customers)
    st.dataframe(df, use_container_width=True)
else:
    st.info("No customers found")

# Add Customer
st.subheader("Add Customer")
with st.form(key="add_customer_form"):
    col1, col2 = st.columns(2)
    with col1:
        new_customer_id = st.text_input("Customer ID (leave blank to auto-generate)", "")
        new_company_name = st.text_input("Company Name *", "")
        new_industry = st.selectbox("Industry", ["制造业", "零售", "物流", "教育", "专业服务", "互联网", "医疗健康", "金融服务"])
        new_company_size = st.selectbox("Company Size", ["small", "medium", "large"])
        new_licensed_users = st.number_input("Licensed Users", min_value=1, value=10)
    with col2:
        new_contract_start = st.date_input("Contract Start", value=date(2026, 8, 10))
        new_contract_end = st.date_input("Contract End", value=date(2027, 8, 10))
        new_account_owner = st.text_input("Account Owner", "")
        new_customer_status = st.selectbox("Customer Status", ["活跃", "潜在", "流失"], index=0)
        new_contact_person = st.text_input("Contact Person", "")
        new_contact_info = st.text_input("Contact Info", "")
    new_notes = st.text_area("Notes", "")

    submit_btn = st.form_submit_button("Save Customer")

    if submit_btn:
        if not new_company_name:
            st.error("Company name is required")
        elif new_contract_end < new_contract_start:
            st.error("Contract end date cannot be earlier than start date")
        else:
            # Auto-generate customer ID
            if not new_customer_id:
                existing_ids = [c[0] for c in conn.execute("SELECT customer_id FROM customers").fetchall()]
                next_num = 1
                while f"CUST{next_num:04d}" in existing_ids:
                    next_num += 1
                new_customer_id = f"CUST{next_num:04d}"

            if customer_exists(conn, new_customer_id):
                st.error(f"客户ID {new_customer_id} 已存在，请使用其他ID")
            else:
                success = add_customer(
                    conn,
                    customer_id=new_customer_id,
                    company_name=new_company_name,
                    industry=new_industry,
                    company_size=new_company_size,
                    region="华东",
                    plan_type="basic",
                    licensed_users=new_licensed_users,
                    signup_date="2026-11-19",
                    contract_start_date=new_contract_start.strftime("%Y-%m-%d"),
                    contract_end_date=new_contract_end.strftime("%Y-%m-%d"),
                    monthly_fee=1000.0,
                    account_owner=new_account_owner,
                    customer_status=new_customer_status,
                    contact_person=new_contact_person,
                    contact_info=new_contact_info,
                    notes=new_notes,
                )
                if success:
                    st.success(f"客户 {new_company_name} (ID: {new_customer_id}) 添加成功")
                    st.rerun()
                else:
                    st.error("保存客户失败，请检查日志")

# ============================================================
# 编辑客户
# ============================================================
st.subheader("编辑客户")
edit_id = st.text_input("输入客户ID进行编辑", key="edit_customer_id")
if edit_id:
    customer = get_customer_by_id(conn, edit_id)
    if customer:
        with st.form(key="edit_customer_form"):
            col1, col2 = st.columns(2)
            with col1:
                edit_company_name = st.text_input("客户名称", value=customer.get("company_name", ""))
                edit_industry = st.selectbox("所属行业", ["制造业", "零售", "物流", "教育", "专业服务", "互联网", "医疗健康", "金融服务"],
                                             index=["制造业", "零售", "物流", "教育", "专业服务", "互联网", "医疗健康", "金融服务"].index(
                                                 customer.get("industry", "制造业") if customer.get("industry") in ["制造业", "零售", "物流", "教育", "专业服务", "互联网", "医疗健康", "金融服务"] else 0))
                edit_company_size = st.selectbox("公司规模", ["small", "medium", "large"],
                                                 index=["small", "medium", "large"].index(
                                                     customer.get("company_size", "small") if customer.get("company_size") in ["small", "medium", "large"] else 0))
                edit_licensed_users = st.number_input("授权用户数", min_value=1, value=int(customer.get("licensed_users", 10)))
            with col2:
                edit_contract_start = st.date_input("合同开始日期", value=pd.to_datetime(customer.get("contract_start_date", "2026-08-10")).date())
                edit_contract_end = st.date_input("合同到期日期", value=pd.to_datetime(customer.get("contract_end_date", "2027-08-10")).date())
                edit_account_owner = st.text_input("客户负责人", value=customer.get("account_owner", ""))
                edit_customer_status = st.selectbox("客户状态", ["活跃", "潜在", "流失"],
                                                    index=["活跃", "潜在", "流失"].index(
                                                        customer.get("customer_status", "活跃") if customer.get("customer_status") in ["活跃", "潜在", "流失"] else 0))
                edit_contact_person = st.text_input("联系人", value=customer.get("contact_person", ""))
                edit_contact_info = st.text_input("联系方式", value=customer.get("contact_info", ""))
            edit_notes = st.text_area("备注", value=customer.get("notes", ""))

            col_save, col_cancel = st.columns(2)
            with col_save:
                if st.form_submit_button("更新客户"):
                    success = update_customer(
                        conn,
                        customer_id=edit_id,
                        company_name=edit_company_name if edit_company_name else None,
                        industry=edit_industry if edit_industry else None,
                        company_size=edit_company_size if edit_company_size else None,
                        region="华东",
                        plan_type="basic",
                        licensed_users=edit_licensed_users if edit_licensed_users else None,
                        contract_start_date=edit_contract_start.strftime("%Y-%m-%d") if edit_contract_start else None,
                        contract_end_date=edit_contract_end.strftime("%Y-%m-%d") if edit_contract_end else None,
                        monthly_fee=float(customer.get("monthly_fee", 1000.0)),
                        account_owner=edit_account_owner if edit_account_owner else None,
                        customer_status=edit_customer_status if edit_customer_status else None,
                        contact_person=edit_contact_person if edit_contact_person else None,
                        contact_info=edit_contact_info if edit_contact_info else None,
                        notes=edit_notes if edit_notes else None,
                    )
                    if success:
                        st.success("客户信息更新成功")
                        st.rerun()
                    else:
                        st.error("更新客户失败")

            with col_cancel:
                if st.form_submit_button("取消"):
                    st.experimental_rerun()
    else:
        st.error("无法加载客户信息，请检查客户ID是否存在")
else:
    st.info("在上方输入客户ID进行编辑")

# ============================================================
# 删除客户
# ============================================================
st.subheader("删除客户")
delete_id = st.text_input("输入客户ID进行删除", key="delete_customer_id")
if delete_id:
    customer = get_customer_by_id(conn, delete_id)
    if customer:
        usage_count = conn.execute("SELECT COUNT(*) FROM usage_weekly WHERE customer_id = ?", (delete_id,)).fetchone()[0]
        tickets_count = conn.execute("SELECT COUNT(*) FROM support_tickets WHERE customer_id = ?", (delete_id,)).fetchone()[0]
        followup_count = conn.execute("SELECT COUNT(*) FROM followup_records WHERE customer_id = ?", (delete_id,)).fetchone()[0]

        st.warning(f"⚠️ 如果删除此客户，将影响以下数据：")
        if usage_count > 0:
            st.write(f"  - {usage_count} 条使用数据记录")
        if tickets_count > 0:
            st.write(f"  - {tickets_count} 条工单记录")
        if followup_count > 0:
            st.write(f"  - {followup_count} 条跟进记录")

        st.markdown("**确定要删除此客户吗？**")
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("是的，永久删除", type="primary"):
                has_associated = usage_count > 0 or tickets_count > 0 or followup_count > 0
                if has_associated:
                    st.error("无法删除：客户存在关联的使用数据、工单或跟进记录。请先处理相关数据或手动重新分配。")
                else:
                    success = delete_customer(conn, delete_id)
                    if success:
                        st.success("客户删除成功")
                        st.rerun()
                    else:
                        st.error("删除客户失败")
        with col_no:
            if st.button("取消删除"):
                st.info("删除已取消")
    else:
        st.error("无法加载客户信息，请检查客户ID是否存在")
else:
    st.info("在上方输入客户ID进行删除")

conn.close()