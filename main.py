import streamlit as st
from components.dashboard import show_dashboard
from components.map_view import show_map_view
from styles.custom_css import apply_custom_css
import config

def main():
    # Page configuration
    st.set_page_config(
        page_title=config.PAGE_TITLE,
        page_icon=config.PAGE_ICON,
        layout=config.LAYOUT
    )
    
    # Apply custom CSS
    apply_custom_css()
    
    # Initialize session state
    if 'show_tips' not in st.session_state:
        st.session_state.show_tips = True
    if 'show_welcome' not in st.session_state:
        st.session_state.show_welcome = False
    if 'show_map_welcome' not in st.session_state:
        st.session_state.show_map_welcome = False
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Select Page", ["Dashboard", "Map View"], key="nav_radio")
    
    # Show tips toggle in sidebar
    tips_enabled = st.sidebar.checkbox("Show Helper Tips", value=st.session_state.show_tips, key="tips_toggle")
    if tips_enabled != st.session_state.show_tips:
        st.session_state.show_tips = tips_enabled
    
    # Show tutorial button
    if st.sidebar.button("Show Welcome Tutorial", key="show_welcome_modal"):
        from components.modals import show_welcome_modal_js
        show_welcome_modal_js()
    
    # Display the selected page
    if page == "Dashboard":
        show_dashboard()
    elif page == "Map View":
        show_map_view()
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("Streamlit AWS Timestream Fridge Monitoring Dashboard")
    
    # Add help section to sidebar
    with st.sidebar.expander("❓ Need Help?"):
        st.markdown(config.HELP_TEXT)
    
    # Add keyboard shortcuts helper
    with st.sidebar.expander("⌨️ Keyboard Shortcuts"):
        st.markdown(config.KEYBOARD_SHORTCUTS)
    
    # Add timestamp for last refresh
    from datetime import datetime
    st.sidebar.caption(f"Last refreshed: {datetime.now().strftime('%m/%d/%Y, %I:%M:%S %p')}")
    
    # First-time user tutorial modal button
    tutorial_trigger = st.sidebar.button("Show Tutorial", key="tutorial_button")
    if tutorial_trigger:
        from components.modals import show_tutorial_js
        show_tutorial_js()

if __name__ == "__main__":
    main()