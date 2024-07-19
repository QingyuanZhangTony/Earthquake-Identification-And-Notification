import streamlit as st
import datetime
from io import BytesIO
import matplotlib.pyplot as plt
import plotly.express as px

import plotly.graph_objects as go

import pandas as pd
import matplotlib.colors as mcolors
from main import download_station_data_logic, process_stream_logic, detect_phases_logic, download_catalogue_logic, \
    match_events_logic, generate_report_logic, send_email_logic, display_matched_earthquakes

config = {
    'report_date': '2024-04-23'
}

# Initialize state variables
# Station Data
if 'station_downloaded' not in st.session_state:
    st.session_state.station_downloaded = False
if 'is_downloading' not in st.session_state:
    st.session_state.is_downloading = False

# Catalog Data
if 'catalog_downloaded' not in st.session_state:
    st.session_state.catalog_downloaded = False
if 'is_catalog_downloading' not in st.session_state:
    st.session_state.is_catalog_downloading = False
if 'event_count' not in st.session_state:
    st.session_state.event_count = 0
if 'catalog_provider' not in st.session_state:
    st.session_state.catalog_provider = "Not Downloaded"

if 'selected_projection' not in st.session_state:
    st.session_state.selected_projection = "local"

# Process Stream Data
if 'stream_processed' not in st.session_state:
    st.session_state.stream_processed = False
if 'is_processing' not in st.session_state:
    st.session_state.is_processing = False

# Detect Phases
if 'phases_detected' not in st.session_state:
    st.session_state.phases_detected = False
if 'is_detecting' not in st.session_state:
    st.session_state.is_detecting = False
if 'p_count' not in st.session_state:
    st.session_state.p_count = 0
if 's_count' not in st.session_state:
    st.session_state.s_count = 0

# Match Events
if 'matching_completed' not in st.session_state:
    st.session_state.matching_completed = False
if 'is_matching' not in st.session_state:
    st.session_state.is_matching = False
if 'matching_summary' not in st.session_state:
    st.session_state.matching_summary = ""

# Generate Report
if 'report_generated' not in st.session_state:
    st.session_state.report_generated = False
if 'is_generating_report' not in st.session_state:
    st.session_state.is_generating_report = False

# Send Email
if 'email_sent' not in st.session_state:
    st.session_state.email_sent = False
if 'is_sending_email' not in st.session_state:
    st.session_state.is_sending_email = False

# Application Title
st.title("Daily Earthquake Identification")

# Station Data Container
station_settings_container = st.container()
with station_settings_container:
    st.header("Station Data")
    '''This step downloads stream data and fetch station location.'''
    col1, col2 = st.columns([3, 2])

    with col1:
        report_date = st.date_input("Report Date:",
                                    value=datetime.datetime.strptime(config['report_date'], '%Y-%m-%d'))

        # Make the button display 'Downloading' and make it unclickable before download is finished
        proceed_button = st.button('Download Station Data' if not st.session_state.is_downloading else 'Downloading...',
                                   key='proceed_station', disabled=st.session_state.is_downloading)

    with col2:
        st.subheader("Status")

        # Metrics showing station data status
        if st.session_state.station_downloaded:
            latitude = f"{st.session_state.global_station.latitude:.2f}"
            longitude = f"{st.session_state.global_station.longitude:.2f}"
            st.metric(label="Stream Data", value=st.session_state.stream_message)
            st.metric(label="Station Coordinate", value=st.session_state.location_message)
        else:
            st.metric(label="Stream Data", value="Not Downloaded")
            st.metric(label="Station Coordinate", value="Not Fetched")

    if proceed_button:
        st.session_state.is_downloading = True
        st.rerun()

    if st.session_state.is_downloading:
        report_date_str = report_date.strftime('%Y-%m-%d')
        st.session_state.report_date = report_date
        result = download_station_data_logic(st.session_state.network, st.session_state.station_code,
                                             st.session_state.data_provider_url, report_date_str,
                                             st.session_state.overwrite)

        if result['status'] == 'success':
            st.session_state.global_station = result['data']
            st.session_state.station_downloaded = True
            st.session_state.stream_message = result['stream_message']
            st.session_state.location_message = result['location_message']
        else:
            st.session_state.station_downloaded = False
            st.session_state.stream_message = result['message']
            st.session_state.location_message = result['message']

        st.session_state.is_downloading = False
        st.rerun()

    # Plotting the original stream if station data is downloaded
    if st.session_state.station_downloaded:
        st.subheader("Original Stream")
        original_stream_plot = BytesIO()
        st.session_state.global_station.stream.original_stream.plot(outfile=original_stream_plot, format='png')
        original_stream_plot.seek(0)
        st.image(original_stream_plot)
        st.session_state.original_stream_plot_buf = original_stream_plot
st.divider()

# Catalog Data Container
catalog_settings_container = st.container()
with catalog_settings_container:
    st.header("Catalog Data")
    '''This step requests earthquake catalog from the specified providers.'''
    col1, col2 = st.columns([3, 2])

    with col1:
        # Streamlit session state initialization if needed
        if 'is_catalog_downloading' not in st.session_state:
            st.session_state.is_catalog_downloading = False
        if 'catalog_provider' not in st.session_state:
            st.session_state.catalog_provider = "Not Downloaded"
        if 'event_count' not in st.session_state:
            st.session_state.event_count = 0

        proceed_button_catalog = st.button(
            'Download Catalog' if not st.session_state.is_catalog_downloading else 'Downloading...',
            key=f"proceed_catalog_{st.session_state.is_catalog_downloading}",
            disabled=st.session_state.is_catalog_downloading)

    with col2:
        st.subheader("Status")
        if st.session_state.catalog_downloaded:
            st.metric(label="Catalog Provider", value=st.session_state.catalog_provider)
            st.metric(label="Events Downloaded", value=st.session_state.event_count)
        else:
            st.metric(label="Catalog Provider", value="Not Requested")
            st.metric(label="Events Downloaded", value="Not Downloaded")

    if proceed_button_catalog and st.session_state.global_station:
        st.session_state.is_catalog_downloading = True
        st.rerun()

    if st.session_state.is_catalog_downloading:
        catalog_providers_list = [provider.strip() for provider in st.session_state.catalog_providers.split(',')]
        radmin = float(st.session_state.radmin)
        radmax = float(st.session_state.radmax)
        minmag = float(st.session_state.minmag)
        maxmag = float(st.session_state.maxmag)

        catalog, message = download_catalogue_logic(st.session_state.global_station, radmin, radmax, minmag, maxmag,
                                                    catalog_providers_list)
        if catalog:
            st.session_state.global_catalog = catalog
            st.session_state.catalog_downloaded = True
            st.session_state.event_count = len(catalog.original_catalog_earthquakes)
            st.session_state.catalog_provider = catalog.provider
        else:
            st.session_state.catalog_downloaded = False
            st.session_state.event_count = 0
            st.session_state.catalog_provider = "Not Downloaded"
        st.session_state.is_catalog_downloading = False
        st.rerun()

    # Add map
    if st.session_state.catalog_downloaded:
        st.subheader("Catalog Visualization")
        tab1, tab2 = st.tabs(["Static Plot", "Interactive Map"])

        with tab1:
            # Dropdown for choosing projection type
            projection_type = st.selectbox("Choose Projection Type", ['local', 'ortho', 'global'])
            if 'catalog_static_plot_buf' not in st.session_state or st.session_state.selected_projection != projection_type:
                st.session_state.selected_projection = projection_type
                catalog_static_plot = BytesIO()
                # Assume original_catalog.plot is a method that can take projection type as an argument
                st.session_state.global_catalog.original_catalog.plot(projection=projection_type,
                                                                      outfile=catalog_static_plot, format='png')
                catalog_static_plot.seek(0)
                st.session_state.catalog_static_plot_buf = catalog_static_plot

            if 'catalog_static_plot_buf' in st.session_state:
                st.image(st.session_state.catalog_static_plot_buf, caption=f"{projection_type} Projection")

        with tab2:
            fig = st.session_state.global_catalog.plot_interactive_map()
            if fig:
                st.plotly_chart(fig)
st.divider()

# Process Stream Container
process_stream_container = st.container()
with process_stream_container:
    st.header("Process Stream Data")
    '''This step performs stream signal processing. CUDA will be utilized for DeepDenoiser if available.'''
    col1, col2 = st.columns([3, 2])

    with col1:
        st.subheader("Settings")

        if 'is_processing' not in st.session_state:
            st.session_state.is_processing = False

        # 在按下按钮时将按钮文本变为“Processing...”并禁用按钮
        proceed_button_process = st.button('Process Stream' if not st.session_state.is_processing else 'Processing...',
                                           key='proceed_process', disabled=st.session_state.is_processing)

    with col2:
        st.subheader("Status")

        # 显示处理状态的 Metrics
        if not st.session_state.station_downloaded:
            st.metric(label="Stream Data", value="Not Processed")
        elif st.session_state.stream_processed:
            st.metric(label="Stream Processing", value="Completed")
        else:
            st.metric(label="Stream Processing", value="Not Done")

    if proceed_button_process and st.session_state.global_station:
        st.session_state.is_processing = True
        st.rerun()  # 刷新页面以显示“Processing...”并禁用按钮

    if st.session_state.is_processing:
        process_stream_logic(st.session_state.global_station, st.session_state.detrend_demean,
                             st.session_state.detrend_linear, st.session_state.remove_outliers,
                             st.session_state.apply_bandpass, st.session_state.taper, st.session_state.denoise,
                             st.session_state.save_processed)
        st.session_state.stream_processed = True

        # 保存绘图数据以便后续重新绘制
        img_buf_processed = BytesIO()
        st.session_state.global_station.stream.processed_stream.plot(outfile=img_buf_processed, format='png')
        img_buf_processed.seek(0)
        st.session_state.img_buf_processed = img_buf_processed

        st.session_state.is_processing = False
        st.rerun()  # 处理完成后刷新页面以恢复按钮文本和启用按钮

    # 绘制处理后的流数据图表
    if 'img_buf_processed' in st.session_state:
        st.subheader("Processed Stream")
        st.image(st.session_state.img_buf_processed)
st.divider()

# Detect Phases Container
detect_phases_container = st.container()
with detect_phases_container:
    st.header("Detect Phases")
    '''This step will detect P/S waves from the stream. CUDA will be utilized for phase picking if available.'''
    col1, col2 = st.columns([3, 2])

    with col1:
        if 'is_detecting' not in st.session_state:
            st.session_state.is_detecting = False

        proceed_button_detect = st.button(
            'Proceed with Detection' if not st.session_state.is_detecting else 'Detecting...', key='proceed_detect',
            disabled=st.session_state.is_detecting)

    with col2:
        st.subheader("Status")
        # Display metrics
        if st.session_state.phases_detected:
            st.metric(label="P waves detected", value=st.session_state.p_count)
            if not st.session_state.p_only:
                st.metric(label="S waves detected", value=st.session_state.s_count)
        else:
            st.metric(label="P waves detected", value="Not Completed")
            if not st.session_state.p_only:
                st.metric(label="S waves detected", value="Not Completed")

    if proceed_button_detect and st.session_state.global_station:
        st.session_state.is_detecting = True
        st.rerun()  # 刷新页面以显示“Detecting...”并禁用按钮

    if st.session_state.is_detecting:
        picked_signals, annotated_stream, p_count, s_count = detect_phases_logic(st.session_state.global_station,
                                                                                 st.session_state.p_threshold,
                                                                                 st.session_state.s_threshold,
                                                                                 st.session_state.p_only,
                                                                                 st.session_state.save_annotated)
        st.session_state.phases_detected = True
        st.session_state.p_count = p_count
        st.session_state.s_count = s_count

        st.session_state.is_detecting = False
        st.rerun()  # 检测完成后刷新页面以恢复按钮文本和启用按钮
st.divider()

# Match Events Container
match_events_container = st.container()
with match_events_container:
    st.header("Match Events")
    '''This step matches detected P/S waves with the earthquakes from the catalog.'''
    col1, col2 = st.columns([3, 2])

    with col1:
        if 'is_matching' not in st.session_state:
            st.session_state.is_matching = False

        proceed_button_match = st.button('Proceed with Matching' if not st.session_state.is_matching else 'Matching...',
                                         key='proceed_match', disabled=st.session_state.is_matching)

    with col2:
        st.subheader("Status")
        if st.session_state.matching_completed:
            st.metric(label="Catalogued earthquakes detected", value=st.session_state.detected_catalogued)
            st.metric(label="Detected earthquakes not catalogued", value=st.session_state.detected_not_catalogued_count)
        else:
            st.metric(label="Catalogued earthquakes detected", value="Not Completed")
            st.metric(label="Detected earthquakes not catalogued", value="Not Completed")

    if proceed_button_match and st.session_state.global_catalog and st.session_state.phases_detected:
        st.session_state.is_matching = True
        st.rerun()  # 刷新页面以显示“Matching...”并禁用按钮

    if st.session_state.is_matching:
        # Reset the matching state
        st.session_state.matching_completed = False
        st.session_state.detected_catalogued = 0
        st.session_state.detected_not_catalogued_count = 0

        detected_catalogued, detected_not_catalogued_count = match_events_logic(
            st.session_state.global_catalog,
            st.session_state.tolerance_p,
            st.session_state.tolerance_s if 'tolerance_s' in locals() else 0.0,
            st.session_state.p_only,
            st.session_state.save_results
        )
        st.session_state.matching_completed = True
        st.session_state.detected_catalogued = detected_catalogued
        st.session_state.detected_not_catalogued_count = detected_not_catalogued_count

        st.session_state.is_matching = False
        st.rerun()  # 匹配完成后刷新页面以恢复按钮文本和启用按钮
st.divider()

# Generate Report Container
generate_report_container = st.container()
with generate_report_container:
    st.header("Generate Report")
    '''This step generates detailed report for successfully matched earthquakes.'''
    col1, col2 = st.columns([3, 2])

    with col1:
        if 'is_generating_report' not in st.session_state:
            st.session_state.is_generating_report = False

        proceed_button_report = st.button(
            'Generate Report' if not st.session_state.is_generating_report else 'Generating...',
            key='proceed_report', disabled=st.session_state.is_generating_report)

    with col2:
        st.subheader("Status")

        if st.session_state.report_generated:
            st.metric(label="Report", value="Generated Successfully")
        else:
            st.metric(label="Report", value="Not Generated")

    if proceed_button_report:
        st.session_state.is_generating_report = True
        st.rerun()

    if st.session_state.is_generating_report:
        if not st.session_state.global_station:
            st.session_state.report_status_message = "Station data not available. Please complete the station data step first."
            st.session_state.is_generating_report = False
        elif not st.session_state.global_catalog:
            st.session_state.report_status_message = "Catalog data not available. Please complete the catalog data step first."
            st.session_state.is_generating_report = False
        elif not st.session_state.matching_completed:
            st.session_state.report_status_message = "Event matching not completed. Please complete the event matching step first."
            st.session_state.is_generating_report = False
        else:
            st.session_state.report_status_message = "Generating Report..."
            report = generate_report_logic(st.session_state.global_station, st.session_state.global_catalog,
                                           st.session_state.simplified, st.session_state.p_only,
                                           st.session_state.fill_map, st.session_state.create_gif)
            st.session_state.global_report = report
            st.session_state.report_generated = True
            st.session_state.report_status_message = "Report Generated Successfully"

            # Display matched earthquakes information and plots
            display_matched_earthquakes(st.session_state.global_catalog, st.session_state.simplified,
                                        st.session_state.p_only)

        st.session_state.is_generating_report = False
        st.rerun()

    if st.session_state.report_generated:
        display_matched_earthquakes(st.session_state.global_catalog, st.session_state.simplified,
                                    st.session_state.p_only)

st.divider()

# Send Email Container
send_email_container = st.container()
with send_email_container:
    st.header("Send Report")
    '''This step will send the generated report via Email.'''
    col1, col2 = st.columns([3, 2])

    with col1:
        st.subheader("Settings")
        if 'is_sending_email' not in st.session_state:
            st.session_state.is_sending_email = False

        proceed_button_email = st.button('Send Email' if not st.session_state.is_sending_email else 'Sending...',
                                         key='proceed_email', disabled=st.session_state.is_sending_email)

    with col2:
        st.subheader("Status")

        # Display email status in metrics
        if st.session_state.email_sent:
            st.metric(label="Email Status", value="Sent Successfully")
        else:
            st.metric(label="Email Status", value="Not Sent")

    if proceed_button_email and st.session_state.global_report:
        st.session_state.is_sending_email = True
        st.rerun()  # Refresh page to show "Sending..." and disable button

    if st.session_state.is_sending_email:
        email_result = send_email_logic(st.session_state.global_report, st.session_state.email_recipient)
        if email_result == "Email sent successfully.":
            st.session_state.email_sent = True
        else:
            st.session_state.email_sent = False

        st.session_state.is_sending_email = False
        st.rerun()  # Refresh page to restore button text and enable button
st.divider()
