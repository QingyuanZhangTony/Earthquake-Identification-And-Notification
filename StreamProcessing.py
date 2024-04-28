import bisect
from collections import deque

import numpy as np
import pandas as pd
from obspy import UTCDateTime, Stream
from obspy.signal.filter import bandpass


def remove_outliers_threshold(trace, threshold_factor=2):
    # Calculate global mean and standard deviation for the trace
    global_mean = trace.data.mean()
    global_std = trace.data.std()

    # Identify outliers as points beyond the threshold times the standard deviation from the mean
    outliers = np.abs(trace.data - global_mean) > (threshold_factor * global_std)
    trace.data[outliers] = global_mean  # Replace outliers with the global mean
    return trace


def remove_outliers_IQR(trace, threshold_factor=2):
    # Calculate outliers using the median and IQR
    median = np.median(trace.data)
    quartile1 = np.percentile(trace.data, 25)
    quartile3 = np.percentile(trace.data, 75)
    iqr = quartile3 - quartile1
    lower_bound = median - (threshold_factor * iqr)
    upper_bound = median + (threshold_factor * iqr)

    # Identify data points that are outside the boundaries
    outliers = (trace.data < lower_bound) | (trace.data > upper_bound)
    # Replace outliers with the median, or consider other replacement strategies
    trace.data[outliers] = median
    return trace


def remove_outliers_window(trace, window_size=10, threshold_factor=1.5):
    # Prepare an empty array to store the processed data
    filtered_data = np.copy(trace.data)

    # Iterate through the data, processing each window
    for i in range(len(trace.data)):
        # Calculate the start and end index for the window
        start_index = max(0, i - window_size // 2)
        end_index = min(len(trace.data), i + window_size // 2)

        # Extract data within the window
        window_data = trace.data[start_index:end_index]

        # Compute median and IQR within the window
        median = np.median(window_data)
        quartile1 = np.percentile(window_data, 25)
        quartile3 = np.percentile(window_data, 75)
        iqr = quartile3 - quartile1

        # Calculate boundaries for outliers
        lower_bound = median - (threshold_factor * iqr)
        upper_bound = median + (threshold_factor * iqr)

        # Check if the current point is an outlier and replace it if necessary
        if trace.data[i] < lower_bound or trace.data[i] > upper_bound:
            filtered_data[i] = median  # Replace outlier with window median

    # Update original data
    trace.data = filtered_data
    return trace


def remove_outliers_window_optimized(trace, window_size=10, threshold_factor=1.5):
    # Prepare an empty list to store the processed data
    filtered_data = np.copy(trace.data)
    # Deque to store indexes of elements in the current window
    window = deque()
    # Sorted list to store the current window's data for median and IQR calculation
    sorted_window = []

    # Iterate through the data
    for i in range(len(trace.data)):
        # Remove elements outside the window
        if window and window[0] < i - window_size // 2:
            old_index = window.popleft()
            old_value = trace.data[old_index]
            sorted_window.remove(old_value)

        # Add the current element to the window
        bisect.insort_left(sorted_window, trace.data[i])
        window.append(i)

        # Compute median and IQR within the window if the window is full
        if len(window) > window_size // 2:
            median = sorted_window[len(sorted_window) // 2]
            quartile1 = sorted_window[len(sorted_window) // 4]
            quartile3 = sorted_window[(3 * len(sorted_window)) // 4]
            iqr = quartile3 - quartile1

            # Calculate boundaries for outliers
            lower_bound = median - (threshold_factor * iqr)
            upper_bound = median + (threshold_factor * iqr)

            # Replace outliers in the middle of the window
            middle = window[max(0, len(window) // 2 - 1)]
            if trace.data[middle] < lower_bound or trace.data[middle] > upper_bound:
                filtered_data[middle] = median

    # Return the trace with outliers replaced
    trace.data = filtered_data
    return trace


def stream_process(stream):
    # Remove the mean and linear trend from the data
    stream.detrend("demean")
    stream.detrend("linear")

    for trace in stream:
        # Remove outliers from the trace
        trace = remove_outliers_threshold(trace)
        #trace = remove_outliers_IQR(trace)
        # Apply a bandpass filter to the trace data
        trace.data = bandpass(trace.data, freqmin=1, freqmax=40, df=trace.stats.sampling_rate, corners=5)

    # Return the processed stream
    return stream


def extract_trace_inside_window(df, stream):
    extracted_segments = Stream()  # Initialize an empty Stream to hold the segments

    # Loop through each earthquake event in the DataFrame
    for index, row in df.iterrows():
        # Make sure P_predict and S_predict are not NaN
        if pd.isna(row['P_predict']) or pd.isna(row['S_predict']):
            continue

        p_arrival = UTCDateTime(row['P_predict'])
        s_arrival = UTCDateTime(row['S_predict'])

        # Define a buffer time around the P and S wave arrivals to visualize pre-arrival activity
        buffer_time = 45  # seconds

        # Calculate start and end times for the waveform extraction
        start_time = p_arrival - buffer_time
        end_time = s_arrival + buffer_time

        # Extract the waveform segment from the stream
        waveform_segment = stream.slice(start_time, end_time)

        # Add the extracted waveform segments to the new Stream object
        extracted_segments += waveform_segment

    return extracted_segments


def extract_trace_outside_window(df, stream):
    remaining_segments = Stream()  # Initialize an empty Stream to hold the segments

    # First, collect all the time windows
    time_windows = []
    for index, row in df.iterrows():
        if pd.isna(row['P_predict']) or pd.isna(row['S_predict']):
            continue

        p_arrival = UTCDateTime(row['P_predict'])
        s_arrival = UTCDateTime(row['S_predict'])
        buffer_time = 45  # seconds

        start_time = p_arrival - buffer_time
        end_time = s_arrival + buffer_time
        time_windows.append((start_time, end_time))

    # Sort time windows by start time
    time_windows.sort()

    # Compute the complementary intervals
    # Assume the stream has an overall start and end time
    stream_start = stream[0].stats.starttime
    stream_end = stream[-1].stats.endtime

    # Start by assuming we take everything from the beginning
    # of the stream to the start of the first window
    if time_windows:
        if stream_start < time_windows[0][0]:
            remaining_segments += stream.slice(stream_start, time_windows[0][0])

    # Now handle the gaps between the windows
    for i in range(len(time_windows) - 1):
        gap_start = time_windows[i][1]
        gap_end = time_windows[i + 1][0]
        if gap_start < gap_end:
            remaining_segments += stream.slice(gap_start, gap_end)

    # Finally, handle the interval from the end of the last window to the end of the stream
    if time_windows and stream_end > time_windows[-1][1]:
        remaining_segments += stream.slice(time_windows[-1][1], stream_end)

    return remaining_segments
