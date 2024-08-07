import streamlit as st
from main import load_config

# Load default settings
default_config = load_config()

# Initialize or update session state variables from YAML
for key, value in default_config.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Page title
st.title("Settings")
st.divider()

# Settings Container
settings_container = st.container()
with settings_container:
    st.header("Settings")
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Station Settings", "Catalog Settings", "Stream Processing", "Event Detection", "Report Generation", "Email Settings"])

    # Station Settings Tab
    with tab1:
        network = st.text_input("Network:", value=st.session_state['network'])
        station_code = st.text_input("Station Code:", value=st.session_state['station_code'])
        data_provider_url = st.text_input("Data Provider URL:", value=st.session_state['data_provider_url'])
        overwrite = st.checkbox("Overwrite Existing Data", value=st.session_state['overwrite'])

    # Catalog Settings Tab
    with tab2:
        catalog_providers = st.text_input("Catalog Providers:", value=st.session_state['catalog_providers'])
        radmin = st.text_input("Minimum Radius:", value=st.session_state['radmin'])
        radmax = st.text_input("Maximum Radius:", value=st.session_state['radmax'])
        minmag = st.text_input("Minimum Magnitude:", value=st.session_state['minmag'])
        maxmag = st.text_input("Maximum Magnitude:", value=st.session_state['maxmag'])

    # Stream Processing Tab
    with tab3:
        col3, col4 = st.columns(2)
        # Process Stream Settings
        with col3:
            detrend_demean = st.checkbox("Detrend (Demean)", value=st.session_state['detrend_demean'])
            detrend_linear = st.checkbox("Detrend (Linear)", value=st.session_state['detrend_linear'])
            remove_outliers = st.checkbox("Remove Outliers", value=st.session_state['remove_outliers'])
            apply_bandpass = st.checkbox("Bandpass Filter", value=st.session_state['apply_bandpass'])
            taper = st.checkbox("Taper", value=st.session_state['taper'])
            denoise = st.checkbox("Denoise", value=st.session_state['denoise'])
            save_processed = st.checkbox("Save Processed Stream To File", value=st.session_state['save_processed'])

    # Event Detection Tab
    with tab4:
        # Detect Phases Settings
        with st.container():
            st.subheader("Phase Picking Settings")

            p_only = st.checkbox("Use Only P-waves", value=st.session_state['p_only'])
            col1, col2 = st.columns(2)
            with col1:
                p_threshold = st.slider("P Confidence Filtering Threshold", 0.0, 1.0, st.session_state['p_threshold'])
            with col2:
                s_threshold = st.slider("S Confidence Filtering Threshold", 0.0, 1.0, st.session_state['s_threshold'], disabled=p_only)
            save_annotated = st.checkbox("Save Annotated Stream", value=st.session_state['save_annotated'])

        st.markdown("<br><br>", unsafe_allow_html=True)

        # Match Events Settings
        with st.container():
            st.subheader("Event Matching Settings")
            col3, col4 = st.columns(2)
            with col3:
                tolerance_p = st.slider("P-Phase Matching Tolerance (s)", 0.0, 30.0, st.session_state['tolerance_p'])
            with col4:
                tolerance_s = st.slider("S-Phase Matching Tolerance (s)", 0.0, 30.0, st.session_state['tolerance_s'], disabled=p_only)
            save_results = st.checkbox("Save Matching Results", value=st.session_state['save_results'])

    # Report Generation Tab
    with tab5:
        st.subheader("Report Generation")

        simplified = st.checkbox("Simplified Report", value=st.session_state['simplified'])
        fill_map = st.checkbox("Fill Map Style For Catalog Plot", value=st.session_state['fill_map'])
        create_gif = st.checkbox("Create GIF For Catalog Plot", value=st.session_state['create_gif'])

    # Email Settings Tab
    with tab6:
        st.subheader("Email Settings")

        # 使用 st.columns 来调整输入框的宽度
        col1, _ = st.columns([3, 1])
        with col1:
            email_recipient = st.text_input("Recipient Email:", value=st.session_state['email_recipient'])

        st.markdown("<br><br>", unsafe_allow_html=True)

# Save Settings Container
save_settings_container = st.container()
with save_settings_container:
    col1, col2 = st.columns(2)
    if col1.button('Save Settings'):
        st.session_state.network = network
        st.session_state.station_code = station_code
        st.session_state.data_provider_url = data_provider_url
        st.session_state.catalog_providers = catalog_providers
        st.session_state.radmin = radmin
        st.session_state.radmax = radmax
        st.session_state.minmag = minmag
        st.session_state.maxmag = maxmag
        st.session_state.detrend_demean = detrend_demean
        st.session_state.detrend_linear = detrend_linear
        st.session_state.remove_outliers = remove_outliers
        st.session_state.apply_bandpass = apply_bandpass
        st.session_state.taper = taper
        st.session_state.denoise = denoise
        st.session_state.save_processed = save_processed
        st.session_state.p_only = p_only
        st.session_state.p_threshold = p_threshold
        st.session_state.s_threshold = s_threshold
        st.session_state.save_annotated = save_annotated
        st.session_state.tolerance_p = tolerance_p
        st.session_state.tolerance_s = tolerance_s
        st.session_state.save_results = save_results
        st.session_state.email_recipient = email_recipient
        st.session_state.overwrite = overwrite
        st.session_state.simplified = simplified
        st.session_state.fill_map = fill_map
        st.session_state.create_gif = create_gif

        # Refresh the page to avoid widget state conflict
        st.rerun()

    if col2.button('Reset Settings'):
        new_config = load_config()
        for key, value in new_config.items():
            st.session_state[key] = value
        st.rerun()
        st.success("Settings Reset to Default!")
