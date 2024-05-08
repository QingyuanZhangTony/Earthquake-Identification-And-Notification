import os
from datetime import datetime

import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.legend_handler import HandlerLine2D
from obspy import UTCDateTime, read
from obspy import read_events

from event_detection import calculate_matching_stats


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
        print(f"Loaded catalogue from {file_path}")

    return catalogue, provider


def read_csv_from_path(path, date, station_information, identifier):
    network, station, _ = station_information
    date_str = date.strftime('%Y-%m-%d')
    filename = f"{date_str}.{identifier}.csv"
    file_path = os.path.join(path, filename)

    # Load the DataFrame from the specified CSV file
    df = pd.read_csv(file_path)
    print(f"Loaded csv from {file_path}")
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
        "depth": row.get('depth', None) / 1000,
        "event_id": event_id,
        "full_id": full_id,
        "detected_p_time": row.get('P_detected', ""),  # Correct syntax using .get()
        "detected_s_time": row.get('S_detected', ""),
        "predicted_p_time": row.get('P_predict', ""),
        "predicted_s_time": row.get('S_predict', ""),
        "p_time_error": row.get('P_error', ""),
        "s_time_error": row.get('S_error', ""),
    }
    return earthquake_info


def plot_predictions_wave(stream, predictions, earthquake_info, path=None, show=True):
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

    # Calculate the time range for slicing the stream
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

    # Create subplots for visualizing the seismic data and predictions
    fig, axes = plt.subplots(3, 1, figsize=(13, 9), sharex=True,
                             gridspec_kw={'hspace': 0.04, 'height_ratios': [1, 1, 1]},
                             constrained_layout=True)

    color_dict = {"P": "C0", "S": "C1", "De": "#008000"}

    # First subplot: Normalized Waveform Plot
    axes[0].plot(trace[0].times(), trace[0].data / np.amax(np.abs(trace[0].data)), 'k', label=trace[0].stats.channel)
    axes[0].set_ylabel('Normalized Amplitude')

    # Second subplot: Prediction Confidence Plot
    for pred_trace in predictions:
        model_name, pred_class = pred_trace.stats.channel.split("_")
        if pred_class == "N":
            continue  # Skip noise traces
        c = color_dict.get(pred_class, "black")  # Use black as default color if not found
        offset = pred_trace.stats.starttime - start_time
        label = "Detection" if pred_class == "De" else pred_class  # Change "De" to "Detection"
        axes[1].plot(offset + pred_trace.times(), pred_trace.data, label=label, c=c)
    axes[1].set_ylabel("Prediction Confidence")
    axes[1].legend(loc='upper right')
    axes[1].set_ylim(0, 1.1)

    # Third subplot: Spectrogram
    fs = trace[0].stats.sampling_rate
    axes[2].specgram(trace[0].data, NFFT=1024, Fs=fs, noverlap=512, cmap='viridis')
    axes[2].set_ylabel('Frequency [Hz]')
    axes[2].set_xlabel('Time [s]')

    # Add markers for detected and predicted seismic phases
    times = [detected_p_time, detected_s_time, predicted_p_time, predicted_s_time]
    colors = ['C0', 'C1', 'C0', 'C1']
    styles = ['-', '-', '--', '--']
    labels = ['Detected P Arrival', 'Detected S Arrival', 'Predicted P Arrival', 'Predicted S Arrival']
    for ax in axes[:-1]:  # Loop through the first two axes to add lines
        for t, color, style, label in zip(times, colors, styles, labels):
            if t:
                t_utc = UTCDateTime(t)
                ax.axvline(x=t_utc - start_time, color=color, linestyle=style, label=label, linewidth=0.8)

    # Title
    event_time = UTCDateTime(earthquake_info["time"]).strftime('%Y-%m-%d %H:%M:%S.%f')[:-4]
    axes[0].set_title(
        f'Detection of Event {event_time} - Lat: {earthquake_info["lat"]}, Long: {earthquake_info["long"]} - Magnitude: {earthquake_info["mag"]} {earthquake_info["mag_type"]}',
        fontsize=18)
    axes[0].set_xlim(0, end_time - start_time)

    # Values for x-axis
    x_ticks = np.arange(0, end_time - start_time + 1, 60)
    x_labels = [(start_time + t).strftime('%H:%M:%S.%f')[:-4] for t in x_ticks]  # 秒精确到小数点后两位
    for ax in axes:
        ax.set_xticks(x_ticks)
        ax.set_xticklabels(x_labels, rotation=0)  # 让坐标水平显示

    # Add all labels to the legend
    handles, labels = axes[0].get_legend_handles_labels()
    axes[0].legend(handles, labels, loc='upper right')

    # Save the figure in all cases
    if path:
        file_path = os.path.join(path, f'annotation_{earthquake_info["event_id"]}.png')
        plt.savefig(file_path)
        if not show:
            print(f"Saved plot to {file_path}")

    # Show the figure if show is True
    if show:
        plt.show()

    plt.close()


# Produce a world map with all catalogued events and station
def plot_catalogue(df, station_information, station_coordinates, catalogue_date, fill_map=False, path=None, show=True):
    network, station, data_provider = station_information
    try:
        latitude, longitude = station_coordinates
        valid_coordinates = True
    except Exception:
        valid_coordinates = False  # Failed to get coordinates

    fig, ax = plt.subplots(figsize=(10, 7), subplot_kw={
        'projection': ccrs.PlateCarree(central_longitude=longitude if valid_coordinates else 0)
    })
    ax.set_global()
    ax.coastlines()

    if fill_map:
        ax.stock_img()
        cmap = plt.get_cmap('autumn')
        station_color = '#7F27FF'
        marker_color = '#FAA300'
    else:
        cmap = plt.get_cmap('viridis')
        station_color = '#F97300'
        marker_color = '#135D66'

    if valid_coordinates:
        ax.plot(longitude, latitude, marker='^', color=station_color, markersize=16, linestyle='None',
                transform=ccrs.Geodetic(), label=f'Station {station}')

    norm = plt.Normalize(1, 10)

    # Custom markers for the legend
    detected_marker = plt.Line2D([], [], color=marker_color, marker='s', markersize=10, linestyle='None',
                                 markeredgecolor='white')
    undetected_marker = plt.Line2D([], [], color=marker_color, marker='o', markersize=10, linestyle='None',
                                   markeredgecolor='white')
    station_marker = plt.Line2D([], [], color=station_color, marker='^', markersize=10, linestyle='None',
                                markeredgecolor='white')

    # Process each event in the DataFrame
    detected_count = 0
    undetected_count = 0
    for index, event in df.iterrows():
        if event['catalogued'] and pd.notna(event['lat']) and pd.notna(event['long']) and pd.notna(event['mag']):
            color = cmap(norm(event['mag']))
            marker = 's' if event.get('detected', False) else 'o'  # Square if detected, circle otherwise
            if event.get('detected', False):
                detected_count += 1
            else:
                undetected_count += 1
            ax.plot(event['long'], event['lat'], marker=marker, color=color, markersize=10, markeredgecolor='white',
                    transform=ccrs.Geodetic())

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, orientation='vertical', pad=0.02, aspect=32.5, fraction=0.015, shrink=0.9)
    cbar.set_label('Magnitude')

    title_date = catalogue_date.strftime('%Y-%m-%d')
    title = f"Catalogued Event for Station {network}.{station} on {title_date}"
    plt.title(title, fontsize=15)

    # Set up the legend with custom markers
    if detected_count >= 1:
        plt.legend([detected_marker, undetected_marker, station_marker],
                   [f'Detected Earthquake: {detected_count}', f'Undetected Earthquake: {undetected_count}',
                    f'Station {station}'], loc='lower center', handler_map={plt.Line2D: HandlerLine2D(numpoints=1)},
                   ncol=3)
    else:
        plt.legend([undetected_marker, station_marker],
                   [f'Undetected Earthquake: {undetected_count}', f'Station {station}'], loc='lower center',
                   handler_map={plt.Line2D: HandlerLine2D(numpoints=1)}, ncol=3)

    if path:
        file_path = os.path.join(path, f'catalogued_plot_{title_date}.png')
        plt.tight_layout()
        plt.savefig(file_path, bbox_inches='tight', pad_inches=0)

    # Show the figure if show is True
    if show:
        plt.tight_layout()
        plt.show()

    plt.close()


def html_header(date_str):
    header = f"""
    <html>
    <head>
        <title>Earthquake Report for {date_str}</title>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .event {{ margin-bottom: 40px; }}
            .event img, .catalogue_plot img {{ width: 100%; max-width: 800px; }}
            .catalogue-list {{ width: 80%; max-width: 600px; }}
            .annotation_plot {{ width: 100% }}
            .statistics {{ margin-top: 5px; }}
            .section_title {{ font-weight: bold; color: #4793AF; font-size: 20px; }}
            .event_details, .catalogue-list {{ width: 800px; }}
            table {{ border-collapse: collapse; font-size: 15px; width: 100%; }}
        </style>
    </head>
    <body>
        <h1>Earthquake Report for {date_str}</h1>
    """
    return header


def html_basic_info(network, station_code, catalogue_provider):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    html_content = f"""
        <p><strong>Station:</strong> {network}.{station_code}&nbsp;&nbsp;&nbsp;&nbsp;<strong>Catalogue Provider:</strong> {catalogue_provider}&nbsp;&nbsp;&nbsp;&nbsp;<strong>Issued At:</strong> {current_time}</p>
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


def html_catalogue_list(df, simplified):
    catalogued_events = df[df['catalogued'] == True]

    table_rows = []
    for index, event in catalogued_events.iterrows():

        if simplified:
            event_time = datetime.strptime(event["time"], '%Y-%m-%dT%H:%M:%S.%f').strftime('%Y-%m-%d %H:%M:%S')
            row_style = ''  # No style needed when simplified and only showing detected
        else:
            event_time = event["time"]
            row_style = ' style="color: #557C55; font-weight: bold;"' if event[
                'detected'] else ' style="color: #707070;"'

        # Only add detected events if simplified is True
        if simplified and not event['detected']:
            continue

        table_rows.append(
            f'<tr{row_style}>'
            f'<td>{event_time}</td>'
            f'<td>{event["lat"]}, {event["long"]}</td>'
            f'<td>{event["mag"]} {event["mag_type"]}</td>'
            f'</tr>'
        )

    # Create the HTML for the table rows
    table_html = '\n'.join(table_rows)

    # Conditional heading for detected catalogued events
    detected_heading = "<p><strong>Detected Catalogued Events:</strong></p>" if simplified else ""

    # Build the final HTML content
    html_content = f"""
    <div class="catalogue-list">
        {detected_heading}
        <table border="1" style="width: 100%; border-collapse: collapse;">
            <thead>
                <tr>
                    <th>Time</th>
                    <th>Location</th>
                    <th>Magnitude</th>
                </tr>
            </thead>
            <tbody>
                {table_html}
            </tbody>
        </table>
    </div>
    """
    return html_content


def html_event_stats(df, detected):
    # Calculate stats from the dataframe
    number_catalogued, number_matched, number_not_detected, number_not_in_catalogue, number_p_identified, number_s_identified = calculate_matching_stats(
        df)
    total_detected = number_matched + number_not_in_catalogue

    # Basic HTML content with total events detected
    html_content = f"""
    <div>
        <p class="section_title"><strong>Detected Events Statistics</strong></p>
        <p><strong>Total Events Detected:</strong> {total_detected}</p>
    """

    if detected:
        # Include detailed stats if any catalogued earthquakes were detected
        event_detected_rate = (number_matched / number_catalogued * 100) if number_catalogued else 0
        p_detected_rate = (number_p_identified / number_catalogued * 100) if number_catalogued else 0
        s_detected_rate = (number_s_identified / number_catalogued * 100) if number_catalogued else 0

        html_content += f"""
        <p><strong>Catalogued Events Detected:</strong> {number_matched} out of {number_catalogued}</p>
        <p><strong>Event Detected Rate:</strong> {event_detected_rate:.2f}%</p>
        <p><strong>P Wave Detected Rate:</strong> {p_detected_rate:.2f}%</p>
        <p><strong>S Wave Detected Rate:</strong> {s_detected_rate:.2f}%</p>
        <p><strong>Detected But Not Catalogued:</strong> {number_not_in_catalogue}</p>
        </div>
        """
    else:
        # If no catalogued earthquakes were detected, add this message
        html_content += """
        <p><strong>No earthquake from the catalogue was detected.</strong></p>
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
                    <td colspan="2">Depth</td><td colspan="2">{event_info['depth']:.2f} km</td>
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
                    <td colspan="2">P Peak Confidence</td><td colspan="2">{event_info.get('P_peak_confidence', 'N/A')}</td>
                    <td colspan="2">S Peak Confidence</td><td colspan="2">{event_info.get('S_peak_confidence', 'N/A')}</td>
                </tr>
                <tr>
                    <td colspan="2">P time error</td><td colspan="2">{event_info.get('p_time_error', 'N/A')}</td>
                    <td colspan="2">S time error</td><td colspan="2">{event_info.get('s_time_error', 'N/A')}</td>
                </tr>
            </table>
        </div>
        <br>
        <br>
"""

        html_parts.append(event_html)

    html_content = '\n'.join(html_parts)
    return html_content


def create_earthquake_report_html(df, file_path, date, station, simplified=True):
    matched_events = df[(df['catalogued'] == True) & (df['detected'] == True)]

    event_detected = not matched_events.empty

    network, station_code, _ = station
    date_str = date.strftime('%Y-%m-%d')
    output_html_file = os.path.join(file_path, f"{date_str}_report.html")
    catalog_image_filename = f"catalogued_plot_{date_str}.png"  # Image file name for the catalogue plot

    # Determine the provider from the catalogued events
    catalogue_provider = df[df['catalogued'] == True]['provider'].iloc[0] if not df[df['catalogued'] == True].empty else "Unknown"

    header = html_header(date_str)
    basic_info = html_basic_info(network, station_code, catalogue_provider)
    catalogue_map = html_catalogue_map(catalog_image_filename)  # Call to add the catalogue map
    catalogue_list = html_catalogue_list(df, simplified)
    event_stats = html_event_stats(df, event_detected)

    event_info = html_matched_info(matched_events, catalogue_provider)

    # Assemble all parts into the final HTML content
    html_content = f"{header}{basic_info}<hr>{catalogue_map}{catalogue_list}<hr>{event_stats}<hr>{event_info}</body></html>"

    with open(output_html_file, 'w') as file:
        file.write(html_content)
    print(f"HTML report generated: {output_html_file}")

    return html_content

