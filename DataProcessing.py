import numpy as np
from obspy.signal.filter import bandpass


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


