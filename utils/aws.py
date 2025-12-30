import boto3
import streamlit as st
import pandas as pd
from datetime import datetime
import config

# -- AWS Session Handling -----------------------------------------------------
_boto3_session = None

def set_aws_session(boto3_session):
    """
    Set the AWS session for the app and validate credentials via STS.
    The session should be created server-side (e.g., from Streamlit Secrets)
    and initialized once at startup in main.py.
    """
    global _boto3_session
    try:
        sts = boto3_session.client("sts")
        sts.get_caller_identity()
    except Exception:
        st.error(
            "AWS credentials are not configured correctly for this deployment. "
            "If you are the maintainer, verify Streamlit Secrets and IAM permissions."
        )
        st.stop()

    _boto3_session = boto3_session


def get_timestream_client():
    """Return a Timestream Query client from the initialized session."""
    if _boto3_session is None:
        st.error(
            "AWS session is not initialized. This app expects credentials to be "
            "configured server-side (Streamlit Secrets) and set during startup."
        )
        st.stop()

    return _boto3_session.client("timestream-query")

# -- Query Execution ----------------------------------------------------------
@st.cache_data(ttl=config.REFRESH_RATE)
def query_timestream(query: str):
    """Execute a query against AWS Timestream using the configured session."""
    client = get_timestream_client()
    try:
        return client.query(QueryString=query)
    except Exception as e:
        st.error(f"Error querying Timestream: {e}")
        return None

# -- Result Parsing -----------------------------------------------------------
def parse_query_result(result):
    """Parse Timestream query results into a pandas DataFrame."""
    if not result or "ColumnInfo" not in result:
        return pd.DataFrame()

    columns = [col["Name"] for col in result["ColumnInfo"]]
    rows = []

    for row in result.get("Rows", []):
        parsed = []
        for cell in row.get("Data", []):
            if "ScalarValue" in cell:
                parsed.append(cell["ScalarValue"])
            elif "NullValue" in cell:
                parsed.append(None)
            else:
                parsed.append(None)
        rows.append(parsed)

    return pd.DataFrame(rows, columns=columns)

# -- Convenience Functions ----------------------------------------------------
@st.cache_data(ttl=config.REFRESH_RATE)
def get_latest_data_for_all_fridges():
    """Get latest data for all fridges (last 24 hours)."""
    query = f"""
    SELECT fridge_id, est_time, temp, door_usage, time
    FROM "{config.DATABASE_NAME}"."{config.TABLE_NAME}"
    WHERE time > ago(24h)
    ORDER BY time DESC
    """
    result = query_timestream(query)
    df = parse_query_result(result)

    if df.empty or "fridge_id" not in df.columns:
        return {}

    latest = {}
    for fridge in config.FRIDGE_OPTIONS.values():
        sub = df[df["fridge_id"] == fridge]
        if not sub.empty:
            latest[fridge] = sub.iloc[0].to_dict()
    return latest

@st.cache_data(ttl=config.REFRESH_RATE)
def get_latest_data_for_fridge(fridge_id):
    """Get latest data for a specific fridge."""
    query = f"""
    SELECT fridge_id, est_time, temp, door_usage, time
    FROM "{config.DATABASE_NAME}"."{config.TABLE_NAME}"
    WHERE fridge_id = '{fridge_id}'
    ORDER BY time DESC
    LIMIT 1
    """
    result = query_timestream(query)
    df = parse_query_result(result)
    return df.iloc[0].to_dict() if not df.empty else None

@st.cache_data(ttl=config.REFRESH_RATE)
def get_historical_data_for_fridge(fridge_id, start_datetime, end_datetime):
    """Get historical data for a fridge in a time range."""
    start_str = start_datetime.strftime("%m/%d/%Y, %I:%M:%S %p")
    end_str   = end_datetime.strftime("%m/%d/%Y, %I:%M:%S %p")

    query = f"""
    SELECT est_time, temp, door_usage, fridge_id, region, time
    FROM "{config.DATABASE_NAME}"."{config.TABLE_NAME}"
    WHERE fridge_id = '{fridge_id}'
      AND parse_datetime(est_time, 'MM/dd/yyyy, hh:mm:ss a')
          BETWEEN parse_datetime('{start_str}', 'MM/dd/yyyy, hh:mm:ss a')
              AND parse_datetime('{end_str}', 'MM/dd/yyyy, hh:mm:ss a')
    ORDER BY time DESC
    """
    result = query_timestream(query)
    df = parse_query_result(result)

    if df.empty:
        return pd.DataFrame()

    df["display_time"] = df["est_time"]
    df["est_time_dt"] = pd.to_datetime(
        df["est_time"], format="%m/%d/%Y, %I:%M:%S %p", errors="coerce"
    )
    return df
