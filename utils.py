import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, AutoDateLocator
from obspy import UTCDateTime


def plot_with_timestamps(trace, start_time, predicted_p_times, predicted_s_times, earthquake_info):
    # Create the plot
    plt.figure(figsize=(10, 4))
    ax = plt.gca()

    # Plot the waveform data of the trace
    times = trace.times("matplotlib")
    ax.plot_date(times, trace.data, 'k-', linewidth=0.5)  # No label here to exclude from legend

    # Mark actual earthquake start time with vertical line
    start_time_utc = UTCDateTime(start_time)
    ax.axvline(x=start_time_utc.matplotlib_date, color='red', linestyle="--", label='Detected Start')

    # Mark predicted P wave arrival times with vertical lines
    for p_time in predicted_p_times:
        p_time_utc = UTCDateTime(p_time)
        ax.axvline(x=p_time_utc.matplotlib_date, color='green', linestyle="--", label='Predicted P Arrival')

    # Mark predicted S wave arrival times with vertical lines
    for s_time in predicted_s_times:
        s_time_utc = UTCDateTime(s_time)
        ax.axvline(x=s_time_utc.matplotlib_date, color='blue', linestyle="--", label='Predicted S Arrival')

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
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right', fontsize=10)

    # Create a custom legend and display the plot
    ax.legend()

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
        trace = create_trace_from_stream(stream, row['detected_start'], row['S_predict'], 60, 60)
        if trace.count() == 0:
            continue
        plot_with_timestamps(trace[0], row['detected_start'], [row['P_predict']], [row['S_predict']],
                                   earthquake_info)
