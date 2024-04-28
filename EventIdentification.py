import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.dates import DateFormatter
from matplotlib.ticker import MaxNLocator
from obspy import UTCDateTime
from obspy.signal.trigger import classic_sta_lta, trigger_onset


def detect_earthquakes(stream, sta_window, lta_window, threshold_on, threshold_off):
    # This list will store the start and end times of all detected earthquakes
    detected_earthquakes = []

    # Process each trace in the stream
    for trace in stream:
        # Apply the STA/LTA algorithm
        cft = classic_sta_lta(trace.data, int(sta_window * trace.stats.sampling_rate),
                              int(lta_window * trace.stats.sampling_rate))

        # Define the trigger on and off thresholds
        on_off = trigger_onset(cft, threshold_on, threshold_off)

        # Convert index positions to actual times based on the trace's timing
        for onset in on_off:
            start = trace.stats.starttime + onset[0] / trace.stats.sampling_rate
            end = trace.stats.starttime + onset[1] / trace.stats.sampling_rate
            detected_earthquakes.append((start, end))

    return detected_earthquakes


def plot_identified(trace, earthquake_times):
    # Create the plot
    plt.figure(figsize=(12, 3))
    ax = plt.gca()

    # Plot the waveform data of the trace
    times = trace.times("matplotlib")
    ax.plot_date(times, trace.data, 'b-', linewidth=0.5, label=trace.id)

    # Get the start and end times of the trace
    trace_start = trace.stats.starttime
    trace_end = trace.stats.endtime

    # Mark earthquake times with vertical lines
    for start_time, end_time in earthquake_times:
        start_time_utc = UTCDateTime(start_time)
        end_time_utc = UTCDateTime(end_time)

        # Check if earthquake times are within the trace's timeframe
        if start_time_utc >= trace_start and end_time_utc <= trace_end:
            start_matplotlib = start_time_utc.matplotlib_date
            end_matplotlib = end_time_utc.matplotlib_date
            ax.axvline(x=start_matplotlib, color='r', linewidth=1, linestyle="--", label='Start')
            ax.axvline(x=end_matplotlib, color='g', linewidth=1, linestyle="--", label='End')

    # Set legends and titles
    ax.legend()
    ax.set_title(f'Trace: {trace.id}')
    ax.set_ylabel('Amplitude')
    ax.set_xlabel('Time')

    # Set x-axis to date format
    plt.gcf().autofmt_xdate()
    plt.tight_layout()
    plt.show()


def plot_identified_prediction(trace, earthquake_times, predicted_p_times, predicted_s_times):
    # Create the plot
    plt.figure(figsize=(12, 3))
    ax = plt.gca()

    # Plot the waveform data of the trace
    times = trace.times("matplotlib")
    ax.plot_date(times, trace.data, 'k-', linewidth=0.5)  # No label here to exclude from legend

    # Initialize a dictionary to track unique legend labels
    legend_labels = {}

    # Mark actual earthquake start times with vertical lines
    for start_time, _ in earthquake_times:  # Removed end_time as we are not plotting it
        start_time_utc = UTCDateTime(start_time)

        # Check if earthquake start time is within the trace's timeframe
        if start_time_utc >= trace.stats.starttime and start_time_utc <= trace.stats.endtime:
            start_matplotlib = start_time_utc.matplotlib_date
            ax.axvline(x=start_matplotlib, color='r', linewidth=1, linestyle="--")
            legend_labels['Detected Start'] = 'r'  # Add the label only once

    # Mark predicted P wave arrival times with vertical lines
    for p_time in predicted_p_times:
        p_time_utc = UTCDateTime(p_time)
        # Check if the predicted P time is within the trace's timeframe
        if p_time_utc >= trace.stats.starttime and p_time_utc <= trace.stats.endtime:
            p_matplotlib = p_time_utc.matplotlib_date
            ax.axvline(x=p_matplotlib, color='green', linewidth=1, linestyle="--")
            legend_labels['Predicted P Arrival'] = 'green'

    # Mark predicted S wave arrival times with vertical lines
    for s_time in predicted_s_times:
        s_time_utc = UTCDateTime(s_time)
        # Check if the predicted S time is within the trace's timeframe
        if s_time_utc >= trace.stats.starttime and s_time_utc <= trace.stats.endtime:
            s_matplotlib = s_time_utc.matplotlib_date
            ax.axvline(x=s_matplotlib, color='blue', linewidth=1, linestyle="--")
            legend_labels['Predicted S Arrival'] = 'blue'

    # Create a custom legend without duplicates
    custom_lines = [plt.Line2D([0], [0], color=color, lw=2, linestyle='--') for label, color in legend_labels.items()]
    ax.legend(custom_lines, legend_labels.keys())

    ax.set_title(f'Trace: {trace.id}')
    ax.set_ylabel('Amplitude')
    ax.set_xlabel('Time')

    # Set x-axis to the desired date format
    ax.xaxis.set_major_formatter(DateFormatter('%H:%M'))

    # Set x-axis major locator to limit the number of ticks
    ax.xaxis.set_major_locator(MaxNLocator(4))

    # Rotate the x-axis labels to show them horizontally
    plt.setp(ax.get_xticklabels(), rotation=0, ha='center')

    plt.tight_layout()
    plt.show()


def match_catalogue(df, identified_times):
    # Set the accepted time difference (10 seconds)
    time_tolerance = 10

    # Loop through each row in the DataFrame
    for index, row in df.iterrows():
        # Get the predicted P and S wave arrival times
        p_time = UTCDateTime(row['P_predict']) if pd.notna(row['P_predict']) else None
        s_time = UTCDateTime(row['S_predict']) if pd.notna(row['S_predict']) else None

        # Loop through each actual earthquake time in identified_times
        for start_time, _ in identified_times:  # Only use the start time from each tuple
            eq_start_time_utc = UTCDateTime(start_time)  # Get the earthquake start time

            # If close to the predicted P or S arrival times, mark as detected
            if (p_time and abs(eq_start_time_utc - p_time) <= time_tolerance) or \
               (s_time and abs(eq_start_time_utc - s_time) <= time_tolerance):
                df.at[index, 'detected'] = True
                df.at[index, 'detected_start'] = eq_start_time_utc.isoformat()
                break  # Exit the loop once a match is found

    return df
