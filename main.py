import os

import streamlit as st

from catalog import Catalog
from report import Report

import os
import pandas as pd
from datetime import datetime
from station import Station


def read_total_events_summary(network, code, url, date=None):
    if date is None:
        date = datetime.today().strftime('%Y-%m-%d')

    # Construct the path to the 'total_events_summary.csv' file using os.getcwd() as the base directory
    base_dir = os.getcwd()
    station_folder = os.path.join(base_dir, "data", f"{network}.{code}")
    file_path = os.path.join(station_folder, 'total_events_summary.csv')

    # Read the CSV file into a DataFrame
    try:
        df = pd.read_csv(file_path)
        return df
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return None
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None


def download_station_data_logic(network, station_code, data_provider_url, report_date, overwrite):
    station = Station(network, station_code, data_provider_url, report_date)
    result = station.download_day_stream(overwrite=overwrite)
    status = result.get('status')

    if status == 'success' or status == 'exists':
        try:
            station.fetch_coordinates()
            coordinates_message = f"{station.latitude:.2f}, {station.longitude:.2f}"
        except Exception as e:
            coordinates_message = f"Failed to fetch coordinates: {str(e)}"

        stream_message = f"Stream downloaded for {report_date}." if status == 'success' else "Data already exists"
        return {
            'status': 'success',
            'data': station,
            'stream_message': stream_message,
            'location_message': coordinates_message
        }
    else:
        # Handle error or no data conditions
        error_message = result.get('message', 'No detailed error message available.')
        return {
            'status': 'fail',
            'message': f'Failed to download data. {error_message}'
        }


def process_stream_logic(station, detrend_demean, detrend_linear, remove_outliers, apply_bandpass, taper, denoise,
                         save_processed):
    station.stream.process_stream(
        detrend_demean=detrend_demean,
        detrend_linear=detrend_linear,
        remove_outliers=remove_outliers,
        apply_bandpass=apply_bandpass,
        taper=taper,
        denoise=denoise
    )
    if save_processed:
        station.stream.save_stream(station, stream_to_save=station.stream.processed_stream, identifier="processed")


def detect_phases_logic(station, p_threshold, s_threshold, p_only, save_annotated):
    station.stream.predict_and_annotate()
    station.stream.filter_confidence(p_threshold, s_threshold)
    p_count = sum(1 for pred in station.stream.picked_signals if pred['phase'] == 'P')
    s_count = sum(1 for pred in station.stream.picked_signals if pred['phase'] == 'S')

    if save_annotated:
        station.stream.save_stream(station, stream_to_save=station.stream.annotated_stream,
                                   identifier="processed.annotated")

    return station.stream.picked_signals, station.stream.annotated_stream, p_count, s_count


def download_catalogue_logic(station, radmin, radmax, minmag, maxmag, catalogue_providers):
    catalog = Catalog(station, radmin=radmin, radmax=radmax, minmag=minmag, maxmag=maxmag,
                      catalogue_providers=catalogue_providers)
    catalog.request_catalogue()
    if catalog.original_catalog_earthquakes:
        return catalog, f"Catalog downloaded from {catalog.provider}. Number of events: {len(catalog.original_catalog_earthquakes)}."
    else:
        return None, "Failed to download catalog data."


def match_events_logic(catalog, tolerance_p, tolerance_s, p_only, save_results):
    catalog.all_day_earthquakes = catalog.match_and_merge(
        catalog.station.stream.picked_signals,
        tolerance_p=tolerance_p,
        tolerance_s=tolerance_s,
        p_only=p_only
    )

    for eq in catalog.all_day_earthquakes:
        eq.update_errors()

    if save_results:
        catalog.save_results()

    # 直接使用 print_summary 方法获取结果
    detected_catalogued, detected_not_catalogued_count = catalog.print_summary()

    return detected_catalogued, detected_not_catalogued_count


def generate_report_logic(station, catalog, simplified, p_only, fill_map, create_gif):
    report = Report(station, catalog, simplified=simplified, p_only=p_only, fill_map=fill_map, create_gif=create_gif)
    report.construct_email()
    return report


def display_matched_earthquakes(catalog, simplified, p_only):
    st.subheader("Catalog Plot of All Earthquakes")
    st.image(catalog.catalog_plot_path)
    matched_earthquakes = [eq for eq in catalog.all_day_earthquakes if eq.detected and eq.catalogued]

    if matched_earthquakes:
        st.subheader("Matched Earthquakes Details")

        if len(matched_earthquakes) > 5:
            options = [eq.unique_id for eq in matched_earthquakes]
            selected_eq_id = st.selectbox("Select Earthquake", options)
            selected_earthquake = next(eq for eq in matched_earthquakes if eq.unique_id == selected_eq_id)
            earthquakes_to_display = [(None, selected_earthquake)]
        else:
            tabs = st.tabs([eq.unique_id for eq in matched_earthquakes])
            earthquakes_to_display = zip(tabs, matched_earthquakes)

        for tab, earthquake in earthquakes_to_display:
            container = tab if tab else st.container()
            with container:
                if earthquake.plot_path:
                    st.image(earthquake.plot_path)

                # First line: Time, Location, Magnitude
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**Time:** {earthquake.time.strftime('%Y-%m-%d %H:%M:%S')}")
                with col2:
                    st.write(f"**Location:** {float(earthquake.lat):.2f}, {float(earthquake.long):.2f}")
                with col3:
                    st.write(f"**Magnitude:** {float(earthquake.mag):.2f} {earthquake.mag_type}")

                if not simplified:
                    event_id_display = earthquake.event_id.split(':', 1)[
                        -1] if ':' in earthquake.event_id else earthquake.event_id
                    st.write(f"**Event ID:** {event_id_display}")

                # Second line: Distance, Depth, Unique ID
                col4, col5, col6 = st.columns(3)
                with col4:
                    st.write(f"**Epicentral Distance:** {float(earthquake.epi_distance):.2f} km")
                with col5:
                    st.write(f"**Depth:** {float(earthquake.depth):.2f} km")
                with col6:
                    st.write(f"**Unique ID:** {earthquake.unique_id}")

                # Third line: P Predicted, P Detected, P Error
                col7, col8, col9 = st.columns(3)
                with col7:
                    st.write(f"**P Predicted:** {earthquake.p_predicted.strftime('%Y-%m-%d %H:%M:%S')}")
                with col8:
                    st.write(f"**P Detected:** {earthquake.p_detected.strftime('%Y-%m-%d %H:%M:%S')}")
                with col9:
                    st.write(f"**P Error:** {earthquake.p_error}")

                # Fourth line: P Confidence (if not


def send_email_logic(report, email_recipient):
    report.send_email(email_recipient)
    return "Email sent successfully."


# Function to load settings from a YAML file
def load_config(filename='default_config.yaml'):
    import yaml
    with open(filename, 'r') as file:
        config = yaml.safe_load(file)
    # Convert list to comma-separated string for specific fields if necessary
    if 'catalog_providers' in config and isinstance(config['catalog_providers'], list):
        config['catalog_providers'] = ', '.join(config['catalog_providers'])
    return config


if __name__ == '__main__':
    # Load default settings
    default_config = load_config()

    # Step 1: Station Data Settings
    network = default_config['network']
    station_code = default_config['station_code']
    data_provider_url = default_config['data_provider_url']
    #report_date_str = default_config['report_date']
    report_date_str = '2024-03-03'
    overwrite = default_config['overwrite']

    # Download station data
    result = download_station_data_logic(network, station_code, data_provider_url, report_date_str, overwrite)
    if result['status'] == 'success':
        station = result['data']
        print("Station data downloaded successfully.")
        print("Stream Data Status:", result.get('stream_message', 'No stream message.'))
        print("Station Coordinate Status:", result.get('location_message', 'No location message.'))

        # Step 2: Catalog Data Settings
        catalog_providers = default_config['catalog_providers'].split(', ')
        radmin = default_config['radmin']
        radmax = default_config['radmax']
        minmag = default_config['minmag']
        maxmag = default_config['maxmag']

        # Download catalog data
        catalog, message = download_catalogue_logic(station, radmin, radmax, minmag, maxmag, catalog_providers)
        if not catalog:
            print(f"Failed to download catalog data: {message}")
        else:
            print(f"Catalog downloaded successfully. Number of events: {len(catalog.original_catalog_earthquakes)}")

            # Step 3: Process Stream Data
            detrend_demean = default_config['detrend_demean']
            detrend_linear = default_config['detrend_linear']
            remove_outliers = default_config['remove_outliers']
            apply_bandpass = default_config['apply_bandpass']
            taper = default_config['taper']
            denoise = default_config['denoise']
            save_processed = default_config['save_processed']

            # Process stream data
            process_stream_logic(station, detrend_demean, detrend_linear, remove_outliers, apply_bandpass, taper,
                                 denoise, save_processed)
            print("Stream processing completed and saved.")

            # Step 4: Detect Phases
            p_threshold = default_config['p_threshold']
            s_threshold = default_config['s_threshold']
            p_only = default_config['p_only']
            save_annotated = default_config['save_annotated']

            # Detect phases
            picked_signals, annotated_stream, p_count, s_count = detect_phases_logic(station, p_threshold, s_threshold,
                                                                                     p_only, save_annotated)
            print(f"P waves detected: {p_count}, S waves detected: {s_count}")

            # Step 5: Match Events
            tolerance_p = default_config['tolerance_p']
            tolerance_s = default_config['tolerance_s']
            save_results = default_config['save_results']

            # Match events
            summary = match_events_logic(catalog, tolerance_p, tolerance_s, p_only, save_results)
            print(summary)

            # Step 6: Generate Report
            simplified = default_config['simplified']
            fill_map = default_config['fill_map']
            create_gif = default_config['create_gif']

            # Generate report
            #report = generate_report_logic(station, catalog, simplified, p_only, fill_map, create_gif)
            #print("Report generated successfully.")

            # Step 7: Send Email
            #email_recipient = default_config['email_recipient']

            # Send email
            #result = send_email_logic(report, email_recipient)
            #print(result)
    else:
        print(f"Failed to download station data: {result['message']}")
