# RVA Community Fridges – Admin Dashboard

[Live Dashboard](https://rvacfdash.streamlit.app/)

## Overview
Internal admin dashboard for monitoring operational data from community fridges across Richmond, VA. Built to support reliability, maintenance, and data-driven decision making for a community food access initiative.

## What It Does
- Visualizes real-time and historical fridge telemetry
- Surfaces temperature, door activity, and device health
- Provides centralized visibility for administrators

## Tech Stack
- Frontend: Streamlit
- Backend: AWS Lambda (Python), API Gateway
- Database: Amazon Timestream
- Cloud: AWS
- Infrastructure: Docker, CloudWatch

## Data
- Temperature readings
- Door open/close events
- Device uptime and status

## Status
Active internal tool. Admin-only access.

## Notes
This project was built to support a real-world community initiative and emphasizes reliability, observability, and clear data presentation over public-facing features.

## Screenshots
![Admin Dashboard](images/example1.png)
![Admin Dashboard2](images/example2.png)
