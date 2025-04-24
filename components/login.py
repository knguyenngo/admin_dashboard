# components/login.py
import streamlit as st

def show_aws_login():
    st.title("🔑 AWS Login")
    with st.form("aws_login", clear_on_submit=False):
        access_key = st.text_input("AWS Access Key ID", type="default")
        secret_key = st.text_input("AWS Secret Access Key", type="password")
        region     = st.text_input("AWS Region", value="us-east-1")
        submitted = st.form_submit_button("Log in")
    if submitted:
        if not access_key or not secret_key:
            st.error("Both key and secret are required.")
        else:
            st.session_state.aws_access_key = access_key
            st.session_state.aws_secret_key = secret_key
            st.session_state.aws_region     = region
            st.rerun()
    # don’t render anything else if not logged in
    st.stop()
