import streamlit as st
import mysql.connector
import pandas as pd
import io
from datetime import date
import os
from dotenv import load_dotenv

# Ensure login happened
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.error("You must login first!")
    st.stop()

role = st.session_state.role

# 🔹 DB connection (same as before)
if os.path.exists("env.txt"):
    load_dotenv("env.txt")

def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", st.secrets.get("DB_HOST")),
        port=int(os.getenv("DB_PORT", st.secrets.get("DB_PORT", "3306"))),
        user=os.getenv("DB_USER", st.secrets.get("DB_USER")),
        password=os.getenv("DB_PASS", st.secrets.get("DB_PASS")),
        database=os.getenv("DB_NAME", st.secrets.get("DB_NAME")),
    )

def execute_query(query, params=()):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def fetch_query(query, params=()):
    conn = get_connection()
    rows = []
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
    return rows

st.set_page_config(page_title="Company & Project Management", layout="wide")
st.title(f"Company & Project Management — {role}")

menu = st.sidebar.radio("Navigation", ["Register Company", "Add Project", "Update Project", "Review Projects"])

# ----------------------------
# Register Company (Admin only)
# ----------------------------
if menu == "Register Company":
    if role != "Admin":
        st.error("Only Admin can register companies.")
        st.stop()

    company_id = st.text_input("Company ID (must be unique)")
    company_name = st.text_input("Company Name")
    full_name = st.text_input("Full Name")

    if st.button("Save Company"):
        if not company_id or not company_name or not full_name:
            st.error("Company ID, Company Name, and Full Name are required!")
        else:
            rows = fetch_query("SELECT COUNT(*) FROM companies WHERE company_id = %s", (company_id,))
            if rows and rows[0][0] > 0:
                st.error(f"Company ID '{company_id}' already exists!")
            else:
                query = "INSERT INTO companies (company_id, company_name, full_name) VALUES (%s, %s, %s)"
                execute_query(query, (company_id, company_name, full_name))
                st.success(f"Company '{company_name}' registered successfully!")

# ----------------------------
# Add Project
# ----------------------------
elif menu == "Add Project":
    companies = fetch_query("SELECT company_id, company_name FROM companies ORDER BY company_name")
    if companies:
        company_choice = st.selectbox("Select Company", [f"{c[1]} (ID: {c[0]})" for c in companies])
        company_id = [c[0] for c in companies if f"{c[1]} (ID: {c[0]})" == company_choice][0]

        allowed_types = ["IAS19", "Risk", "ESG", "Reserving", "Other"]
        if role != "Admin":
            allowed_types = [role]  # non-admins restricted to their project type

        project_type = st.selectbox("Project Type", allowed_types)
        start_date = st.date_input("Start Date", value=date.today())
        invoice_amount = st.number_input("Invoice Amount", min_value=0.0, step=100.0)
        is_paid = st.checkbox("Paid?")
        project_responsible = st.text_input("Project Responsible")

        if st.button("Save Project"):
            rows = fetch_query(
                "SELECT COUNT(*) FROM projects1 WHERE company_id = %s AND project_type = %s",
                (company_id, project_type)
            )
            if rows and rows[0][0] > 0:
                st.error(f"Project '{project_type}' already exists for this company!")
            else:
                query = """
                    INSERT INTO projects1 (
                        company_id, project_type, start_date, invoice_amount, is_paid, project_responsible
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """
                params = (company_id, project_type, start_date, invoice_amount, is_paid, project_responsible)
                execute_query(query, params)
                st.success(f"Added project '{project_type}' for company ID {company_id}")
    else:
        st.info("No companies registered yet.")

# ----------------------------
# Update Project
# ----------------------------
elif menu == "Update Project":
    projects = fetch_query("""
        SELECT p.project_id, c.company_name, p.project_type
        FROM projects1 p
        JOIN companies c ON p.company_id = c.company_id
        ORDER BY c.company_name, p.project_type
    """)
    if projects:
        project_choice = st.selectbox("Select Project", [f"{p[1]} - {p[2]}" for p in projects])
        project_id = [p[0] for p in projects if f"{p[1]} - {p[2]}" == project_choice][0]

        row = fetch_query("""
            SELECT start_date, invoice_amount, is_paid, project_responsible, project_type
            FROM projects1 WHERE project_id = %s
        """, (project_id,))[0]

        if role != "Admin" and row[4] != role:
            st.error("You cannot update projects outside your role!")
            st.stop()

        with st.form("update_form"):
            start_date = st.date_input("Start Date", value=row[0] or date.today())
            invoice_amount = st.number_input("Invoice Amount", min_value=0.0, step=100.0, value=row[1] or 0.0)
            is_paid = st.checkbox("Paid?", value=bool(row[2]))
            project_responsible = st.text_input("Project Responsible", value=row[3] or "")
            submitted = st.form_submit_button("Update Project")
            if submitted:
                query = """
                    UPDATE projects1
                    SET start_date=%s, invoice_amount=%s, is_paid=%s, project_responsible=%s
                    WHERE project_id=%s
                """
                params = (start_date, invoice_amount, is_paid, project_responsible, project_id)
                execute_query(query, params)
                st.success("Project updated successfully!")
    else:
        st.info("No projects available to update.")

# ----------------------------
# Review Projects
# ----------------------------
elif menu == "Review Projects":
    query = """
        SELECT c.company_id, c.company_name, c.full_name,
               p.project_type, p.start_date, p.invoice_amount, p.is_paid, p.project_responsible
        FROM companies c
        LEFT JOIN projects1 p ON c.company_id = p.company_id
    """
    rows = fetch_query(query)

    if role != "Admin":
        rows = [r for r in rows if r[3] == role]

    if rows:
        df = pd.DataFrame(rows, columns=[
            "Company ID", "Company Name", "Full Name",
            "Project Type", "Start Date", "Invoice Amount", "Paid", "Project Responsible"
        ])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No data available for your role.")


