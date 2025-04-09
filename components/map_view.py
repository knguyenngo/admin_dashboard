import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from folium.plugins import MarkerCluster
from datetime import datetime, timedelta
import time

def show_map_view():
    """
    Renders the map view page showing all community fridges on an interactive map
    with their current status and information.
    """
    st.title("Community Fridge Locations")
    
    if st.session_state.show_tips:
        create_map_guides()
    
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
            for fridge_id, address in get_fridge_locations().items():
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
            if st.session_state.get('show_tips', True):
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
            if not fridge_df.empty and 'Status' in fridge_df.columns:
                status_counts = fridge_df['Status'].value_counts()
                
                # Import plotly only if needed to reduce startup time
                import plotly.express as px
                
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
            else:
                st.warning("No status data available for pie chart")
            
            # Display auto-refresh notice
            st.caption(f"Data refreshes every 5 seconds. Last refreshed: {datetime.now().strftime('%H:%M:%S')}")
            
        # Wait for 5 seconds before refreshing
        time.sleep(5)