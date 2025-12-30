# components/login.py
import streamlit as st

def require_admin():
    if st.session_state.get("is_admin"):
        return

    st.subheader("Admin Access")

    with st.form("admin_login", clear_on_submit=True):
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")

    if submitted:
        expected = st.secrets.get("ADMIN_PASSWORD")
        if not expected:
            st.error("ADMIN_PASSWORD is not set in Streamlit Secrets.")
            st.stop()

        if password == expected:
            st.session_state.is_admin = True
            st.rerun()
        else:
            st.error("Incorrect password.")

    st.stop()

