import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, AutoDateLocator
from obspy import UTCDateTime


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
        ax.axvline(x=detected_p_time_utc .matplotlib_date, color='red', linestyle="--", label='Detected Start', linewidth=0.8)
    if detected_s_time:
        detected_s_time_utc = UTCDateTime(detected_s_time)
        ax.axvline(x=detected_s_time_utc .matplotlib_date, color='purple', linestyle="--", label='Detected Start', linewidth=0.8)

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


def create_trace_from_stream(stream, start_time, end_time, window_before, window_after):
    starttime = UTCDateTime(start_time) - window_before
    endtime = UTCDateTime(end_time) + window_after
    return stream.slice(starttime=starttime, endtime=endtime).copy()


def catalogued_and_detected_plot(df, stream):
    filtered_events = df[(df['catalogued'] == True) & (df['detected'] == True)]

    for _, row in filtered_events.iterrows():
        earthquake_info = {
            "time": row['time'],
            "lat": row['lat'],
            "long": row['long'],
            "mag": row['mag'],
            "mag_type": row['mag_type'],
        }
        trace = create_trace_from_stream(stream, row['P_predict'], row['S_predict'], 60, 60)
        if trace.count() == 0:
            continue
        plot_with_timestamps(trace[0], row['P_detected'], row['S_detected'], row['P_predict'], row['S_predict'], earthquake_info)
