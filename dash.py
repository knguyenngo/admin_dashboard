import streamlit as st
import pandas as pd
import plotly.express as px
import boto3
from datetime import datetime, timedelta
import time
import requests
import folium
from streamlit_folium import folium_static
from folium.plugins import MarkerCluster

# Page configuration
st.set_page_config(
    page_title="Fridge Monitoring Dashboard",
    page_icon="🧊",
    layout="wide"
)

# Custom CSS for tooltips, guide elements, and modal popup
st.markdown("""
<style>
.tooltip {
    position: relative;
    display: inline-block;
    cursor: pointer;
}
.tooltip .tooltiptext {
    visibility: hidden;
    width: 250px;
    background-color: #555;
    color: #fff;
    text-align: left;
    border-radius: 6px;
    padding: 10px;
    position: absolute;
    z-index: 1;
    bottom: 125%;
    left: 50%;
    margin-left: -125px;
    opacity: 0;
    transition: opacity 0.3s;
    font-size: 14px;
}
.tooltip:hover .tooltiptext {
    visibility: visible;
    opacity: 0.95;
}
.guide-card {
    background: linear-gradient(90deg, #1E88E5 0%, #64B5F6 100%);
    color: white;
    margin: 10px 0;
    padding: 16px;
    border-radius: 6px;
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}
.welcome-banner {
    background: linear-gradient(90deg, #1E88E5 0%, #64B5F6 100%);
    color: white;
    padding: 20px;
    border-radius: 6px;
    margin-bottom: 20px;
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}
.close-button {
    float: right;
    background: rgba(255,255,255,0.3);
    border: none;
    color: white;
    padding: 5px 10px;
    border-radius: 3px;
    cursor: pointer;
}

/* New modal popup styles */
.modal-overlay {
    display: flex;
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.5);
    z-index: 9999;
    justify-content: center;
    align-items: center;
}

.modal-content {
    background: linear-gradient(90deg, #1E88E5 0%, #64B5F6 100%);
    color: white;
    width: 80%;
    max-width: 800px;
    padding: 30px;
    border-radius: 8px;
    box-shadow: 0 8px 16px rgba(0,0,0,0.2);
    position: relative;
    animation: modalFadeIn 0.5s ease;
}

@keyframes modalFadeIn {
    from {opacity: 0; transform: translateY(-50px);}
    to {opacity: 1; transform: translateY(0);}
}

.modal-close {
    position: absolute;
    top: 15px;
    right: 15px;
    background: rgba(255,255,255,0.3);
    border: none;
    color: white;
    width: 30px;
    height: 30px;
    border-radius: 50%;
    font-size: 18px;
    display: flex;
    justify-content: center;
    align-items: center;
    cursor: pointer;
    transition: background 0.3s;
}

.modal-close:hover {
    background: rgba(255,255,255,0.5);
}

.modal-button {
    background-color: white;
    color: #1E88E5;
    border: none;
    padding: 10px 20px;
    border-radius: 4px;
    font-weight: bold;
    cursor: pointer;
    margin-top: 15px;
    transition: background 0.3s;
}

.modal-button:hover {
    background-color: #f0f0f0;
}
</style>
""", unsafe_allow_html=True)

# Modal popup JavaScript
st.markdown("""
<script>
document.addEventListener('DOMContentLoaded', function() {
    // Function to create and show modal
    function showModal() {
        // Create overlay
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        
        // Create modal content
        const modal = document.createElement('div');
        modal.className = 'modal-content';
        
        // Add heading
        const heading = document.createElement('h2');
        heading.textContent = '👋 Welcome to the Fridge Monitoring Dashboard!';
        modal.appendChild(heading);
        
        // Add content
        const content = document.createElement('div');
        content.innerHTML = `
            <p>This dashboard provides real-time monitoring of community fridges across Richmond. 
            Here are some quick tips to get started:</p>
            <ul>
                <li>Select a fridge from the sidebar dropdown</li>
                <li>View current temperature and door usage data</li>
                <li>Explore historical data with different time ranges</li>
                <li>Switch to Map View to see all fridges at once</li>
            </ul>
        `;
        modal.appendChild(content);
        
        // Add close button
        const closeBtn = document.createElement('button');
        closeBtn.className = 'modal-close';
        closeBtn.textContent = '✕';
        closeBtn.onclick = function() {
            document.body.removeChild(overlay);
            // Store in localStorage that the user has seen the welcome message
            localStorage.setItem('welcomeModalSeen', 'true');
        };
        modal.appendChild(closeBtn);
        
        // Add "Get Started" button
        const startBtn = document.createElement('button');
        startBtn.className = 'modal-button';
        startBtn.textContent = 'Get Started';
        startBtn.onclick = function() {
            document.body.removeChild(overlay);
            // Store in localStorage that the user has seen the welcome message
            localStorage.setItem('welcomeModalSeen', 'true');
        };
        modal.appendChild(startBtn);
        
        // Add modal to overlay
        overlay.appendChild(modal);
        
        // Add overlay to body
        document.body.appendChild(overlay);
    }
    
    // Check if user has seen the welcome message before
    if (!localStorage.getItem('welcomeModalSeen')) {
        // Small delay to ensure the page has loaded
        setTimeout(showModal, 500);
    }
});
</script>
""", unsafe_allow_html=True)

# Load AWS credentials from environment variables or config
import os
from dotenv import load_dotenv

# Initialize environment variables
load_dotenv()

# Sidebar for configuration
st.sidebar.title("Fridge Monitoring Dashboard")

# AWS configuration
aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
aws_region = os.getenv("AWS_REGION", "us-east-1")

# Timestream database and table configuration
database_name = os.getenv("TIMESTREAM_DATABASE", "RVACF-Timestream-DB")
table_name = os.getenv("TIMESTREAM_TABLE", "multi_value")

# Define fridge options and locations
fridge_options = {
    0: "venable-st-fridge",
    1: "hull-st-fridge",
    2: "new-kingdom-fridge",
    3: "oakwood-art-fridge",
    4: "city-church-fridge",
    5: "studio-23-fridge",
    6: "fulton-hill-fridge",
    7: "cary-st-fridge",
    8: "sankofa-fridge",
    9: "meadowbridge-fridge",
    10: "6pic-fridge",
    11: "fonticello-fridge",
    12: "matchbox-mutualaid",
    13: "main-st-fridge"
}

fridge_locations = {
    'venable-st-fridge': '2025 Venable St, Richmond, VA',
    'new-kingdom-fridge': '3200 Dill Ave, Richmond, VA',
    'studio-23-fridge': '109 W 15th St, Richmond, VA',
    'hull-st-fridge': '2414 Hull St, Richmond, VA',
    'matchbox-mutualaid': '2919 North Ave, Richmond, VA',
    '6pic-fridge': '3001 Meadowbridge Rd, Virginia',
    'meadowbridge-fridge': '3613 Meadowbridge Rd, Richmond, VA',
    'fonticello-fridge': '255 W 27th St, Richmond, VA',
    'fulton-hill-fridge': '4809 Parker St, Richmond, VA',
    'city-church-fridge': '4700 Oakleys Ln, Richmond, VA',
    'sankofa-fridge': '309 Covington Rd, Richmond, VA',
    'oakwood-art-fridge': '917 N 35th St, Richmond, VA',
    'cary-st-fridge': '2913 W Cary St, Richmond, VA',
    'main-st-fridge': '121 E Main St, Richmond, VA'
}

fridge_coordinates = {
    'venable-st-fridge': (37.5395, -77.4259),
    'new-kingdom-fridge': (37.5601, -77.4368),
    'studio-23-fridge': (37.5360, -77.4338),
    'hull-st-fridge': (37.5358, -77.4478),
    'matchbox-mutualaid': (37.5807, -77.4255),
    '6pic-fridge': (37.5756, -77.4219),
    'meadowbridge-fridge': (37.5870, -77.4215),
    'fonticello-fridge': (37.5316, -77.4330),
    'fulton-hill-fridge': (37.5299, -77.4048),
    'city-church-fridge': (37.5238, -77.3477),
    'sankofa-fridge': (37.5659, -77.4666),
    'oakwood-art-fridge': (37.5409, -77.4113),
    'cary-st-fridge': (37.5553, -77.4834),
    'main-st-fridge': (37.5350, -77.4396)
}

# Function to get fridge coordinates
def get_all_fridge_coordinates():
    return fridge_coordinates

# Function to connect to AWS Timestream and execute queries
# Reduced cache TTL to 5 seconds
@st.cache_data(ttl=5)
def query_timestream(query, aws_access_key, aws_secret_key, region):
    if not aws_access_key or not aws_secret_key:
        st.warning("AWS credentials not found.")
        return None
        
    client = boto3.client(
        'timestream-query',
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name=region
    )
    
    try:
        response = client.query(QueryString=query)
        return response
    except Exception as e:
        st.error(f"Error querying Timestream: {str(e)}")
        return None

# Helper function to create unique keys for Streamlit elements
def unique_key(prefix=""):
    """Generate a unique key for Streamlit elements to avoid duplicate IDs"""
    return f"{prefix}_{datetime.now().timestamp()}_{id(datetime.now())}"

# Helper function to display plotly charts with guaranteed unique keys
def safe_plotly_chart(fig, use_container_width=True, prefix="plot"):
    """Display a plotly chart with a guaranteed unique key"""
    key = unique_key(prefix)
    return st.plotly_chart(fig, use_container_width=use_container_width, key=key)

# Function to parse Timestream query results into pandas DataFrame
def parse_query_result(result):
    if not result:
        return pd.DataFrame()
        
    columns = [col['Name'] for col in result['ColumnInfo']]
    data = []
    
    for row in result['Rows']:
        parsed_row = []
        for cell in row['Data']:
            if 'ScalarValue' in cell:
                parsed_row.append(cell['ScalarValue'])
            elif 'NullValue' in cell:
                parsed_row.append(None)
            else:
                parsed_row.append(str(cell))
        
        data.append(parsed_row)
    
    return pd.DataFrame(data, columns=columns)

# Function to get latest data for all fridges
# Reduced cache TTL to 5 seconds
@st.cache_data(ttl=5)
def get_latest_data_for_all_fridges():
    # Query to get latest data for all fridges
    query = f"""
    SELECT fridge_id, est_time, temp, door_usage
    FROM "{database_name}"."{table_name}"
    WHERE time > ago(24h)
    ORDER BY est_time DESC
    """
    
    result = query_timestream(query, aws_access_key, aws_secret_key, aws_region)
    df = parse_query_result(result)
    
    if df.empty:
        return pd.DataFrame()
    
    # Get latest data for each fridge
    latest_data = {}
    
    if not df.empty and 'fridge_id' in df.columns:
        for fridge_id in fridge_options.values():
            fridge_data = df[df['fridge_id'] == fridge_id]
            if not fridge_data.empty:
                latest_data[fridge_id] = fridge_data.iloc[0].to_dict()
    
    return latest_data

# Function to get latest data for a specific fridge
# Reduced cache TTL to 5 seconds
@st.cache_data(ttl=5)
def get_latest_data_for_fridge(fridge_id):
    query = f"""
    SELECT fridge_id, est_time, temp, door_usage
    FROM "{database_name}"."{table_name}"
    WHERE fridge_id = '{fridge_id}'
    ORDER BY est_time DESC
    LIMIT 1
    """
    
    result = query_timestream(query, aws_access_key, aws_secret_key, aws_region)
    df = parse_query_result(result)
    
    if df.empty:
        return None
    
    return df.iloc[0].to_dict()

# Function to get historical data for a specific fridge
# Reduced cache TTL to 5 seconds
@st.cache_data(ttl=5)
def get_historical_data_for_fridge(fridge_id, start_datetime, end_datetime):
    # Format timestamps for est_time comparison
    # Use MM/DD/YYYY, HH:MM:SS AM/PM format for est_time string comparison
    start_time_str = start_datetime.strftime('%m/%d/%Y, %I:%M:%S %p')
    end_time_str = end_datetime.strftime('%m/%d/%Y, %I:%M:%S %p')
    
    # For regular queries, directly use est_time
    query = f"""
    SELECT est_time, temp, door_usage, fridge_id, region, time
    FROM "{database_name}"."{table_name}"
    WHERE fridge_id = '{fridge_id}'
    AND parse_datetime(est_time, 'MM/dd/yyyy, hh:mm:ss a') 
        BETWEEN parse_datetime('{start_time_str}', 'MM/dd/yyyy, hh:mm:ss a') 
        AND parse_datetime('{end_time_str}', 'MM/dd/yyyy, hh:mm:ss a')
    ORDER BY est_time DESC
    """
    
    result = query_timestream(query, aws_access_key, aws_secret_key, aws_region)
    df = parse_query_result(result)
    
    if df.empty:
        return pd.DataFrame()
    
    # Process data for visualization
    if 'est_time' in df.columns:
        # Keep original est_time for display
        df['display_time'] = df['est_time']
        # Create a datetime column for plotting
        df['est_time_dt'] = pd.to_datetime(df['est_time'], format='%m/%d/%Y, %I:%M:%S %p')
    
    return df

# Function to determine fridge status
def determine_fridge_status(temp):
    if temp is None:
        return "Unknown", "gray"
    
    temp = float(temp)
    if 2 <= temp <= 6:
        return "Operating normally", "green"
    elif temp < 2:
        return "Too cold", "blue"
    else:  # temp > 6
        return "Too warm", "red"

# Initialize session state for controlling tooltips
if 'show_tips' not in st.session_state:
    st.session_state.show_tips = True
# Hide the old welcome banners
if 'show_welcome' not in st.session_state:
    st.session_state.show_welcome = False  # We'll use the JavaScript modal instead
if 'show_map_welcome' not in st.session_state:
    st.session_state.show_map_welcome = False  # We'll use the JavaScript modal for this as well

# Helper function to create tooltips
def create_tooltip(text, tip_text):
    return f"""
    <div class="tooltip">{text} ⓘ
        <span class="tooltiptext">{tip_text}</span>
    </div>
    """

# Main navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Select Page", ["Dashboard", "Map View"], key="nav_radio")

# Show tips toggle in sidebar
tips_enabled = st.sidebar.checkbox("Show Helper Tips", value=st.session_state.show_tips, key="tips_toggle")
if tips_enabled != st.session_state.show_tips:
    st.session_state.show_tips = tips_enabled

# Show tutorial button that will trigger modal
if st.sidebar.button("Show Welcome Tutorial", key="show_welcome_modal"):
    # Use JavaScript to show the modal when button is clicked
    st.markdown("""
    <script>
    // Function to create and show modal
    function showWelcomeModal() {
        // Create overlay
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        
        // Create modal content
        const modal = document.createElement('div');
        modal.className = 'modal-content';
        
        // Add heading
        const heading = document.createElement('h2');
        heading.textContent = '👋 Welcome to the Fridge Monitoring Dashboard!';
        modal.appendChild(heading);
        
        // Add content
        const content = document.createElement('div');
        content.innerHTML = `
            <p>This dashboard provides real-time monitoring of community fridges across Richmond. 
            Here are some quick tips to get started:</p>
            <ul>
                <li>Select a fridge from the sidebar dropdown</li>
                <li>View current temperature and door usage data</li>
                <li>Explore historical data with different time ranges</li>
                <li>Switch to Map View to see all fridges at once</li>
            </ul>
        `;
        modal.appendChild(content);
        
        // Add close button
        const closeBtn = document.createElement('button');
        closeBtn.className = 'modal-close';
        closeBtn.textContent = '✕';
        closeBtn.onclick = function() {
            document.body.removeChild(overlay);
        };
        modal.appendChild(closeBtn);
        
        // Add "Get Started" button
        const startBtn = document.createElement('button');
        startBtn.className = 'modal-button';
        startBtn.textContent = 'Get Started';
        startBtn.onclick = function() {
            document.body.removeChild(overlay);
        };
        modal.appendChild(startBtn);
        
        // Add modal to overlay
        overlay.appendChild(modal);
        
        // Add overlay to body
        document.body.appendChild(overlay);
    }
    
    // Small delay to ensure the page has loaded
    setTimeout(showWelcomeModal, 300);
    </script>
    """, unsafe_allow_html=True)

if page == "Dashboard":
    # Define query options
    st.sidebar.title("Fridge Selection")
    # Create a dropdown for fridge selection
    fridge_selection = st.sidebar.selectbox(
        "Select Fridge",
        options=list(fridge_options.keys()),
        format_func=lambda x: f"{x}: {fridge_options[x]}",
        key="fridge_select"
    )
    fridge_id = fridge_options[fridge_selection]

    # Display selected fridge ID
    st.sidebar.info(f"Selected fridge ID: {fridge_id}")

    # Time range selector for historical data
    st.sidebar.title("Historical Data")
    time_range = st.sidebar.selectbox(
        "Select Time Range",
        ["Last Hour", "Last 24 Hours", "Last 7 Days", "Custom"],
        key="time_range"
    )

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
    
    # Quick guide card
    if st.session_state.show_tips:
        st.markdown("""
        <div class="guide-card">
            <h4>🔍 Dashboard Quick Guide</h4>
            <p>Data refreshes every 5 seconds. Use the sidebar to select different fridges and time ranges.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Create columns for header info and mini map
    header_col1, header_col2 = st.columns([3, 2])
    
    with header_col1:
        st.subheader(f"Selected Fridge: {fridge_id}")
        st.markdown(f"**Location**: {fridge_locations.get(fridge_id, 'Location not available')}")
        
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
                popup=f"<b>{fridge_id}</b><br>{fridge_locations[fridge_id]}",
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
                st.caption(f"Data refreshes every 5 seconds. Next refresh: {(datetime.now() + timedelta(seconds=5)).strftime('%H:%M:%S')}")
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
                        st.dataframe(historical_data, key=f"hist_data_{datetime.now().timestamp()}")
                    
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
        
        # Wait for 5 seconds before refreshing
        time.sleep(5)

elif page == "Map View":
    st.title("Community Fridge Locations")
    
    # Quick guide card for map
    if st.session_state.show_tips:
        st.markdown("""
        <div class="guide-card">
            <h4>🔍 Map View Guide</h4>
            <p>Marker colors: <span style="color: green">●</span> Operating normally, 
            <span style="color: blue">●</span> Too cold, 
            <span style="color: red">●</span> Too warm, 
            <span style="color: gray">●</span> No data</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Map container for auto-refresh
    map_refresh_container = st.empty()
    
    while True:
        with map_refresh_container.container():
            # Get all fridge coordinates
            fridge_coords = get_all_fridge_coordinates()
            
            # Create a map centered on Richmond, VA
            m = folium.Map(location=[37.5407, -77.4360], zoom_start=12)
            
            # Create a marker cluster for better visualization
            marker_cluster = MarkerCluster().add_to(m)
            
            # Get latest data for all fridges
            latest_data_all = get_latest_data_for_all_fridges()
            
            # Prepare data for table display
            fridge_table_data = []
            
            # Add markers for each fridge
            for fridge_id, address in fridge_locations.items():
                if fridge_id in fridge_coords:
                    lat, lon = fridge_coords[fridge_id]
                    
                    # Get status data for this fridge
                    if fridge_id in latest_data_all:
                        fridge_data = latest_data_all[fridge_id]
                        
                        if 'temp' in fridge_data and fridge_data['temp'] is not None:
                            # Determine status based on temperature
                            status, color = determine_fridge_status(fridge_data['temp'])
                            temp = float(fridge_data['temp'])
                            door_usage = fridge_data.get('door_usage', 'N/A')
                            last_updated = fridge_data.get('est_time', 'N/A')
                        else:
                            status = "No data"
                            color = "gray"
                            temp = "N/A"
                            door_usage = "N/A"
                            last_updated = "N/A"
                    else:
                        status = "No data"
                        color = "gray"
                        temp = "N/A"
                        door_usage = "N/A"
                        last_updated = "N/A"
                    
                    # Create detailed popup with status info
                    popup_html = f"""
                    <div style="width: 200px">
                        <h4>{fridge_id}</h4>
                        <p><b>Address:</b> {address}</p>
                        <p><b>Status:</b> {status}</p>
                        <p><b>Temperature:</b> {temp if temp != 'N/A' else 'No data'}°C</p>
                        <p><b>Door Usage (24h):</b> {door_usage}</p>
                        <p><b>Last updated:</b> {last_updated}</p>
                        <a href="/?page=Dashboard&fridge_id={fridge_id}" target="_blank">View Details</a>
                    </div>
                    """
                    
                    # Create marker with icon
                    marker = folium.Marker(
                        location=[lat, lon],
                        popup=folium.Popup(popup_html, max_width=300),
                        tooltip=fridge_id,
                        icon=folium.Icon(color=color, icon="snowflake", prefix="fa")
                    )
                    
                    # Add marker to cluster
                    marker.add_to(marker_cluster)
                    
                    # Add data for table
                    fridge_table_data.append({
                        "Fridge ID": fridge_id,
                        "Address": address,
                        "Status": status,
                        "Temperature (°C)": temp if temp != 'N/A' else "No data",
                        "Door Usage (24h)": door_usage,
                        "Last Updated": last_updated
                    })
            
            # Display the map
            st.subheader("Interactive Map of All Community Fridges")
            
            # Map interaction tip if tips are enabled
            if st.session_state.show_tips:
                st.markdown("""
                <div style="border: 1px dashed #FF9800; padding: 10px; border-radius: 5px; margin-bottom: 15px;">
                    <p><strong>🖱️ Map Interaction Tips:</strong> 
                    • Click on markers to see fridge details<br>
                    • Zoom in/out with scroll wheel<br>
                    • Click and drag to pan the map<br>
                    • Click a marker's "View Details" link to see full dashboard for that fridge</p>
                </div>
                """, unsafe_allow_html=True)
                
            folium_static(m, width=1000, height=600)
            
            # Create a table with fridge information
            st.subheader("Fridge Status Information")
            
            # Convert to dataframe and display
            fridge_df = pd.DataFrame(fridge_table_data)
            
            # Add status coloring
            def color_status(val):
                if "normally" in val:
                    return 'background-color: #c6efce; color: #006100'
                elif "cold" in val:
                    return 'background-color: #bdd7ee; color: #1f497d'
                elif "warm" in val:
                    return 'background-color: #ffc7ce; color: #9c0006'
                else:  # No data
                    return 'background-color: #f2f2f2; color: #666666'
            
            # Display styled dataframe
            st.dataframe(fridge_df.style.applymap(color_status, subset=['Status']), key=f"main_df_{datetime.now().timestamp()}")
            
            # Add filtering options with unique key
            st.subheader("Filter Fridges")
            status_filter = st.multiselect(
                "Filter by Status",
                ["Operating normally", "Too cold", "Too warm", "No data"],
                default=["Operating normally", "Too cold", "Too warm", "No data"],
                key=f"status_filter_{datetime.now().timestamp()}"
            )
            
            filtered_df = fridge_df[fridge_df['Status'].isin(status_filter)]
            st.write(f"Showing {len(filtered_df)} fridges")
            st.dataframe(filtered_df.style.applymap(color_status, subset=['Status']), key=f"filtered_df_{datetime.now().timestamp()}")
            
            # Add summary statistics
            st.subheader("Status Summary")
            status_counts = fridge_df['Status'].value_counts()
            fig = px.pie(
                status_counts, 
                values=status_counts.values, 
                names=status_counts.index,
                title="Fridge Status Distribution",
                color=status_counts.index,
                color_discrete_map={
                    "Operating normally": "#c6efce", 
                    "Too cold": "#bdd7ee", 
                    "Too warm": "#ffc7ce",
                    "No data": "#f2f2f2"
                }
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Display auto-refresh notice
            st.caption(f"Data refreshes every 5 seconds. Last refreshed: {datetime.now().strftime('%H:%M:%S')}")
            
        # Wait for 5 seconds before refreshing
        time.sleep(5)

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("Streamlit AWS Timestream Fridge Monitoring Dashboard")

# Add help section to sidebar
with st.sidebar.expander("❓ Need Help?"):
    st.markdown("""
    ### Dashboard Controls
    - **Navigation:** Switch between Dashboard and Map View
    - **Fridge Selection:** Choose which fridge to monitor
    - **Time Range:** Select data time period
    - **Show Helper Tips:** Toggle guide elements on/off
    
    ### Status Colors
    - 🟢 **Green:** Operating normally (2-6°C)
    - 🔵 **Blue:** Too cold (below 2°C)
    - 🔴 **Red:** Too warm (above 6°C)
    - ⚪ **Gray:** No data available
    
    ### Contact
    For technical support, please contact:
    [support@fridgemonitoring.org](mailto:support@fridgemonitoring.org)
    """)

# Add keyboard shortcuts helper
with st.sidebar.expander("⌨️ Keyboard Shortcuts"):
    st.markdown("""
    - **R** - Manually refresh data
    - **F** - Toggle fullscreen
    - **S** - Save current view
    - **D** - Toggle dark/light mode
    """)

# Add timestamp for last refresh
st.sidebar.caption(f"Last refreshed: {datetime.now().strftime('%m/%d/%Y, %I:%M:%S %p')}")

# First-time user tutorial modal (hidden by default)
tutorial_trigger = st.sidebar.button("Show Tutorial", key="tutorial_button")
if tutorial_trigger:
    st.markdown("""
    <script>
    // This would be a tutorial walkthrough implementation
    // In a real implementation, we'd use a proper Streamlit component
    </script>
    """, unsafe_allow_html=True)