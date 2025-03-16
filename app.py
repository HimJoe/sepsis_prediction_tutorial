%%writefile app.py

import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import altair as alt

st.title("Sepsis Alert Threshold Optimization Tool")

# Sidebar for parameters
st.sidebar.header("Clinical Setting Parameters")
beds = st.sidebar.number_input("Number of ICU beds", min_value=5, max_value=200, value=100)
avg_stay = st.sidebar.number_input("Average length of stay (days)", min_value=1.0, max_value=30.0, value=3.0)
minutes_per_alert = st.sidebar.number_input("Minutes to respond to each alert", min_value=1, max_value=60, value=10)
staff_hours = st.sidebar.number_input("Available staff hours per day", min_value=1, max_value=100, value=24)

# Main threshold control
st.header("Alert Threshold Configuration")
threshold = st.slider("Set sepsis alert threshold", min_value=0.0, max_value=1.0, value=0.5, step=0.01)

# Model performance data (in a real app, this would come from your actual model)
# These functions would be replaced with your actual model's performance curves
def get_sensitivity(threshold):
    return max(0, 1 - threshold**0.7)  # Simplified function

def get_specificity(threshold):
    return min(1, 0.4 + 0.6 * threshold**0.6)  # Simplified function

def get_alert_rate(threshold):
    return max(0, 0.8 - 0.7 * threshold**1.2)  # Simplified function

# Calculate metrics for current threshold
sensitivity = get_sensitivity(threshold)
specificity = get_specificity(threshold)
alert_rate = get_alert_rate(threshold)

# Calculate workload impact
patients_per_day = beds / avg_stay
alerts_per_day = alert_rate * patients_per_day
hours_needed = alerts_per_day * minutes_per_alert / 60

# Display metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("Sensitivity", f"{sensitivity:.2f}")
col2.metric("Specificity", f"{specificity:.2f}")
col3.metric("Alerts per Day", f"{alerts_per_day:.1f}")
col4.metric("Staff Hours Needed", f"{hours_needed:.1f}")

# Staffing status
if hours_needed > staff_hours:
    st.error(f"⚠️ Alert burden exceeds available staff hours by {hours_needed - staff_hours:.1f} hours")
else:
    st.success(f"✅ Current threshold is feasible with {staff_hours - hours_needed:.1f} staff hours to spare")

# Generate data for charts
thresholds = np.arange(0.01, 1.0, 0.01)
sensitivities = [get_sensitivity(t) for t in thresholds]
specificities = [get_specificity(t) for t in thresholds]
alert_rates = [get_alert_rate(t) for t in thresholds]
hours_needed_range = [get_alert_rate(t) * patients_per_day * minutes_per_alert / 60 for t in thresholds]

# Prepare chart data
chart_data = pd.DataFrame({
    'Threshold': thresholds,
    'Sensitivity': sensitivities,
    'Specificity': specificities,
    'Alert Rate': alert_rates,
    'Hours Needed': hours_needed_range
})

# Display interactive charts
st.header("Performance Metrics vs. Threshold")

# Line chart for sensitivity/specificity
metrics_chart = alt.Chart(chart_data).transform_fold(
    ['Sensitivity', 'Specificity', 'Alert Rate'],
    as_=['Metric', 'Value']
).mark_line().encode(
    x=alt.X('Threshold:Q'),
    y=alt.Y('Value:Q', scale=alt.Scale(domain=[0, 1])),
    color='Metric:N',
    tooltip=['Threshold', 'Value']
).interactive()

st.altair_chart(metrics_chart, use_container_width=True)

# Workload chart
workload_chart = alt.Chart(chart_data).mark_line(color='red').encode(
    x=alt.X('Threshold:Q'),
    y=alt.Y('Hours Needed:Q'),
    tooltip=['Threshold', 'Hours Needed']
).interactive()

# Add a horizontal line for available staff
staff_line = alt.Chart(pd.DataFrame({'staff_hours': [staff_hours]})).mark_rule(color='green').encode(
    y='staff_hours'
)

st.altair_chart(workload_chart + staff_line, use_container_width=True)

# Find optimal thresholds
st.header("Recommended Thresholds")

# Maximum sensitivity within staff constraints
valid_thresholds = chart_data[chart_data['Hours Needed'] <= staff_hours]
if not valid_thresholds.empty:
    optimal_idx = valid_thresholds['Sensitivity'].idxmax()
    optimal_threshold = valid_thresholds.iloc[optimal_idx]['Threshold']
    st.success(f"Recommended threshold for maximum sensitivity: {optimal_threshold:.2f}")
    st.info(f"This gives sensitivity: {valid_thresholds.iloc[optimal_idx]['Sensitivity']:.2f}, " 
            f"requiring {valid_thresholds.iloc[optimal_idx]['Hours Needed']:.1f} staff hours")
else:
    st.error("No feasible threshold found within staff constraints.")
