# config.py
# Keep this file "dumb": constants only. Do not import streamlit or read secrets here.

# Page configuration
PAGE_TITLE = "Fridge Monitoring Dashboard"
PAGE_ICON = "🧊"
LAYOUT = "wide"

# Defaults (actual values set in main.py from Streamlit Secrets)
AWS_REGION_DEFAULT = "us-east-1"
DATABASE_NAME_DEFAULT = "RVACF-Timestream-DB"
TABLE_NAME_DEFAULT = "multi_value"

# Define fridge options and locations
FRIDGE_OPTIONS = {
    3: "oakwood-art-fridge",
    7: "cary-st-fridge",
    11: "fonticello-fridge",
    14: "expo-fridge"
}

FRIDGE_LOCATIONS = {
    "fonticello-fridge": "255 W 27th St, Richmond, VA",
    "oakwood-art-fridge": "917 N 35th St, Richmond, VA",
    "cary-st-fridge": "2913 W Cary St, Richmond, VA",
    "expo-fridge": "1200 West Broad Street, Richmond, VA"
}

FRIDGE_COORDINATES = {
    "fonticello-fridge": (37.5316, -77.4330),
    "oakwood-art-fridge": (37.5409, -77.4113),
    "cary-st-fridge": (37.5553, -77.4834),
    "expo-fridge": (37.55227, -77.4526)
}

# Help text for sidebar
HELP_TEXT = """
### Dashboard Controls
- **Navigation:** Switch between Dashboard and Map View
- **Fridge Selection:** Choose which fridge to monitor
- **Time Range:** Select data time period
- **Auto Refresh:** Toggle to start/stop

### Status Colors
- **Green:** Operating normally
- **Blue:** Too cold
- **Red:** Too warm
- **Gray:** No data available
"""

KEYBOARD_SHORTCUTS = """
- **R** - Manually refresh data
- **F** - Toggle fullscreen
- **S** - Save current view
"""

# Data refresh rate in seconds
REFRESH_RATE = 5

