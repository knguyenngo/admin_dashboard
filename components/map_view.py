# components/map_view.py

import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import folium_static
import plotly.express as px
import time
from datetime import datetime

from utils.aws import get_latest_data_for_all_fridges
from utils.data import get_all_fridge_coordinates, get_fridge_locations, determine_fridge_status
from utils.helpers import safe_plotly_chart
from styles.custom_css import apply_custom_css, color_status_style, get_status_color_map

import config

def show_map_view():
    # ─── 1) one-time setup ────────────────────────────────────
    apply_custom_css()
    st.title("Community Fridge Locations")
    st.empty()
    st.sidebar.empty()
    # filter widget created once
    ALL_STATUSES = ["Operating normally", "Too cold", "Too warm", "No data"]
    status_filter = st.multiselect(
        "Filter by Status",
        options=ALL_STATUSES,
        default=ALL_STATUSES,
        key="map_status_filter"
    )

    # build the base map once
    coords     = get_all_fridge_coordinates()
    latest_all = get_latest_data_for_all_fridges()
    base_map   = folium.Map(location=[37.5407, -77.4360], zoom_start=12)
    cluster    = MarkerCluster().add_to(base_map)

    for fid, addr in get_fridge_locations().items():
        if fid not in coords:
            continue
        lat, lon = coords[fid]
        data = latest_all.get(fid, {})
        temp = data.get("temp")
        status, color = (
            determine_fridge_status(float(temp)) if temp is not None
            else ("No data", "gray")
        )
        folium.Marker(
            [lat, lon],
            popup=(
                f"<b>{fid}</b><br>{addr}"
                f"<br><b>Status:</b> {status}"
                f"<br><b>Temp:</b> {temp if temp is not None else 'N/A'}°C"
            ),
            icon=folium.Icon(color=color, icon="snowflake", prefix="fa")
        ).add_to(cluster)

    st.subheader("Interactive Map")
    folium_static(base_map, width=800, height=400)

    # ─── 2) placeholder for auto-refreshing content ───────────
    refresh = st.empty()

    while True:
        # fetch fresh data
        latest_all = get_latest_data_for_all_fridges()
        rows = []
        for fid, addr in get_fridge_locations().items():
            if fid not in coords:
                continue
            data = latest_all.get(fid, {})
            temp = data.get("temp")
            if temp is not None:
                status, _ = determine_fridge_status(float(temp))
                door    = data.get("door_usage", "N/A")
                updated = data.get("est_time",    "N/A")
            else:
                status, door, updated = "No data", "N/A", "N/A"

            rows.append({
                "Fridge ID":         fid,
                "Address":           addr,
                "Status":            status,
                "Temperature (°C)":  temp if temp is not None else "No data",
                "Door Usage (24h)":  door,
                "Last Updated":      updated
            })

        df = pd.DataFrame(rows)
        filtered = df[df["Status"].isin(status_filter)]

        with refresh.container():
            # table + pie in two columns
            col_table, col_chart = st.columns([3,2])

            with col_table:
                st.subheader("Fridge Status Table")
                st.caption(f"Showing {len(filtered)} of {len(df)} fridges")
                styled = filtered.style.map(
                    color_status_style(), subset=["Status"]
                )
                st.dataframe(styled, use_container_width=True)

            with col_chart:
                st.subheader("Status Distribution")
                counts = filtered["Status"].value_counts()
                if not counts.empty:
                    fig = px.pie(
                        names=counts.index,
                        values=counts.values,
                        color=counts.index,
                        color_discrete_map=get_status_color_map()
                    )
                    safe_plotly_chart(fig, prefix="map_status_pie")
                else:
                    st.info("No statuses to show.")

            st.caption(f"Last refreshed: {datetime.now():%Y-%m-%d %H:%M:%S}")

        time.sleep(config.REFRESH_RATE)
