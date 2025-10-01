import streamlit as st

users = {
    "risk_user": {"password": "risk123", "role": "Risk"},
    "ias19_user": {"password": "ias19123", "role": "IAS19"},
    "admin": {"password": "admin123", "role": "Admin"}
}

st.set_page_config(page_title="Login", layout="centered")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.role = None

st.title("Login")

username = st.text_input("Username")
password = st.text_input("Password", type="password")

if st.button("Login"):
    if username in users and users[username]["password"] == password:
        st.session_state.authenticated = True
        st.session_state.role = users[username]["role"]
        st.success(f"Welcome {username}, role: {st.session_state.role}")
        st.switch_page("main.py")  
    else:
        st.error("Invalid credentials")
