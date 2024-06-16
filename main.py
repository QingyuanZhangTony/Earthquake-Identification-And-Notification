import datetime
from station import Station
from stream_processing import process_stream, denoise_stream, save_stream, taper_stream

from catalog import Catalog
from report import Report


def download_station_data_logic(network, station_code, data_provider_url, report_date):
    station = Station(network, station_code, data_provider_url, report_date)
    stream_file = station.download_stream_data(overwrite=False)
    if stream_file:
        try:
            station.fetch_coordinates()
            coordinates_message = f"Station coordinates fetched: {station.latitude}, {station.longitude}"
        except Exception as e:
            coordinates_message = f"Failed to fetch coordinates: {str(e)}"
        return station, f"Data downloaded successfully. {coordinates_message}"
    else:
        return None, "Failed to download data."


def process_stream_logic(station, detrend_demean, detrend_linear, remove_outliers, bandpass_filter, taper, denoise):
    processed_stream = process_stream(
        station.original_stream,
        detrend_demean=detrend_demean,
        detrend_linear=detrend_linear,
        remove_outliers=remove_outliers,
        bandpass_filter=bandpass_filter
    )
    if taper:
        processed_stream = taper_stream(processed_stream)
    station.processed_stream = processed_stream

    if denoise:
        processed_stream = denoise_stream(processed_stream)
    station.processed_stream = processed_stream


def detect_phases_logic(station, p_threshold, s_threshold, p_only):
    station.predict_and_annotate()
    station.filter_confidence(p_threshold, s_threshold)
    p_count = sum(1 for pred in station.picked_signals if pred['phase'] == 'P')
    s_count = sum(1 for pred in station.picked_signals if pred['phase'] == 'S')
    return station.picked_signals, station.annotated_stream, p_count, s_count


def download_catalogue_logic(station, radmin, radmax, minmag, maxmag, catalogue_providers):
    catalog = Catalog(station, radmin=radmin, radmax=radmax, minmag=minmag, maxmag=maxmag,
                      catalogue_providers=catalogue_providers)
    catalog.request_catalogue()
    if catalog.events:
        catalog.process_catalogue()
        return catalog, f"Catalog downloaded successfully from {catalog.provider} for {catalog.date.strftime('%Y-%m-%d')}. Number of events: {len(catalog.events)}."
    else:
        return None, "Failed to download catalog data."


def match_events_logic(catalog, tolerance_p, tolerance_s, p_only, save_results):
    catalog.processed_earthquakes = catalog.match_and_merge(
        catalog.station.picked_signals,
        tolerance_p=tolerance_p,
        tolerance_s=tolerance_s,
        p_only=p_only
    )
    for eq in catalog.processed_earthquakes:
        eq.update_errors()

    if save_results:
        catalog.save_results()


def generate_report_logic(station, catalog, simplified, p_only, fill_map, create_gif):
    report = Report(station, catalog, simplified=simplified, p_only=p_only, fill_map=fill_map, create_gif=create_gif)
    report.construct_email()
    return report


def send_email_logic(report, email_recipient):
    report.send_email(email_recipient)
    return "Email sent successfully."


if __name__ == '__main__':
    network = 'AM'
    station_code = 'R50D6'
    data_provider_url = 'https://data.raspberryshake.org'
    report_date = "2024-06-01"
    email_recipient = '891578348@qq.com'

    # Download Station Data
    station, message = download_station_data_logic(network, station_code, data_provider_url, report_date)
    print(message)

    if station:
        # Process Stream
        detrend_demean = True
        detrend_linear = True
        remove_outliers = True
        bandpass_filter = True
        taper = True
        denoise = True
        process_stream_logic(station, detrend_demean, detrend_linear, remove_outliers, bandpass_filter, taper, denoise)
        save_stream(station, station.processed_stream, "processed")
        print("Stream processing completed and saved.")

        # Detect Phases
        p_threshold = 0.7
        s_threshold = 1.0
        p_only = True
        picked_signals, annotated_stream, p_count, s_count = detect_phases_logic(station, p_threshold, s_threshold,
                                                                                 p_only)
        save_stream(station, station.annotated_stream, "processed.annotated")
        print(f"P waves detected: {p_count}, S waves detected: {s_count}")

        # Download Catalogue Data
        catalog_providers = ['IRIS', 'USGS', 'EMSC']
        radmin = 0.0
        radmax = 90.0
        minmag = 4.0
        maxmag = 10.0
        catalog, message = download_catalogue_logic(station, radmin, radmax, minmag, maxmag, catalog_providers)
        print(message)

        if catalog:
            # Match Events
            tolerance_p = 10.0
            tolerance_s = 0.0
            save_results = True  # 设置默认值
            match_events_logic(catalog, tolerance_p, tolerance_s, p_only, save_results)
            catalog.print_summary()

            # Generate Report
            simplified = False
            fill_map = True
            create_gif = True
            report = generate_report_logic(station, catalog, simplified, p_only, fill_map, create_gif)
            print("Report HTML generated successfully.")

            # Send Email
            result = send_email_logic(report, email_recipient)
            print(result)
