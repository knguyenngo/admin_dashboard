# main.py
import streamlit as st
import config

def main():
    # 1) Must be first Streamlit call
    st.set_page_config(
        page_title=config.PAGE_TITLE,
        page_icon=config.PAGE_ICON,
        layout=config.LAYOUT
    )

    # 2) Load deployment config from Streamlit Secrets (server-side)
    #    (Keep secrets out of config.py to avoid import-time crashes.)
    config.AWS_REGION = st.secrets.get("AWS_REGION", getattr(config, "AWS_REGION_DEFAULT", "us-east-1"))
    config.DATABASE_NAME = st.secrets.get(
        "TIMESTREAM_DATABASE",
        getattr(config, "DATABASE_NAME_DEFAULT", "RVACF-Timestream-DB")
    )
    config.TABLE_NAME = st.secrets.get(
        "TIMESTREAM_TABLE",
        getattr(config, "TABLE_NAME_DEFAULT", "multi_value")
    )

    # 3) Gate the app (no AWS creds involved)
    from components.login import require_admin
    require_admin()

    # 4) Only now import modules that may call st.* at import-time
    from components.dashboard import show_dashboard
    from components.map_view import show_map_view
    from styles.custom_css import apply_custom_css

    apply_custom_css()

    # 5) Configure AWS session SERVER-SIDE via Streamlit Secrets
    import boto3
    session = boto3.Session(
        aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"],
        region_name=config.AWS_REGION
    )

    from utils.aws import set_aws_session
    set_aws_session(session)

    # 6) Initialize session state (UI only)
    st.session_state.setdefault("show_tips", True)
    st.session_state.setdefault("show_welcome", False)
    st.session_state.setdefault("show_map_welcome", False)

    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Select Page", ["Dashboard", "Map View"], key="nav_radio")

    # Display selected page
    if page == "Dashboard":
        show_dashboard()
    else:
        show_map_view()

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("Streamlit AWS Timestream Fridge Monitoring Dashboard")

    with st.sidebar.expander("Need Help?"):
        st.markdown(config.HELP_TEXT)

    from datetime import datetime
    st.sidebar.caption(f"Last refreshed: {datetime.now().strftime('%m/%d/%Y, %I:%M:%S %p')}")

if __name__ == "__main__":
    main()

