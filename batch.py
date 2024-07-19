import datetime
from main import load_config, download_station_data_logic, download_catalogue_logic, process_stream_logic, detect_phases_logic, match_events_logic
import time
if __name__ == '__main__':
    # Load default settings
    default_config = load_config()

    # Calculate the date range from January 1st of the current year to yesterday
    start_date = datetime.date(2024, 1, 1)
    end_date = datetime.date.today() - datetime.timedelta(days=1)

    current_date = start_date
    while current_date <= end_date:
        report_date_str = current_date.strftime('%Y-%m-%d')
        print(f"Processing data for {report_date_str}")

        # Step 1: Station Data Settings
        network = default_config['network']
        station_code = default_config['station_code']
        data_provider_url = default_config['data_provider_url']
        overwrite = default_config['overwrite']

        # Download station data
        result = download_station_data_logic(network, station_code, data_provider_url, report_date_str, overwrite)
        print(result['status'])
        if result['status'] == 'success' or result['status'] == 'exists':
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

        else:
            print(f"Failed to process data for {report_date_str}")

        # Move to the next day regardless of success or failure
        current_date += datetime.timedelta(days=1)
        print('Waiting 60 seconds before next day')
        time.sleep(60)


