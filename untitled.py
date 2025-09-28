import streamlit as st
import mysql.connector

st.title("Add New Company")

company_name = st.text_input("Company Name")
company_full_name = st.text_input("Full Name")
sector = st.text_input("Sector")
is_client = st.checkbox("Is Client?")

if st.button("Save"):
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="1234",
        database="company_projects"
    )
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM companies WHERE company_name = %s", (company_name,))
    (count,) = cursor.fetchone()

    if count > 0:
        st.error("⚠️ This company already exists!")
    else:
        cursor.execute(
            "INSERT INTO companies (company_name, company_full_name, sector, is_client) VALUES (%s, %s, %s, %s)",
            (company_name, company_full_name, sector, is_client)
        )
        conn.commit()
        st.success("✅ Company added successfully!")

    conn.close()
