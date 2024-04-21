import numpy as np
from obspy.signal.filter import bandpass
import os
from obspy import UTCDateTime
from obspy import read


def get_stream(date, station_info):
    network, station, data_provider = station_info
    dataset_folder = f"{network}.{station}"
    cur_dir = os.getcwd()
    # Include the 'data' directory in the path
    data_dir = os.path.join(cur_dir, "data", dataset_folder)

    # Find the mseed file with the specified date and station
    file_name = f"{date.strftime('%Y-%m-%d')}_{network}.{station}..Z.mseed"
    file_path = os.path.join(data_dir, file_name)

    # Read the stream from the mseed file
    stream = read(file_path)
    return stream


def remove_outliers(trace, threshold_factor=2):
    # Calculate global mean and standard deviation for the trace
    global_mean = trace.data.mean()
    global_std = trace.data.std()

    # Identify outliers as points beyond the threshold times the standard deviation from the mean
    outliers = np.abs(trace.data - global_mean) > (threshold_factor * global_std)
    trace.data[outliers] = global_mean  # Replace outliers with the global mean
    return trace


def stream_process(stream):
    # Remove the mean and linear trend from the data
    stream.detrend("demean")
    stream.detrend("linear")

    for trace in stream:
        # Remove outliers from the trace
        trace = remove_outliers(trace)
        # Apply a bandpass filter to the trace data
        trace.data = bandpass(trace.data, freqmin=1, freqmax=40, df=trace.stats.sampling_rate, corners=5)

    # Return the processed stream
    return stream


def plot_graph(stream):
    stream.plot()
