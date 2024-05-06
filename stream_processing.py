import bisect
from collections import deque

import numpy as np
import pandas as pd
from obspy import UTCDateTime, Stream
from obspy.signal.filter import bandpass
import seisbench.models as sbm
import torch
from utils import *


# Methods for removing outliers
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


# Denoise stream with pretrained DeepDenoiser
def deep_denoiser(stream, model):
    # Enable GPU processing if available
    enable_GPU(model)

    # Save original channel names
    original_channels = [tr.stats.channel for tr in stream]

    # Apply denoising model
    annotations = model.annotate(stream)

    # Restore original channel names
    for tr, channel in zip(annotations, original_channels):
        tr.stats.channel = channel

    return annotations


# Apply conventional methods for signal cleaning
def stream_process(stream):
    # Remove the mean and linear trend from the data
    stream.detrend("demean")
    stream.detrend("linear")

    for trace in stream:
        # Remove outliers from the trace
        trace = remove_outliers_threshold(trace)

        # Apply a bandpass filter to the trace data
        trace.data = bandpass(trace.data, freqmin=1, freqmax=40, df=trace.stats.sampling_rate, corners=5)

    # Return the processed stream
    return stream


# Save the processed and denoised stream to file
def save_stream_to_file(stream, path, date, station_information, type):
    network, station = station_information[:2]
    location = "*"  # Default value, or customize as needed
    channel = "*Z*"  # Default value, or customize as needed

    # Format the filename with NSLC and '_processed' suffix
    date_str = date.strftime('%Y-%m-%d')
    nslc = f"{network}.{station}.{location}.{channel}".replace("*", "")
    filename = f"{date_str}_{nslc}.{type}.mseed"
    file_path = os.path.join(path, filename)

    # Ensure the directory exists
    os.makedirs(path, exist_ok=True)

    # Write the stream to a MiniSEED file
    stream.write(file_path, format='MSEED')

    print(f"Stream saved to {file_path}")
