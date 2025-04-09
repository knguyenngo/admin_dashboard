import streamlit as st
import pandas as pd
import plotly.express as px
import time
import folium
from streamlit_folium import folium_static
from datetime import datetime, timedelta

from utils.aws import get_latest_data_for_fridge, get_historical_data_for_fridge
from utils.data import determine_fridge_status, get_all_fridge_coordinates
from utils.helpers import create_tooltip, safe_plotly_chart
from components.tooltips import create_dashboard_guides
import config

def show_dashboard():
    """Display the dashboard page"""
    # Define query options
    st.sidebar.title("Fridge Selection")
    # Create a dropdown for fridge selection
    fridge_selection = st.sidebar.selectbox(
        "Select Fridge",
        options=list(config.FRIDGE_OPTIONS.keys()),
        format_func=lambda x: f"{x}: {config.FRIDGE_OPTIONS[x]}",
        key="fridge_select"
    )
    fridge_id = config.FRIDGE_OPTIONS[fridge_selection]

    # Display selected fridge ID
    st.sidebar.info(f"Selected fridge ID: {fridge_id}")

    # Time range selector for historical data
    st.sidebar.title("Historical Data")
    time_range = st.sidebar.selectbox(
        "Select Time Range",
        ["Last Hour", "Last 24 Hours", "Last 7 Days", "Custom"],
        key="time_range"
    )

    # Handle custom time range
    if time_range == "Custom":
        start_date = st.sidebar.date_input("Start Date", datetime.now() - timedelta(days=1), key="start_date")
        end_date = st.sidebar.date_input("End Date", datetime.now(), key="end_date")
        start_time = st.sidebar.time_input("Start Time", datetime.min.time(), key="start_time")
        end_time = st.sidebar.time_input("End Time", datetime.max.time(), key="end_time")
        
        start_datetime = datetime.combine(start_date, start_time)
        end_datetime = datetime.combine(end_date, end_time)
    else:
        end_datetime = datetime.now()
        if time_range == "Last Hour":
            start_datetime = end_datetime - timedelta(hours=1)
        elif time_range == "Last 24 Hours":
            start_datetime = end_datetime - timedelta(days=1)
        else:  # Last 7 Days
            start_datetime = end_datetime - timedelta(days=7)

    # Add fridge details to the dashboard header
    st.title(f"Fridge Monitoring Dashboard")
    
    # Show guides if tips are enabled
    if st.session_state.show_tips:
        create_dashboard_guides()
    
    # Create columns for header info and mini map
    header_col1, header_col2 = st.columns([3, 2])
    
    with header_col1:
        st.subheader(f"Selected Fridge: {fridge_id}")
        st.markdown(f"**Location**: {config.FRIDGE_LOCATIONS.get(fridge_id, 'Location not available')}")
        
        # Add tooltip for fridge location if tips are enabled
        if st.session_state.show_tips:
            st.markdown(create_tooltip(
                "What does the status mean?", 
                "• <b>Operating normally</b>: Temperature between 2-6°C<br>"
                "• <b>Too cold</b>: Temperature below 2°C<br>"
                "• <b>Too warm</b>: Temperature above 6°C<br>"
                "• Door usage counts how many times the fridge was opened"
            ), unsafe_allow_html=True)
    
    with header_col2:
        # Show a mini map of the selected fridge
        fridge_coords = get_all_fridge_coordinates()
        if fridge_id in fridge_coords:
            lat, lon = fridge_coords[fridge_id]
            mini_map = folium.Map(location=[lat, lon], zoom_start=15, width=400, height=200)
            folium.Marker(
                [lat, lon],
                popup=f"<b>{fridge_id}</b><br>{config.FRIDGE_LOCATIONS[fridge_id]}",
                tooltip=fridge_id,
                icon=folium.Icon(color="blue", icon="snowflake", prefix="fa")
            ).add_to(mini_map)
            folium_static(mini_map, width=400, height=200)
        else:
            st.warning("Location coordinates not available for this fridge")

    # Auto-refresh container
    refresh_container = st.empty()
    
    while True:
        with refresh_container.container():
            # Display latest data
            st.subheader("Current Status")
            
            # Feature highlight for current status if tips are enabled
            if st.session_state.show_tips:
                st.markdown("""
                <div style="border: 1px dashed #4CAF50; padding: 10px; border-radius: 5px; margin-bottom: 15px;">
                    <p><strong>📊 Real-time Status:</strong> Shows the current temperature, door usage, and operational status.
                    Data refreshes automatically every 5 seconds.</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Get latest data for this fridge
            latest_data = get_latest_data_for_fridge(fridge_id)
            
            if latest_data is None:
                st.warning(f"No recent data available for {fridge_id}.")
            
            # Display latest metrics in a nice layout
            if latest_data:
                # Determine status based on temperature
                if 'temp' in latest_data and latest_data['temp'] is not None:
                    temp = float(latest_data['temp']) 
                    status, color = determine_fridge_status(temp)
                else:
                    temp = None
                    status = "Unknown"
                    color = "gray"
                
                # Get door usage
                door_usage = latest_data.get('door_usage', 'N/A')
                
                # Display timestamp
                est_time = latest_data.get('est_time', 'N/A')
                
                # Create a nice layout for current status
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        label="Temperature",
                        value=f"{temp}°C" if temp is not None else "No data",
                        delta=None
                    )
                    
                with col2:
                    st.metric(
                        label="Door Usage (24h)",
                        value=door_usage if door_usage != 'N/A' else "No data",
                        delta=None
                    )
                    
                with col3:
                    # Create a colored status indicator
                    st.markdown(f"""
                    <div style="
                        background-color: {color}; 
                        padding: 10px; 
                        border-radius: 5px; 
                        color: white; 
                        text-align: center;
                        margin-top: 25px;
                        font-weight: bold;
                    ">
                        {status}
                    </div>
                    """, unsafe_allow_html=True)
                
                st.caption(f"Last updated: {est_time}")
                st.caption(f"Data refreshes every {config.REFRESH_RATE} seconds. Next refresh: {(datetime.now() + timedelta(seconds=config.REFRESH_RATE)).strftime('%H:%M:%S')}")
            else:
                st.error("No data available for this fridge.")
        
            # Get historical data
            st.subheader("Historical Data")
            
            # Feature highlight for historical data if tips are enabled
            if st.session_state.show_tips:
                st.markdown("""
                <div style="border: 1px dashed #2196F3; padding: 10px; border-radius: 5px; margin-bottom: 15px;">
                    <p><strong>📈 Historical Data:</strong> The charts below show temperature and door usage patterns over time.
                    Change the time range in the sidebar to see different periods of data.</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Show a loading indicator
            with st.spinner("Loading historical data..."):
                # Get historical data without aggregation
                historical_data = get_historical_data_for_fridge(
                    fridge_id, 
                    start_datetime, 
                    end_datetime
                )
                
                if historical_data.empty:
                    st.warning(f"No historical data available for {fridge_id} in the selected time range.")
                else:
                    # Display the historical data
                    with st.expander("Show Raw Data"):
                        st.dataframe(historical_data)
                    
                    # Create title for visualization
                    title_prefix = f"Fridge {fridge_selection}: {fridge_id}"
                    
                    # Temperature chart section
                    st.subheader("Temperature Over Time")
                    
                    # Regular temperature chart with unique key
                    fig_temp = px.line(
                        historical_data, 
                        x="est_time_dt", 
                        y="temp",
                        title=f"{title_prefix} - Temperature over time",
                        labels={"est_time_dt": "Time", "temp": "Temperature (°C)"}
                    )
                    safe_plotly_chart(fig_temp, prefix="temp_chart")

                    # Door usage chart section
                    st.subheader("Door Usage Over Time")
                    
                    # Regular door usage chart with unique key
                    fig_door = px.scatter(
                        historical_data, 
                        x="est_time_dt", 
                        y="door_usage",
                        title=f"{title_prefix} - Door Usage over time",
                        labels={"est_time_dt": "Time", "door_usage": "Door Usage Count"}
                    )
                    safe_plotly_chart(fig_door, prefix="door_chart")

                    # Add summary metrics
                    temp_stats_col1, temp_stats_col2, temp_stats_col3 = st.columns(3)
                    
                    with temp_stats_col1:
                        st.metric(
                            "Average Temperature", 
                            f"{pd.to_numeric(historical_data['temp'], errors='coerce').mean():.2f}°C"
                        )
                    
                    with temp_stats_col2:
                        st.metric(
                            "Max Temperature", 
                            f"{pd.to_numeric(historical_data['temp'], errors='coerce').max():.2f}°C"
                        )
                        
                    with temp_stats_col3:
                        st.metric(
                            "Min Temperature", 
                            f"{pd.to_numeric(historical_data['temp'], errors='coerce').min():.2f}°C"
                        )
                        
                    door_stats_col1, door_stats_col2, door_stats_col3 = st.columns(3)
                    
                    with door_stats_col1:
                        st.metric(
                            "Total Door Usage", 
                            f"{pd.to_numeric(historical_data['door_usage'], errors='coerce').sum()}"
                        )
                    
                    with door_stats_col2:
                        st.metric(
                            "Max Door Usage", 
                            f"{pd.to_numeric(historical_data['door_usage'], errors='coerce').max()}"
                        )
                        
                    with door_stats_col3:
                        st.metric(
                            "Avg Door Usage", 
                            f"{pd.to_numeric(historical_data['door_usage'], errors='coerce').mean():.2f}"
                        )
        
        # Wait before refreshing
        time.sleep(config.REFRESH_RATE)