
# -*- coding: utf-8 -*-
"""Ticket Management Page"""

import streamlit as st
import pandas as pd
from datetime import date, datetime

from src.database import get_connection
from src.config import DB_PATH


st.title("Ticket Management")
st.markdown("---")

conn = get_connection(DB_PATH)

try:
    # =========================================================
    # Load Customer IDs
    # =========================================================
    customer_rows = conn.execute(
        "SELECT customer_id FROM customers ORDER BY customer_id"
    ).fetchall()

    customer_ids = [row[0] for row in customer_rows]

    # =========================================================
    # Ticket List
    # =========================================================
    st.subheader("Ticket List")

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        customer_filter = st.selectbox(
            "Customer",
            [""] + customer_ids
        )

    with col2:
        status_filter = st.selectbox(
            "Status",
            ["", "open", "in_progress", "resolved", "closed"]
        )

    with col3:
        priority_filter = st.selectbox(
            "Priority",
            ["", "low", "medium", "high", "urgent"]
        )

    # Build query
    query = """
        SELECT *
        FROM support_tickets
        WHERE 1=1
    """

    params = []

    if customer_filter:
        query += " AND customer_id = ?"
        params.append(customer_filter)

    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)

    if priority_filter:
        query += " AND priority = ?"
        params.append(priority_filter)

    query += " ORDER BY created_at DESC"

    tickets = conn.execute(query, params).fetchall()

    # Display tickets
    if tickets:
        df = pd.DataFrame(
            tickets,
            columns=[
                "Ticket ID",
                "Customer ID",
                "Created At",
                "Category",
                "Priority",
                "Status",
                "Channel",
                "Subject",
                "First Response At",
                "Resolved At",
                "Satisfaction Score"
            ]
        )

        st.dataframe(
            df,
            use_container_width=True,
            height=400
        )
    else:
        st.info("No tickets found")

    # =========================================================
    # Create New Ticket
    # =========================================================
    st.subheader("Create New Ticket")

    if not customer_ids:
        st.warning("No customers available. Please add a customer first.")

    with st.form(key="create_ticket_form"):

        col1, col2 = st.columns(2)

        with col1:

            if customer_ids:
                new_customer_id = st.selectbox(
                    "Customer *",
                    customer_ids
                )
            else:
                new_customer_id = ""

            new_category = st.selectbox(
                "Category",
                [
                    "login_access",
                    "integration_api",
                    "feature_usage",
                    "data_issue",
                    "billing",
                    "performance",
                    "other"
                ]
            )

            new_priority = st.selectbox(
                "Priority",
                ["low", "medium", "high", "urgent"]
            )

        with col2:

            new_status = st.selectbox(
                "Status",
                ["open", "in_progress", "resolved", "closed"]
            )

            new_channel = st.selectbox(
                "Channel",
                ["email", "chat", "phone", "portal"]
            )

            new_subject = st.text_input(
                "Subject *",
                max_chars=200
            )

        new_description = st.text_area(
            "Description *"
        )

        submit_btn = st.form_submit_button(
            "Create Ticket",
            disabled=not customer_ids
        )

        if submit_btn:

            if not new_customer_id:
                st.error("Please select a customer.")

            elif not new_subject.strip():
                st.error("Subject is required.")

            elif not new_description.strip():
                st.error("Description is required.")

            else:

                try:
                    # Generate Ticket ID
                    last_ticket = conn.execute(
                        """
                        SELECT ticket_id
                        FROM support_tickets
                        ORDER BY ticket_id DESC
                        LIMIT 1
                        """
                    ).fetchone()

                    if last_ticket:
                        last_id = int(last_ticket[0].replace("TKT", ""))
                        ticket_id = f"TKT{last_id + 1:04d}"
                    else:
                        ticket_id = "TKT0001"

                    created_at = datetime.now().strftime(
                        "%Y-%m-%dT%H:%M:%S"
                    )

                    conn.execute(
                        """
                        INSERT INTO support_tickets (
                            ticket_id,
                            customer_id,
                            created_at,
                            category,
                            priority,
                            status,
                            channel,
                            subject,
                            first_response_at,
                            resolved_at,
                            satisfaction_score
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            ticket_id,
                            new_customer_id,
                            created_at,
                            new_category,
                            new_priority,
                            new_status,
                            new_channel,
                            new_subject.strip(),
                            None,
                            None,
                            None
                        )
                    )

                    conn.commit()

                    st.success(
                        f"Ticket {ticket_id} created successfully!"
                    )

                    st.rerun()

                except Exception as e:
                    conn.rollback()
                    st.error(f"Failed to create ticket: {e}")

    # =========================================================
    # Update Ticket
    # =========================================================
    st.subheader("Update Ticket")

    if tickets:

        ticket_ids = [t[0] for t in tickets]

        selected_ticket = st.selectbox(
            "Select ticket to update",
            ticket_ids
        )

        if selected_ticket:

            ticket = next(
                t for t in tickets
                if t[0] == selected_ticket
            )

            with st.form(key="update_ticket_form"):

                col1, col2 = st.columns(2)

                with col1:

                    current_status = (
                        ticket[5]
                        if ticket[5] in [
                            "open",
                            "in_progress",
                            "resolved",
                            "closed"
                        ]
                        else "open"
                    )

                    new_status = st.selectbox(
                        "Status",
                        ["open", "in_progress", "resolved", "closed"],
                        index=[
                            "open",
                            "in_progress",
                            "resolved",
                            "closed"
                        ].index(current_status)
                    )

                    current_priority = (
                        ticket[4]
                        if ticket[4] in [
                            "low",
                            "medium",
                            "high",
                            "urgent"
                        ]
                        else "medium"
                    )

                    new_priority = st.selectbox(
                        "Priority",
                        ["low", "medium", "high", "urgent"],
                        index=[
                            "low",
                            "medium",
                            "high",
                            "urgent"
                        ].index(current_priority)
                    )

                with col2:

                    # First response date
                    if ticket[8]:
                        first_response_default = pd.to_datetime(
                            ticket[8]
                        ).date()
                    else:
                        first_response_default = date.today()

                    new_first_response = st.date_input(
                        "First Response Date",
                        value=first_response_default
                    )

                    # Resolved date
                    if ticket[9]:
                        resolved_default = pd.to_datetime(
                            ticket[9]
                        ).date()
                    else:
                        resolved_default = date.today()

                    new_resolved = st.date_input(
                        "Resolved Date",
                        value=resolved_default
                    )

                    # Satisfaction score
                    current_satisfaction = ticket[10]

                    new_satisfaction = st.number_input(
                        "Satisfaction Score (1-5)",
                        min_value=1,
                        max_value=5,
                        value=(
                            int(current_satisfaction)
                            if current_satisfaction is not None
                            else 5
                        ),
                        step=1
                    )

                    satisfaction_enabled = st.checkbox(
                        "Save satisfaction score",
                        value=current_satisfaction is not None
                    )

                update_btn = st.form_submit_button(
                    "Update Ticket"
                )

                if update_btn:

                    try:

                        # If ticket is not resolved, clear resolved date
                        if new_status not in ["resolved", "closed"]:
                            resolved_at_val = None
                        else:
                            resolved_at_val = (
                                new_resolved.strftime(
                                    "%Y-%m-%dT%H:%M:%S"
                                )
                                if new_resolved
                                else None
                            )

                        first_response_val = (
                            new_first_response.strftime(
                                "%Y-%m-%dT%H:%M:%S"
                            )
                            if new_first_response
                            else None
                        )

                        satisfaction_val = (
                            new_satisfaction
                            if satisfaction_enabled
                            else None
                        )

                        conn.execute(
                            """
                            UPDATE support_tickets
                            SET
                                status = ?,
                                priority = ?,
                                first_response_at = ?,
                                resolved_at = ?,
                                satisfaction_score = ?
                            WHERE ticket_id = ?
                            """,
                            (
                                new_status,
                                new_priority,
                                first_response_val,
                                resolved_at_val,
                                satisfaction_val,
                                selected_ticket
                            )
                        )

                        conn.commit()

                        st.success(
                            f"Ticket {selected_ticket} updated successfully!"
                        )

                        st.rerun()

                    except Exception as e:
                        conn.rollback()
                        st.error(f"Failed to update ticket: {e}")

    else:
        st.info("No tickets available for updating.")

finally:
    conn.close()
