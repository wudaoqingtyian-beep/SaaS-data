# -*- coding: utf-8 -*-
"""Follow-up Management Page"""

import streamlit as st
import pandas as pd
from datetime import date, datetime

from src.database import get_connection
from src.config import DB_PATH

st.title("Customer Follow-up Management")
st.markdown("---")

conn = get_connection(DB_PATH)

# --- Select Customer ---
st.subheader("Select Customer")
customer_search = st.text_input("Search customer name", "")
customers = conn.execute("SELECT customer_id, company_name FROM customers WHERE company_name LIKE ?",
                         (f"%{customer_search}%",)).fetchall()
customer_ids = [c[0] for c in customers] if customers else []
selected_customer_id = st.selectbox("Select customer", [""] + customer_ids) if customer_ids else None

# --- Add Follow-up Record ---
if selected_customer_id:
    st.subheader("Add Follow-up Record")
    with st.form(key="add_followup_form"):
        col1, col2 = st.columns(2)
        with col1:
            followup_date = st.date_input("Follow-up date", value=date.today())
            followup_type = st.selectbox("Follow-up type", 
                                         ["training", "check_in", "issue_resolution", "product_guidance", "renewal_communication"])
            trigger_reason = st.selectbox("Trigger reason",
                                          ["usage_decline", "low_adoption", "repeated_tickets", "overdue_ticket",
                                           "upcoming_renewal", "manual"])
            action_description = st.text_area("Action Description *", "")
        with col2:
            followup_person = st.text_input("Follow-up person", "")
            result_status = st.selectbox("Result status", ["planned", "completed", "cancelled"])
            result_note = st.text_area("Result note", "")
        
        submit_btn = st.form_submit_button("Save Follow-up Record")
        
        if submit_btn:
            # Validate required fields
            if not action_description:
                st.error("Action description is required")
            else:
                # Generate followup_id
                max_id = conn.execute("SELECT MAX(followup_id) FROM followup_records").fetchone()[0] or 0
                new_id = max_id + 1
                
                created_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                
                conn.execute(
                    "INSERT INTO followup_records (followup_id, customer_id, followup_date, followup_type, trigger_reason, "
                    "action_description, result_status, result_note, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (new_id, selected_customer_id, followup_date.strftime("%Y-%m-%d"), followup_type,
                     trigger_reason, action_description, result_status, result_note, created_at)
                )
                conn.commit()
                st.success("Follow-up record saved successfully")
                st.rerun()

# --- Historical Records ---
st.subheader("Historical Follow-up Records")
if selected_customer_id:
    records = conn.execute(
        "SELECT followup_id, followup_date, followup_type, trigger_reason, action_description, result_status, result_note, created_at "
        "FROM followup_records WHERE customer_id = ? ORDER BY followup_date DESC",
        (selected_customer_id,)
    ).fetchall()

    if records:
        df = pd.DataFrame(records, columns=["Follow-up ID", "Date", "Type", "Trigger Reason", "Action Description",
                                             "Result Status", "Result Note", "Created At"])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No follow-up records found for this customer")
else:
    st.info("Select a customer to view follow-up records")