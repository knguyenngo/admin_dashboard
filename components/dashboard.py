import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from datetime import datetime, timedelta
import plotly.express as px

import config
from utils.aws import get_latest_data_for_fridge, get_historical_data_for_fridge
from utils.data import determine_fridge_status, get_all_fridge_coordinates
from utils.helpers import safe_plotly_chart
from components.tooltips import create_dashboard_guides

def show_dashboard():
    # ─── Sidebar ─────────────────────────────────────────────
    fridge_selection = st.sidebar.selectbox(
        "Select Fridge",
        options=list(config.FRIDGE_OPTIONS.keys()),
        format_func=lambda x: f"{x}: {config.FRIDGE_OPTIONS[x]}",
        key="dashboard_fridge_select"
    )
    fridge_id = config.FRIDGE_OPTIONS[fridge_selection]
    st.sidebar.info(f"Fridge ID: {fridge_id}")

    time_range = st.sidebar.selectbox(
        "Select Time Range",
        ["Last Hour", "Last 24 Hours", "Last 7 Days"],
        key="dashboard_time_range"
    )

    # Auto-refresh toggle
    if "auto_refresh_enabled" not in st.session_state:
        st.session_state.auto_refresh_enabled = False

    if st.sidebar.button(
        "Stop Auto-Refresh" if st.session_state.auto_refresh_enabled else "Start Auto-Refresh",
        key="refresh_toggle"
    ):
        st.session_state.auto_refresh_enabled = not st.session_state.auto_refresh_enabled
        st.rerun()

    # ─── Title & Guide ───────────────────────────────────────
    st.title("Fridge Monitoring Dashboard")
    if st.session_state.get("show_tips", False):
        create_dashboard_guides()

    # ─── Static Mini-Map ─────────────────────────────────────
    coords = get_all_fridge_coordinates()
    if fridge_id in coords:
        lat, lon = coords[fridge_id]
        map_box = folium.Map(location=[lat, lon], zoom_start=15)
        folium.Marker(
            [lat, lon],
            popup=f"{fridge_id}",
            tooltip=fridge_id,
            icon=folium.Icon(color="blue", icon="snowflake", prefix="fa")
        ).add_to(map_box)
        folium_static(map_box, width=700, height=300)

    # ─── Placeholders ────────────────────────────────────────
    status_slot = st.empty()
    history_slot = st.empty()
    footer_slot = st.empty()

    def get_start_dt(now: datetime) -> datetime:
        if time_range == "Last Hour":
            return now - timedelta(hours=1)
        if time_range == "Last 24 Hours":
            return now - timedelta(days=1)
        return now - timedelta(days=7)

    def update_content():
        now = datetime.now()
        start_dt = get_start_dt(now)

        # Status block
        with status_slot.container():
            latest = get_latest_data_for_fridge(fridge_id)
            if not latest:
                st.warning("No recent data.")
            else:
                temp_val = float(latest.get("temp")) if latest.get("temp") else None
                door_val = latest.get("door_usage", "N/A")
                updated  = latest.get("est_time", "N/A")

                status_text, color = (
                    determine_fridge_status(temp_val)
                    if temp_val is not None else ("Unknown", "gray")
                )

                col_t, col_d, col_s = st.columns([1, 1, 1])
                col_t.metric("Temperature", f"{temp_val:.1f}°F" if temp_val is not None else "N/A")
                col_d.metric("Door Usage (24h)", door_val)

                col_s.markdown(
                    f"""
                    <div style="
                      background:{color};
                      padding:8px;
                      border-radius:6px;
                      color:white;
                      text-align:center;
                      font-weight:600;
                    ">{status_text}</div>
                    """,
                    unsafe_allow_html=True
                )
                st.caption(f"Last updated: {updated}")

        # History block
        with history_slot.container():
            st.subheader("Historical Data")
            hist = get_historical_data_for_fridge(fridge_id, start_dt, now)
            if hist.empty:
                st.info("No history in this range.")
                return

            hist["temp"] = pd.to_numeric(hist["temp"], errors="coerce")
            hist["door_usage"] = pd.to_numeric(hist["door_usage"], errors="coerce")

            # IMPORTANT: apply the sort
            hist = hist.sort_values("est_time_dt")

            tabs = st.tabs(["Temp", "Doors", "Stats"])
            with tabs[0]:
                fig = px.line(hist, x="est_time_dt", y="temp", title="Temperature")
                safe_plotly_chart(fig, prefix="hist_temp")
            with tabs[1]:
                fig = px.scatter(hist, x="est_time_dt", y="door_usage", title="Door Usage")
                safe_plotly_chart(fig, prefix="hist_door")
            with tabs[2]:
                t = hist["temp"].dropna()
                d = hist["door_usage"].dropna()
                a, b, c = st.columns(3)
                a.metric("Avg Temp", f"{t.mean():.1f}°F" if not t.empty else "N/A")
                b.metric("Max Temp", f"{t.max():.1f}°F" if not t.empty else "N/A")
                c.metric("Min Temp", f"{t.min():.1f}°F" if not t.empty else "N/A")

                x, y, z = st.columns(3)
                x.metric("Total Door Interaction", int(d.sum()) if not d.empty else 0)
                y.metric("Max Door Interaction", int(d.max()) if not d.empty else 0)
                z.metric("Avg Door Interaction", f"{d.mean():.1f}" if not d.empty else "N/A")

    # Initial draw
    update_content()

    # Streamlit-native refresh (no while loop)
    if st.session_state.auto_refresh_enabled:
        st.autorefresh(interval=int(config.REFRESH_RATE * 1000), key="dashboard_autorefresh")
        footer_slot.caption(f"Auto-refresh enabled (every {config.REFRESH_RATE}s).")
    else:
        footer_slot.caption("Auto-refresh is disabled. Click 'Start Auto-Refresh' in the sidebar to enable.")

