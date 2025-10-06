import streamlit as st
import mysql.connector
import pandas as pd
import io
from datetime import date
import os
from dotenv import load_dotenv

if os.path.exists("env.txt"):
    load_dotenv("env.txt")

def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", st.secrets.get("DB_HOST")),
        port=int(os.getenv("DB_PORT", st.secrets.get("DB_PORT", "3306"))),
        user=os.getenv("DB_USER", st.secrets.get("DB_USER")),
        password=os.getenv("DB_PASS", st.secrets.get("DB_PASS")),
        database=os.getenv("DB_NAME", st.secrets.get("DB_NAME")),
        unix_socket=None
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
st.title("Company & Project Management")

menu = st.sidebar.radio(
    "Navigation",
    ["Register Company", "Add Project", "Update Project", "Review Projects"]
)

# ----------------------------
# Register Company
# ----------------------------
if menu == "Register Company":
    st.subheader("Register New Company")

    company_id = st.text_input("Company ID")
    company_name = st.text_input("Company Name")
    full_name = st.text_input("Full Name")

    company_responsible = st.text_input("Company Responsible (Client Contact Person)")
    project_responsible = st.text_input("Project Responsible (Internal / Team Lead)")

    if st.button("Save Company"):
        
        if not company_id or not company_name or not full_name:
            st.error("Company ID, Company Name, and Full Name are required!")
         

        elif not company_id.isdigit():
            st.error("Company ID must contain only digits (0–9).")

        elif len(company_id) != 9:
            st.error("Company ID must be exactly 9 digits long.")
        else:
            rows = fetch_query("SELECT COUNT(*) FROM companies WHERE company_id = %s", (company_id,))
            if rows and rows[0][0] > 0:
                st.error(f"Company ID '{company_id}' already exists!")
            else:
                query = """
                    INSERT INTO companies (
                        company_id, company_name, full_name,
                        company_responsible, project_responsible
                    )
                    VALUES (%s, %s, %s, %s, %s)
                """
                execute_query(query, (company_id, company_name, full_name,
                                      company_responsible, project_responsible))
                st.success(f"Company '{company_name}' registered successfully!")

elif menu == "Add Project":
    st.subheader("Add Project for a Company")

    companies = fetch_query("SELECT company_id, company_name FROM companies ORDER BY company_name")
    if companies:
        company_choice = st.selectbox("Select Company", [f"{c[1]} (ID: {c[0]})" for c in companies])
        company_id = [c[0] for c in companies if f"{c[1]} (ID: {c[0]})" == company_choice][0]

        project_type = st.selectbox("Project Type", ["IAS19", "Risk", "ESG", "Reserving", "Other"])

        # ---- Multi-select Project Responsible ----
        st.markdown("#### Select Project Responsible(s)")
        responsible_options = ["Nefeli", "Aggelos", "Katerina", "Vasilis"]
        project_responsible_list = st.multiselect("Choose one or more persons", responsible_options)
        project_responsible = ", ".join(project_responsible_list) if project_responsible_list else None

        start_date = st.date_input("Date Form Sent (Project Start)", value=date.today())
        end_date = st.date_input("Project Deadline (Final Report Due Date)", value=date.today())
        expected_data_date = st.date_input("Expected Client Data Delivery Date", value=date.today())
        actual_data_date = st.date_input("Actual Client Data Received Date (if available)", value=None)

        if actual_data_date:
            st.markdown("### Data Review and Reporting Phase")
            dc_date = st.date_input("DC Date (Data Check)", value=date.today())
            sito_date = st.date_input("SI/TO Date", value=date.today())
            disclosures = st.text_area("Disclosures / Comments")
            report_date = st.date_input("Report Date", value=date.today())
        else:
            dc_date = sito_date = report_date = None
            disclosures = None

        if st.button("Save Project"):
            # ---- Prevent duplicates for same company & project type ----
            rows = fetch_query(
                "SELECT COUNT(*) FROM projects1 WHERE company_id = %s AND project_type = %s",
                (company_id, project_type)
            )
            if rows and rows[0][0] > 0:
                st.error(f"A project of type '{project_type}' already exists for this company!")
            else:
                query = """
                    INSERT INTO projects1 (
                        company_id, project_type, project_responsible,
                        start_date, end_date,
                        expected_data_date, actual_data_date,
                        dc_date, sito_date, disclosures, report_date
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                params = (
                    company_id, project_type, project_responsible,
                    start_date, end_date,
                    expected_data_date, actual_data_date,
                    dc_date, sito_date, disclosures, report_date
                )
                execute_query(query, params)
                st.success(f"Added project '{project_type}' for company ID {company_id}")
    else:
        st.info("No companies registered yet.")

elif menu == "Review Projects":
    st.subheader("Review All Companies and Projects")

    base_query = """
        SELECT 
            c.company_id, c.company_name, c.full_name,
            c.company_responsible, c.project_responsible,
            p.project_type, p.start_date, p.end_date,
            p.expected_data_date, p.actual_data_date,
            p.dc_date, p.sito_date, p.disclosures, p.report_date
        FROM companies c
        LEFT JOIN projects1 p ON c.company_id = p.company_id
        ORDER BY c.company_name, p.project_type
    """
    rows = fetch_query(base_query)
    if rows:
        df = pd.DataFrame(rows, columns=[
            "Company ID", "Company Name", "Full Name",
            "Company Responsible", "Project Responsible",
            "Project Type", "Start Date", "End Date",
            "Expected Data Date", "Actual Data Date",
            "DC Date", "SI/TO Date", "Disclosures", "Report Date"
        ])
        st.dataframe(df, use_container_width=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Review")

        st.download_button(
            label="Download Excel",
            data=output.getvalue(),
            file_name="companies_projects.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("No data found.")

