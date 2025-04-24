def determine_fridge_status(temp):
    """Determine fridge status based on temperature"""
    if temp is None:
        return "Unknown", "gray"
    
    temp = float(temp)
    if 2 <= temp <= 6:
        return "Operating normally", "green"
    elif temp < 2:
        return "Too cold", "blue"
    else:  # temp > 6
        return "Too warm", "red"

def get_all_fridge_coordinates():
    """Get all fridge coordinates"""
    from config import FRIDGE_COORDINATES
    return FRIDGE_COORDINATES

def get_fridge_locations():
    from config import FRIDGE_LOCATIONS
    return FRIDGE_LOCATIONS