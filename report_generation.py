import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from obspy import UTCDateTime
from obspy import read_events
from obspy.core.stream import read
from station_data import *
import cartopy.crs as ccrs
from event_detection import *

def read_catalogue_file(folder):
    catalogue = None
    provider = None

    # Define the keyword used to identify catalogue files
    keyword = 'catalogue'

    # Traverse through all files in the provided path
    for filename in os.listdir(folder):
        if keyword in filename and filename.endswith(
                '.xml'):  # Check for files matching the catalogue keyword and XML format
            file_path = os.path.join(folder, filename)

            # Extract the provider information from the filename assuming format 'YYYY-MM-DD_PROVIDER.catalogue.xml'
            parts = filename.split('_')
            if len(parts) > 1:
                provider = parts[1].split('.')[0]  # Extract the provider part from the filename

            if catalogue is None:
                catalogue = read_events(file_path)  # Read the first matching file as a catalogue
            else:
                # Merge subsequent catalogues into the initial one
                catalogue += read_events(file_path)

    if not catalogue:
        print(f"No catalogue files found containing '{keyword}'.")
    else:
        print(f"Loaded data from {file_path}")

    return catalogue, provider


def read_csv_from_path(path, date, station_information, identifier):
    network, station, _ = station_information
    date_str = date.strftime('%Y-%m-%d')
    filename = f"{date_str}.{identifier}.csv"
    file_path = os.path.join(path, filename)

    # Load the DataFrame from the specified CSV file
    df = pd.read_csv(file_path)
    print(f"Loaded data from {file_path}")
    return df


def read_stream_from_path(path, date, station_information, identifier):
    network, station, _ = station_information
    date_str = date.strftime('%Y-%m-%d')
    filename = f"{date_str}_{network}.{station}..Z.{identifier}.mseed"
    file_path = os.path.join(path, filename)

    # Load the Stream from the specified MiniSEED file
    stream = read(file_path)
    print(f"Loaded stream from {file_path}")
    return stream


def get_event_info(row):
    full_id = row.get('event_id', '')
    event_id = full_id.split('=')[-1] if '=' in full_id else None

    earthquake_info = {
        "time": row['time'],
        "lat": row['lat'],
        "long": row['long'],
        "mag": row['mag'],
        "mag_type": row['mag_type'],
        "P_peak_confidence": row.get('P_peak_confidence', None),
        "S_peak_confidence": row.get('S_peak_confidence', None),
        "epi_distance": row.get('epi_distance', None),
        "depth": row.get('depth', None),
        "event_id": event_id,
        "full_id": full_id,
        "detected_p_time": row.get('P_detected', ""),  # Correct syntax using .get()
        "detected_s_time": row.get('S_detected', ""),
        "predicted_p_time": row.get('P_predict', ""),
        "predicted_s_time": row.get('S_predict', "")
    }
    return earthquake_info


def plot_predictions_wave(stream, predictions, earthquake_info, path=None, show=False, save=False):
    def ensure_utc(time):
        """Ensure that the input time is a UTCDateTime object. Handles 'nan' and incorrect types."""
        if pd.isna(time):
            return None
        return UTCDateTime(time)

    # Extract times directly from earthquake_info
    detected_p_time = ensure_utc(earthquake_info.get('detected_p_time'))
    detected_s_time = ensure_utc(earthquake_info.get('detected_s_time'))
    predicted_p_time = ensure_utc(earthquake_info.get('predicted_p_time'))
    predicted_s_time = ensure_utc(earthquake_info.get('predicted_s_time'))

    # Use the earliest non-null prediction time for slicing if available
    start_times = [t for t in [predicted_p_time, detected_p_time] if t is not None]
    end_times = [t for t in [predicted_s_time, detected_s_time] if t is not None]
    starttime = min(start_times) - 60 if start_times else None
    endtime = max(end_times) + 60 if end_times else None

    if not starttime or not endtime:
        print("Invalid time range for slicing.")
        return

    trace = stream.slice(starttime=starttime, endtime=endtime)

    if not trace:
        print("No data in the trace.")
        return

    start_time = trace[0].stats.starttime
    end_time = trace[0].stats.endtime

    fig, ax = plt.subplots(2, 1, figsize=(13, 6), sharex=True, gridspec_kw={'hspace': 0.05, 'height_ratios': [1, 1]},
                           constrained_layout=True)

    color_dict = {"P": "C0", "S": "C1", "De": "#008000"}

    for pred_trace in predictions:
        model_name, pred_class = pred_trace.stats.channel.split("_")
        if pred_class == "N":
            continue  # Skip noise traces
        c = color_dict.get(pred_class, "black")  # Use black as default color if not found
        offset = pred_trace.stats.starttime - start_time
        ax[1].plot(offset + pred_trace.times(), pred_trace.data, label=pred_class, c=c)

    ax[1].set_ylabel("Prediction Confidence")
    ax[1].legend(loc=2)
    ax[1].set_ylim(0, 1.1)
    ax[0].plot(trace[0].times(), trace[0].data / np.amax(np.abs(trace[0].data)), 'k', label=trace[0].stats.channel)

    # Plotting detected and predicted arrival times
    times = [detected_p_time, detected_s_time, predicted_p_time, predicted_s_time]
    colors = ['C0', 'C1', 'C0', 'C1']
    styles = ['-', '-', '--', '--']
    labels = ['Detected P Arrival', 'Detected S Arrival', 'Predicted P Arrival', 'Predicted S Arrival']
    for t, color, style, label in zip(times, colors, styles, labels):
        if t:
            t_utc = UTCDateTime(t)
            ax[0].axvline(x=t_utc - start_time, color=color, linestyle=style, label=label, linewidth=0.8)

    ax[0].set_title(
        f'Earthquake on {earthquake_info["time"]} - Lat: {earthquake_info["lat"]}, Long: {earthquake_info["long"]} - Magnitude: {earthquake_info["mag"]}',
        fontsize=18)
    ax[0].set_ylabel('Normalized Amplitude')
    ax[1].set_xlabel('Time [s]')
    ax[0].set_xlim(0, end_time - start_time)
    ax[0].legend(loc='upper right')

    if show:
        plt.show()
    if save and path:
        file_path = os.path.join(path, f'annotation_{earthquake_info["event_id"]}.png')
        plt.savefig(file_path)
        print(f"Saved plot to {file_path}")
        plt.close()


def html_header(date_str):
    header = f"""
    <html>
    <head>
        <title>Earthquake Report for {date_str}</title>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .event {{ margin-bottom: 40px; }}
            .event img {{ width: 100%; max-width: 600px; }}
            .catalogue_plot img {{ width: 100%; max-width: 800px; }}
            .annotation_plot {{ width: 100% }}
            .statistics {{ margin-top: 5px; }}
            .section_title {{ font-weight: bold; color: #4793AF; font-size: 20px; }}
            .event_details {{  width: 800px; }}
            table {{border-collapse: collapse; font-size: 15px; width: 100%; }}

        </style>
    </head>
    <body>
        <h1>Earthquake Report for {date_str}</h1>
    """
    return header


def html_basic_info(network, station_code, catalogue_provider):
    html_content = f"""
        <p><strong>Station:</strong> {network}.{station_code}&nbsp;&nbsp;&nbsp;&nbsp;<strong>Catalogue Provider:</strong> {catalogue_provider}</p>

    """
    return html_content


def html_catalogue_map(catalog_image_filename):
    html_content = f"""
    <p class="section_title"><strong>Catalogued Events:</strong></p>
    <div class="catalogue_plot">
        <img src="{catalog_image_filename}" alt="Catalogue Overview Map">
    </div>
    """
    return html_content


def html_catalogue_list(df):
    catalogued_events = df[df['catalogued'] == True]

    list_items = []
    for index, event in catalogued_events.iterrows():
        # Highlight detected ones
        color_style = ' style="color: blue;"' if event['detected'] else ''
        list_items.append(
            f'<li{color_style}>{event["time"]} | {event["lat"]}, {event["long"]} | {event["mag"]} {event["mag_type"]}</li>')

    list_html = '\n'.join(list_items)

    html_content = f"""
    <div class="catalogue-list">
        <ul>
            {list_html}
        </ul>
    </div>

    """

    return html_content


def html_detected(df):
    number_catalogued, number_matched, number_not_detected, number_not_in_catalogue, number_both_phases_identified = calculate_matching_stats(df)
    total_detected = number_matched + number_not_in_catalogue

    html_content = f"""
    <div>
        <p class="section_title"><strong>Detected Events Statistics</strong></p>
        <p><strong>Total Events Detected:</strong> {total_detected}</p>
    </div>
    """
    return html_content


def html_matched_stats(df):
    number_catalogued, number_matched, number_not_detected, number_not_in_catalogue, number_both_phases_identified = calculate_matching_stats(df)

    detected_rate = (number_matched / number_catalogued * 100) if number_catalogued else 0

    html_content = f"""
    <div>
        <p><strong>Catalogued Events Detected:</strong> {number_matched} out of {number_catalogued}</p>
        <p><strong>Detected Rate:</strong> {detected_rate:.2f}%</p>
        <p><strong>Detected But Not Catalogued:</strong> {number_not_in_catalogue}</p>
    </div>

    """
    return html_content


def html_matched_info(events, catalogue_provider):
    html_parts = ['<p class="section_title"><strong>Details For Detected Catalogued Events:</strong></p>']

    for _, row in events.iterrows():
        event_info = get_event_info(row)
        image_filename = os.path.join(f"annotation_{event_info['event_id']}.png")
        event_html = f"""




        <div class="event_details">
        <img src="{image_filename}" alt="Earthquake Event {event_info['event_id']}" class="annotation_plot">
            <table class="statistics" border="1">
                <tr>
                    <td colspan="2">Event ID</td><td colspan="2">{catalogue_provider} {event_info['event_id']}</td>
                    <td colspan="2">Earthquake Time</td><td colspan="2">{event_info['time']}</td>
                </tr>
                <tr>
                    <td colspan="2">Location</td><td colspan="2">{event_info['lat']}, {event_info['long']}</td>
                    <td colspan="2">Distance to Station</td><td colspan="2">{event_info['epi_distance']:.2f} km</td>
                </tr>
                <tr>
                    <td colspan="2">Magnitude</td><td colspan="2">{event_info['mag']} {event_info['mag_type']}</td>
                    <td colspan="2">Depth</td><td colspan="2">{event_info['depth']} m</td>
                </tr>
                <tr>
                    <td colspan="2">Predicted P time</td><td colspan="2">{event_info.get('predicted_p_time', 'N/A')}</td>
                    <td colspan="2">Predicted S time</td><td colspan="2">{event_info.get('predicted_s_time', 'N/A')}</td>
                </tr>
                <tr>
                    <td colspan="2">Detected P time</td><td colspan="2">{event_info.get('detected_p_time', 'N/A')}</td>
                    <td colspan="2">Detected S time</td><td colspan="2">{event_info.get('detected_s_time', 'N/A')}</td>
                </tr>
                <tr>
                    <td colspan="2">Prediction confidence: P</td><td colspan="2">{event_info.get('P_peak_confidence', 'N/A')}</td>
                    <td colspan="2">Prediction confidence: S</td><td colspan="2">{event_info.get('S_peak_confidence', 'N/A')}</td>
                </tr>
            </table>
        </div>
        <br>
        <br>
"""

        html_parts.append(event_html)

    html_content = '\n'.join(html_parts)
    return html_content


def create_earthquake_report_html(df, file_path, date, station, catalogue_provider):
    matched_events = df[
        (df['catalogued'] == True) & (df['detected'] == True)]

    network, station_code, _ = station
    date_str = date.strftime('%Y-%m-%d')
    output_html_file = os.path.join(file_path, f"{date_str}_report.html")
    catalog_image_filename = f"catalogued_plot_{date_str}.png"  # Image file name for the catalogue plot

    header = html_header(date_str)
    basic_info = html_basic_info(network, station_code, catalogue_provider)
    catalogue_map = html_catalogue_map(catalog_image_filename)  # Call to add the catalogue map
    catalogue_list = html_catalogue_list(df)
    detected_events = html_detected(df)
    matched_stats = html_matched_stats(df)
    event_info = html_matched_info(matched_events, catalogue_provider)

    # Assemble all parts into the final HTML content
    html_content = f"{header}{basic_info}<hr>{catalogue_map}{catalogue_list}<hr>{detected_events}{matched_stats}<hr>{event_info}</body></html>"

    with open(output_html_file, 'w') as file:
        file.write(html_content)
    print(f"HTML report generated: {output_html_file}")

    return output_html_file
