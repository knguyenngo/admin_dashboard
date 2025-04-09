import boto3
import streamlit as st
import pandas as pd
from datetime import datetime
import config

@st.cache_data(ttl=config.REFRESH_RATE)
def query_timestream(query, aws_access_key=config.AWS_ACCESS_KEY, 
                     aws_secret_key=config.AWS_SECRET_KEY, 
                     region=config.AWS_REGION):
    """Execute a query against AWS Timestream database"""
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

def parse_query_result(result):
    """Parse Timestream query results into pandas DataFrame"""
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

@st.cache_data(ttl=config.REFRESH_RATE)
def get_latest_data_for_all_fridges():
    """Get latest data for all fridges"""
    # Query to get latest data for all fridges
    query = f"""
    SELECT fridge_id, est_time, temp, door_usage
    FROM "{config.DATABASE_NAME}"."{config.TABLE_NAME}"
    WHERE time > ago(24h)
    ORDER BY est_time DESC
    """
    
    result = query_timestream(query)
    df = parse_query_result(result)
    
    if df.empty:
        return pd.DataFrame()
    
    # Get latest data for each fridge
    latest_data = {}
    
    if not df.empty and 'fridge_id' in df.columns:
        for fridge_id in config.FRIDGE_OPTIONS.values():
            fridge_data = df[df['fridge_id'] == fridge_id]
            if not fridge_data.empty:
                latest_data[fridge_id] = fridge_data.iloc[0].to_dict()
    
    return latest_data

@st.cache_data(ttl=config.REFRESH_RATE)
def get_latest_data_for_fridge(fridge_id):
    """Get latest data for a specific fridge"""
    query = f"""
    SELECT fridge_id, est_time, temp, door_usage
    FROM "{config.DATABASE_NAME}"."{config.TABLE_NAME}"
    WHERE fridge_id = '{fridge_id}'
    ORDER BY est_time DESC
    LIMIT 1
    """
    
    result = query_timestream(query)
    df = parse_query_result(result)
    
    if df.empty:
        return None
    
    return df.iloc[0].to_dict()

@st.cache_data(ttl=config.REFRESH_RATE)
def get_historical_data_for_fridge(fridge_id, start_datetime, end_datetime):
    """Get historical data for a specific fridge in a time range"""
    # Format timestamps for est_time comparison
    start_time_str = start_datetime.strftime('%m/%d/%Y, %I:%M:%S %p')
    end_time_str = end_datetime.strftime('%m/%d/%Y, %I:%M:%S %p')
    
    query = f"""
    SELECT est_time, temp, door_usage, fridge_id, region, time
    FROM "{config.DATABASE_NAME}"."{config.TABLE_NAME}"
    WHERE fridge_id = '{fridge_id}'
    AND parse_datetime(est_time, 'MM/dd/yyyy, hh:mm:ss a') 
        BETWEEN parse_datetime('{start_time_str}', 'MM/dd/yyyy, hh:mm:ss a') 
        AND parse_datetime('{end_time_str}', 'MM/dd/yyyy, hh:mm:ss a')
    ORDER BY est_time DESC
    """
    
    result = query_timestream(query)
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