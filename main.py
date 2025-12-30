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

    # 2) Gate the app (no AWS creds involved)
    from components.login import require_admin
    require_admin()

    # 3) Only now import modules that may call st.* at import time
    from components.dashboard import show_dashboard
    from components.map_view  import show_map_view
    from styles.custom_css    import apply_custom_css

    apply_custom_css()

    # 4) Configure AWS session SERVER-SIDE via Streamlit Secrets
    import boto3
    aws_region = st.secrets.get("AWS_REGION", "us-east-1")

    session = boto3.Session(
        aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"],
        region_name=aws_region
    )

    from utils.aws import set_aws_session
    set_aws_session(session)

    # 5) Initialize session state (UI only)
    if 'show_tips' not in st.session_state:
        st.session_state.show_tips = True
    if 'show_welcome' not in st.session_state:
        st.session_state.show_welcome = False
    if 'show_map_welcome' not in st.session_state:
        st.session_state.show_map_welcome = False

    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Select Page", ["Dashboard", "Map View"], key="nav_radio")

    # Display selected page
    if page == "Dashboard":
        show_dashboard()
    elif page == "Map View":
        show_map_view()

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("Streamlit AWS Timestream Fridge Monitoring Dashboard")

    # Help section (remove emoji if you want)
    with st.sidebar.expander("Need Help?"):
        st.markdown(config.HELP_TEXT)

    # Last refresh timestamp
    from datetime import datetime
    st.sidebar.caption(f"Last refreshed: {datetime.now().strftime('%m/%d/%Y, %I:%M:%S %p')}")

if __name__ == "__main__":
    main()
