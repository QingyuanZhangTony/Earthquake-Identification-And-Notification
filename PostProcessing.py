import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, AutoDateLocator
from obspy import UTCDateTime
from DataDownload import *
from obspy.geodetics import gps2dist_azimuth
from EventIdentification import *


def plot_with_timestamps(trace, detected_p_time, detected_s_time, predicted_p_time, predicted_s_time, earthquake_info):
    # Create the plot
    plt.figure(figsize=(9, 3))
    ax = plt.gca()

    # Plot the waveform data of the trace
    times = trace.times("matplotlib")
    ax.plot_date(times, trace.data, 'k-', linewidth=0.5)  # No label here to exclude from legend

    # Mark actual detected P and S times with vertical line
    if detected_p_time:
        detected_p_time_utc = UTCDateTime(detected_p_time)
        ax.axvline(x=detected_p_time_utc.matplotlib_date, color='red', linestyle="--", label='Detected Start',
                   linewidth=0.8)
    if detected_s_time:
        detected_s_time_utc = UTCDateTime(detected_s_time)
        ax.axvline(x=detected_s_time_utc.matplotlib_date, color='purple', linestyle="--", label='Detected Start',
                   linewidth=0.8)

    # Mark predicted P and S time with vertical line
    if predicted_p_time:
        p_time_utc = UTCDateTime(predicted_p_time)
        ax.axvline(x=p_time_utc.matplotlib_date, color='green', linestyle="--", label='Predicted P Arrival',
                   linewidth=0.8)
    if predicted_s_time:
        s_time_utc = UTCDateTime(predicted_s_time)
        ax.axvline(x=s_time_utc.matplotlib_date, color='blue', linestyle="--", label='Predicted S Arrival',
                   linewidth=0.8)

    # Set the title with earthquake information
    ax.set_title(f'Earthquake on {earthquake_info["time"]} - '
                 f'Lat: {earthquake_info["lat"]}, Long: {earthquake_info["long"]} - '
                 f'Magnitude: {earthquake_info["mag"]}')

    # Set labels
    ax.set_ylabel('Amplitude')
    ax.set_xlabel('Time')

    # Set x-axis to the desired date format
    ax.xaxis.set_major_formatter(DateFormatter('%Y-%m-%d %H:%M:%S'))

    # Adjust the locator to get more frequent time ticks (could also use AutoDateLocator for automatic tick setting)
    ax.xaxis.set_major_locator(AutoDateLocator())

    # Rotate the x-axis labels to show them horizontally
    plt.setp(ax.get_xticklabels(), rotation=20, ha='right', fontsize=8)

    # Create a custom legend and display the plot
    ax.legend(loc='lower right', fontsize='small')

    plt.tight_layout()
    plt.show()


def plot_spectrogram(trace):
    # 创建图形
    fig = plt.figure(figsize=(9, 3))
    # 生成频谱图
    trace.spectrogram(log=True, title='Spectrogram')
    plt.show()


def create_trace_from_stream(stream, start_time, end_time):
    starttime = UTCDateTime(start_time) - 60
    endtime = UTCDateTime(end_time) + 60
    return stream.slice(starttime=starttime, endtime=endtime).copy()


def get_earthquake_info(row):
    earthquake_info = {
        "time": row['time'],
        "lat": row['lat'],
        "long": row['long'],
        "mag": row['mag'],
        "mag_type": row['mag_type'],
        "P_peak_confidence": row.get('P_peak_confidence', None),
        "S_peak_confidence": row.get('S_peak_confidence', None)
    }
    return earthquake_info


def successful_visualize(df, stream):
    filtered_events = df[(df['catalogued'] == True) & (df['detected'] == True)]

    for _, row in filtered_events.iterrows():
        earthquake_info = get_earthquake_info(row)  # Use the new function to get earthquake info
        trace = create_trace_from_stream(stream, row['P_predict'], row['S_predict'])
        if trace.count() == 0:
            continue
        plot_with_timestamps(trace[0], row['P_detected'], row['S_detected'], row['P_predict'], row['S_predict'],
                             earthquake_info)


def successful_stats(df, stream, station_info):
    filtered_events = df[(df['catalogued'] == True) & (df['detected'] == True)]

    station_coordinates = get_coordinates(station_info)

    for _, row in filtered_events.iterrows():
        earthquake_info = get_earthquake_info(row)  # Use the new function to get earthquake info
        trace = create_trace_from_stream(stream, row['P_predict'], row['S_predict'])
        if trace.count() == 0:
            continue
        print_event_statistics(earthquake_info, station_coordinates)


def calculate_distance(station_coordinates, epicenter_coordinates):
    distance_meters, azimuth, back_azimuth = gps2dist_azimuth(
        station_coordinates[0], station_coordinates[1],  # Station latitude and longitude
        epicenter_coordinates[0], epicenter_coordinates[1]  # Epicenter latitude and longitude
    )
    distance_kilometers = distance_meters / 1000.0
    return distance_kilometers


def print_event_statistics(earthquake_info, station_coordinates):
    epicenter_coordinates = (earthquake_info['lat'], earthquake_info['long'])
    distance_kilometers = calculate_distance(station_coordinates, epicenter_coordinates)

    print(f"Earthquake Time: {earthquake_info['time']}")
    print(f"Location: Lat {earthquake_info['lat']}, Long {earthquake_info['long']}")
    print(f"Magnitude: {earthquake_info['mag']} {earthquake_info['mag_type']}")
    print(f"Distance to Station: {distance_kilometers:.2f} km")

    if 'P_peak_confidence' in earthquake_info:
        print(f"P wave Confidence: {earthquake_info['P_peak_confidence']}")
    if 'S_peak_confidence' in earthquake_info:
        print(f"S wave Confidence: {earthquake_info['S_peak_confidence']}")
    print('-' * 40)

 


