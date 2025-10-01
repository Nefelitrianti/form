import streamlit as st
import mysql.connector
import pandas as pd
import io
from datetime import date
import os
from dotenv import load_dotenv

if os.path.exists("env.txt"):
    load_dotenv("env.txt")

def get_local_connection():
    try:
        return mysql.connector.connect(
            host=os.getenv("LOCAL_HOST"),
            port=int(os.getenv("LOCAL_PORT")),
            user=os.getenv("LOCAL_USER"),
            password=os.getenv("LOCAL_PASS"),
            database=os.getenv("LOCAL_DB"),
            unix_socket=None
        )
    except:
        return None

def get_railway_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", st.secrets.get("DB_HOST")),
        port=int(os.getenv("DB_PORT", st.secrets.get("DB_PORT", "3306"))),
        user=os.getenv("DB_USER", st.secrets.get("DB_USER")),
        password=os.getenv("DB_PASS", st.secrets.get("DB_PASS")),
        database=os.getenv("DB_NAME", st.secrets.get("DB_NAME")),
        unix_socket=None
    )

def dual_execute(query, params=()):
    for conn_func in [get_local_connection, get_railway_connection]:
        conn = conn_func()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
            except:
                pass
            finally:
                cursor.close()
                conn.close()

def dual_fetch(query):
    rows = []
    for conn_func in [get_local_connection, get_railway_connection]:
        conn = conn_func()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute(query)
                rows.extend(cursor.fetchall())
            except:
                pass
            finally:
                cursor.close()
                conn.close()
    return rows

st.set_page_config(page_title="Company & Project Management", layout="wide")
st.title("Company & Project Management")

menu = st.sidebar.radio("Navigation", ["Register Company", "Update Company", "Add Project", "Review Projects"])

if menu == "Register Company":
    st.subheader("Register New Company")

    company_name = st.text_input("Company Name")
    full_name = st.text_input("Full Name")
    company_responsible = st.text_input("Company Responsible")

    st.markdown("### Sector")
   sector_finance = st.checkbox("Finance", key="sector_finance")
    sector_health = st.checkbox("Health", key="sector_health")
    sector_pension = st.checkbox("Pension", key="sector_pension")
    sector_other = st.checkbox("Other", key="sector_other")
st.markdown("### Project Type")
project_IAS19 = st.checkbox("IAS19", key="project_IAS19")
project_Risk = st.checkbox("Risk", key="project_Risk")
project_ESG = st.checkbox("ESG", key="project_ESG")
project_Reserving = st.checkbox("Reserving", key="project_Reserving")
project_Other = st.checkbox("Other", key="project_other")


    if st.button("Save Company"):
        query = """
            INSERT INTO companies (
                company_name, full_name, company_responsible,
                sector_finance, sector_health, sector_pension, sector_other,
                project_IAS19, project_Risk, project_ESG, project_Reserving, project_Other
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            company_name, full_name, company_responsible,
            sector_finance, sector_health, sector_pension, sector_other,
            project_IAS19, project_Risk, project_ESG, project_Reserving, project_Other
        )
        dual_execute(query, params)
        st.success(f"Company '{company_name}' saved")

elif menu == "Update Company":
    st.subheader("Update Existing Company")
    try:
        conn = get_railway_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT company_id, company_name FROM companies ORDER BY company_name")
        companies = cursor.fetchall()
        if companies:
            company_choice = st.selectbox("Select Company", [c[1] for c in companies])
            company_id = [c[0] for c in companies if c[1] == company_choice][0]
            cursor.execute("SELECT full_name, sector, company_responsible, project_responsible FROM companies WHERE company_id = %s", (company_id,))
            row = cursor.fetchone()
            with st.form("update_form"):
                new_full_name = st.text_input("Full Name", value=row[0] or "")
                new_sector = st.text_input("Sector", value=row[1] or "")
                new_company_responsible = st.text_input("Company Responsible", value=row[2] or "")
                new_company_project_responsible = st.text_input("Company Project Responsible", value=row[3] or "")
                submitted = st.form_submit_button("Update")
                if submitted:
                    query = """
                        UPDATE companies
                        SET full_name=%s, sector=%s, company_responsible=%s, project_responsible=%s
                        WHERE company_id=%s
                    """
                    params = (new_full_name, new_sector, new_company_responsible, new_company_project_responsible, company_id)
                    dual_execute(query, params)
                    st.success(f"Company '{company_choice}' updated")
        else:
            st.info("No companies registered yet.")
    except mysql.connector.Error as e:
        st.error(f"Database error: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

elif menu == "Add Project":
    st.subheader("Add Project for a Company")
    try:
        conn = get_railway_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT company_id, company_name FROM companies ORDER BY company_name")
        companies = cursor.fetchall()
        if companies:
            company_choice = st.selectbox("Select Company", [c[1] for c in companies])
            company_id = [c[0] for c in companies if c[1] == company_choice][0]
            with st.form("project_form"):
                set_start = st.checkbox("Set Start Date")
                start_date = st.date_input("Start Date", value=date.today()) if set_start else None
                set_received = st.checkbox("Set Data Received Date")
                data_received = st.date_input("Data Received", value=date.today()) if set_received else None
                set_review = st.checkbox("Set Data Review Date")
                data_review = st.date_input("Data Review", value=date.today()) if set_review else None
                set_report = st.checkbox("Set Report Date")
                report_date = st.date_input("Report Date", value=date.today()) if set_report else None
                invoice_amount = st.number_input("Invoice Amount", min_value=0.0, step=100.0, value=0.0)
                is_paid = st.checkbox("Paid?")
                project_responsible = st.text_input("Project Responsible")
                submitted = st.form_submit_button("Save Project")
                if submitted:
                    cursor.execute("SELECT COUNT(*) FROM projects1 WHERE company_id = %s", (company_id,))
                    (count,) = cursor.fetchone()
                    if count > 0:
                        query = """
                            UPDATE projects1 
                            SET start_date=%s, data_received=%s, data_review=%s, report_date=%s,
                                invoice_amount=%s, is_paid=%s, project_responsible=%s
                            WHERE company_id=%s
                        """
                        params = (start_date, data_received, data_review, report_date,
                                  invoice_amount, is_paid, project_responsible, company_id)
                        dual_execute(query, params)
                        st.success(f"Project for company '{company_choice}' updated")
                    else:
                        query = """
                            INSERT INTO projects1 (company_id, start_date, data_received, data_review, report_date, invoice_amount, is_paid, project_responsible)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        params = (company_id, start_date, data_received, data_review, report_date,
                                  invoice_amount, is_paid, project_responsible)
                        dual_execute(query, params)
                        st.success(f"Project added for company '{company_choice}'")
                    conn.commit()
        else:
            st.info("No companies registered yet.")
    except mysql.connector.Error as e:
        st.error(f"Database error: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

elif menu == "Review Projects":
    st.subheader("Review All Companies and Projects")
    try:
        base_query = """
            SELECT c.company_name, c.full_name, c.sector, c.company_responsible, c.project_responsible,
                   p.start_date, p.data_received, p.data_review, p.report_date,
                   p.invoice_amount, p.is_paid, p.project_responsible
            FROM companies c
            LEFT JOIN projects1 p ON c.company_id = p.company_id
            ORDER BY c.company_name, p.start_date DESC
        """
        rows = dual_fetch(base_query)
        if rows:
            df = pd.DataFrame(rows, columns=[
                "Company Name", "Full Name", "Sector", "Company Responsible", "Company Project Responsible",
                "Start Date", "Data Received", "Data Review", "Report Date",
                "Invoice Amount", "Paid", "Project Responsible"
            ])
            st.dataframe(df, use_container_width=True)
            df_excel = df.drop(columns=["Invoice Amount", "Paid"])
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df_excel.to_excel(writer, index=False, sheet_name="Review")
            st.download_button(
                label="Download Excel (without invoice & paid)",
                data=output.getvalue(),
                file_name="companies_projects.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("No data found.")
    except mysql.connector.Error as e:
        st.error(f"Database error: {e}")


