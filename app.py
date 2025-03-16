import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import altair as alt

# Set page configuration
st.set_page_config(
    page_title="Sepsis Alert Threshold Optimization",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add a title and description
st.title("🏥 Sepsis Alert Threshold Optimization Tool")
st.markdown("""
This tool helps clinicians and administrators optimize sepsis alert thresholds based on:
- Model performance metrics
- Clinical resource constraints
- Patient safety goals
""")

# Sidebar for parameters
st.sidebar.header("Clinical Setting Parameters")
beds = st.sidebar.number_input("Number of ICU beds", min_value=5, max_value=200, value=100)
avg_stay = st.sidebar.number_input("Average length of stay (days)", min_value=1.0, max_value=30.0, value=3.0, step=0.1)
minutes_per_alert = st.sidebar.number_input("Minutes to respond to each alert", min_value=1, max_value=60, value=10)
staff_hours = st.sidebar.number_input("Available staff hours per day", min_value=1, max_value=100, value=24)

# Additional settings in sidebar
st.sidebar.header("Model Settings")
sepsis_prevalence = st.sidebar.slider("Sepsis prevalence (%)", min_value=1, max_value=30, value=10) / 100

# Custom model performance - this would be replaced with your actual model data
st.sidebar.header("Advanced Settings")
advanced_settings = st.sidebar.expander("Customize Model Performance")
with advanced_settings:
    sen_exp = st.slider("Sensitivity curve exponent", 0.1, 2.0, 0.7, 0.1)
    spec_exp = st.slider("Specificity curve exponent", 0.1, 2.0, 0.6, 0.1)
    alert_exp = st.slider("Alert rate curve exponent", 0.1, 2.0, 1.2, 0.1)

# Model performance data (in a real app, this would come from your actual model)
# These functions simulate model performance curves
@st.cache_data
def get_sensitivity(threshold, exponent=0.7):
    return max(0, min(1, 1 - threshold**exponent))

@st.cache_data
def get_specificity(threshold, exponent=0.6):
    return min(1, max(0, 0.4 + 0.6 * threshold**exponent))

@st.cache_data
def get_alert_rate(threshold, exponent=1.2):
    # Expected alert rate considering both true and false positives
    return max(0, min(1, 0.8 - 0.7 * threshold**exponent))

# Main threshold control
st.header("Alert Threshold Configuration")
threshold = st.slider(
    "Set sepsis alert threshold", 
    min_value=0.0, 
    max_value=1.0, 
    value=0.5, 
    step=0.01,
    help="Higher thresholds result in fewer alerts but may miss some cases"
)

# Calculate metrics for current threshold
sensitivity = get_sensitivity(threshold, sen_exp)
specificity = get_specificity(threshold, spec_exp)
alert_rate = get_alert_rate(threshold, alert_exp)

# Calculate derived metrics
ppv = (sensitivity * sepsis_prevalence) / (sensitivity * sepsis_prevalence + (1 - specificity) * (1 - sepsis_prevalence))
npv = (specificity * (1 - sepsis_prevalence)) / ((1 - sensitivity) * sepsis_prevalence + specificity * (1 - sepsis_prevalence))

# Calculate workload impact
patients_per_day = beds / avg_stay
alerts_per_day = alert_rate * patients_per_day
hours_needed = alerts_per_day * minutes_per_alert / 60

# Display metrics in columns with formatted numbers
col1, col2, col3, col4 = st.columns(4)
col1.metric("Sensitivity", f"{sensitivity:.2f}", help="Proportion of sepsis cases detected")
col2.metric("Specificity", f"{specificity:.2f}", help="Proportion of non-sepsis cases correctly classified")
col3.metric("Alerts per Day", f"{alerts_per_day:.1f}", help="Expected number of alerts requiring response")
col4.metric("Staff Hours Needed", f"{hours_needed:.1f}", help="Clinical time required to respond to alerts")

# Additional metrics
col1, col2 = st.columns(2)
with col1:
    st.metric("Positive Predictive Value", f"{ppv:.2f}", help="Probability that a positive alert is a true sepsis case")
with col2:
    st.metric("Negative Predictive Value", f"{npv:.2f}", help="Probability that a negative result is truly non-sepsis")

# Staffing status
st.subheader("Staffing Analysis")
staffing_ratio = hours_needed / staff_hours
if hours_needed > staff_hours:
    st.error(f"⚠️ Alert burden exceeds available staff hours by {hours_needed - staff_hours:.1f} hours (Utilization: {staffing_ratio:.1%})")
elif staffing_ratio > 0.8:
    st.warning(f"⚠️ Alert burden using {staffing_ratio:.1%} of available staff hours ({hours_needed:.1f} of {staff_hours} hours)")
else:
    st.success(f"✅ Current threshold is feasible with {staff_hours - hours_needed:.1f} staff hours to spare (Utilization: {staffing_ratio:.1%})")

# Generate data for charts
thresholds = np.linspace(0.01, 0.99, 99)
sensitivities = [get_sensitivity(t, sen_exp) for t in thresholds]
specificities = [get_specificity(t, spec_exp) for t in thresholds]
alert_rates = [get_alert_rate(t, alert_exp) for t in thresholds]
hours_needed_range = [get_alert_rate(t, alert_exp) * patients_per_day * minutes_per_alert / 60 for t in thresholds]

# Calculate PPV and NPV across thresholds
ppvs = [(get_sensitivity(t, sen_exp) * sepsis_prevalence) / 
        (get_sensitivity(t, sen_exp) * sepsis_prevalence + (1 - get_specificity(t, spec_exp)) * (1 - sepsis_prevalence))
        for t in thresholds]

# Prepare chart data
chart_data = pd.DataFrame({
    'Threshold': thresholds,
    'Sensitivity': sensitivities,
    'Specificity': specificities,
    'Alert Rate': alert_rates,
    'PPV': ppvs,
    'Hours Needed': hours_needed_range
})

# Display interactive charts
st.header("Performance Metrics vs. Threshold")

# Select metrics to display
selected_metrics = st.multiselect(
    "Select metrics to display",
    options=['Sensitivity', 'Specificity', 'Alert Rate', 'PPV'],
    default=['Sensitivity', 'Specificity', 'Alert Rate']
)

if selected_metrics:
    # Line chart for selected metrics
    metrics_chart = alt.Chart(chart_data).transform_fold(
        selected_metrics,
        as_=['Metric', 'Value']
    ).mark_line().encode(
        x=alt.X('Threshold:Q', title='Threshold'),
        y=alt.Y('Value:Q', title='Value', scale=alt.Scale(domain=[0, 1])),
        color=alt.Color('Metric:N', legend=alt.Legend(title="Metrics")),
        tooltip=['Threshold', 'Value', 'Metric']
    ).properties(
        height=300
    ).interactive()

    # Add a vertical line for current threshold
    threshold_line = alt.Chart(pd.DataFrame({'threshold': [threshold]})).mark_rule(color='red').encode(
        x='threshold:Q'
    )

    st.altair_chart(metrics_chart + threshold_line, use_container_width=True)
else:
    st.info("Please select at least one metric to display")

# Workload chart
st.header("Clinical Workload Impact")
workload_chart = alt.Chart(chart_data).mark_area(
    color='red',
    opacity=0.3
).encode(
    x=alt.X('Threshold:Q', title='Threshold'),
    y=alt.Y('Hours Needed:Q', title='Staff Hours Required')
).properties(
    height=300
)

# Add a line for the workload
workload_line = alt.Chart(chart_data).mark_line(
    color='red'
).encode(
    x='Threshold:Q',
    y='Hours Needed:Q'
)

# Add a horizontal line for available staff
staff_line = alt.Chart(pd.DataFrame({'staff_hours': [staff_hours]})).mark_rule(
    color='green'
).encode(
    y='staff_hours:Q'
)

# Add annotation for staff hours
staff_text = alt.Chart(pd.DataFrame({'staff_hours': [staff_hours], 'x': [0.8]})).mark_text(
    align='left',
    baseline='bottom',
    dx=5,
    color='green'
).encode(
    x='x:Q',
    y='staff_hours:Q',
    text=alt.value(f'Available Staff Hours: {staff_hours}')
)

# Add a vertical line for current threshold
threshold_line = alt.Chart(pd.DataFrame({'threshold': [threshold]})).mark_rule(color='red').encode(
    x='threshold:Q'
)

st.altair_chart(workload_chart + workload_line + staff_line + staff_text + threshold_line, use_container_width=True)

# Find optimal thresholds
st.header("Threshold Recommendations")

# Maximum sensitivity within staff constraints
valid_thresholds = chart_data[chart_data['Hours Needed'] <= staff_hours]
if not valid_thresholds.empty:
    # Create three columns for different optimization goals
    col1, col2, col3 = st.columns(3)
    
    # 1. Optimize for sensitivity
    with col1:
        st.subheader("Maximize Sensitivity")
        optimal_idx = valid_thresholds['Sensitivity'].idxmax()
        optimal_threshold = valid_thresholds.iloc[optimal_idx]['Threshold']
        st.success(f"Threshold: {optimal_threshold:.2f}")
        st.write(f"Sensitivity: {valid_thresholds.iloc[optimal_idx]['Sensitivity']:.2f}")
        st.write(f"Specificity: {valid_thresholds.iloc[optimal_idx]['Specificity']:.2f}")
        st.write(f"Staff Hours: {valid_thresholds.iloc[optimal_idx]['Hours Needed']:.1f}")
    
    # 2. Optimize for balanced performance (Youden's J = Sensitivity + Specificity - 1)
    with col2:
        st.subheader("Balanced Performance")
        valid_thresholds['Youden_J'] = valid_thresholds['Sensitivity'] + valid_thresholds['Specificity'] - 1
        balanced_idx = valid_thresholds['Youden_J'].idxmax()
        balanced_threshold = valid_thresholds.iloc[balanced_idx]['Threshold']
        st.success(f"Threshold: {balanced_threshold:.2f}")
        st.write(f"Sensitivity: {valid_thresholds.iloc[balanced_idx]['Sensitivity']:.2f}")
        st.write(f"Specificity: {valid_thresholds.iloc[balanced_idx]['Specificity']:.2f}")
        st.write(f"Staff Hours: {valid_thresholds.iloc[balanced_idx]['Hours Needed']:.1f}")
    
    # 3. Optimize for minimal staffing while maintaining reasonable sensitivity
    with col3:
        st.subheader("Resource Efficient")
        # Find thresholds with at least 0.7 sensitivity
        min_sensitivity = 0.7
        efficient_thresholds = valid_thresholds[valid_thresholds['Sensitivity'] >= min_sensitivity]
        
        if not efficient_thresholds.empty:
            efficient_idx = efficient_thresholds['Hours Needed'].idxmin()
            efficient_threshold = efficient_thresholds.iloc[efficient_idx]['Threshold']
            st.success(f"Threshold: {efficient_threshold:.2f}")
            st.write(f"Sensitivity: {efficient_thresholds.iloc[efficient_idx]['Sensitivity']:.2f}")
            st.write(f"Specificity: {efficient_thresholds.iloc[efficient_idx]['Specificity']:.2f}")
            st.write(f"Staff Hours: {efficient_thresholds.iloc[efficient_idx]['Hours Needed']:.1f}")
        else:
            st.error(f"No threshold with sensitivity ≥{min_sensitivity} is feasible")
else:
    st.error("No feasible threshold found within staff constraints. Consider increasing available staff hours.")

# Additional information and explanations
with st.expander("How to Use This Tool"):
    st.markdown("""
    ### Instructions:
    1. Set your clinical parameters in the sidebar (beds, staff, etc.)
    2. Adjust the threshold slider to see the impact on performance metrics
    3. Review the recommended thresholds based on different optimization goals
    4. Check the staffing analysis to ensure the selected threshold is feasible
    
    ### Key Concepts:
    - **Sensitivity**: Percentage of sepsis cases that trigger an alert (higher = fewer missed cases)
    - **Specificity**: Percentage of non-sepsis cases that don't trigger an alert (higher = fewer false alarms)
    - **PPV**: Positive Predictive Value - probability that an alert represents true sepsis
    - **Alert Rate**: Percentage of patients who will trigger an alert
    - **Staff Hours**: Clinical time required to respond to all alerts
    
    ### Optimization Goals:
    - **Maximize Sensitivity**: Catches as many sepsis cases as possible, but may increase workload
    - **Balanced Performance**: Best trade-off between sensitivity and specificity
    - **Resource Efficient**: Minimizes workload while maintaining acceptable sensitivity
    """)

# Footer
st.markdown("---")
st.markdown("© 2025 Multi-modal Deep Learning for Early Sepsis Prediction")
