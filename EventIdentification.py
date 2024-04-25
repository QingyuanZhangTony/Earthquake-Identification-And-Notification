import pandas as pd
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


def extract_and_plot_waveforms2(df, stream):
    """
    Extracts waveform segments from a stream based on the earthquake P and S arrivals in a DataFrame,
    and plots the waveforms.

    :param df: DataFrame with columns including 'P_arrival', 'S_arrival', and potentially a buffer time.
    :param stream: ObsPy Stream object containing waveform data for a full day.
    """
    # Loop through each earthquake event in the DataFrame
    for index, row in df.iterrows():
        p_arrival = UTCDateTime(row['P_arrival'])
        s_arrival = UTCDateTime(row['S_arrival'])

        # Define a buffer time around the P and S wave arrivals to visualize pre-arrival activity
        buffer_time = 300  # seconds, e.g., 5 minutes

        # Calculate start and end times for the waveform extraction
        start_time = p_arrival - buffer_time
        end_time = s_arrival + buffer_time

        # Extract the waveform segment from the stream
        waveform_segment = stream.slice(start_time, end_time)

        # Plot the waveform segment

        waveform_segment.plot()

from obspy import Stream

def extract_and_plot_waveforms(df, stream):
    """
    Extracts waveform segments from a stream based on the earthquake P and S arrivals in a DataFrame.

    :param df: DataFrame with columns including 'P_arrival', 'S_arrival', and potentially a buffer time.
    :param stream: ObsPy Stream object containing waveform data for a full day.
    :return: Stream object containing all the extracted waveform segments.
    """
    extracted_segments = Stream()  # Initialize an empty Stream to hold the segments

    # Loop through each earthquake event in the DataFrame
    for index, row in df.iterrows():
        # Make sure P_arrival and S_arrival are not NaN
        if pd.isna(row['P_arrival']) or pd.isna(row['S_arrival']):
            continue

        p_arrival = UTCDateTime(row['P_arrival'])
        s_arrival = UTCDateTime(row['S_arrival'])

        # Define a buffer time around the P and S wave arrivals to visualize pre-arrival activity
        buffer_time = 300  # seconds, e.g., 5 minutes

        # Calculate start and end times for the waveform extraction
        start_time = p_arrival - buffer_time
        end_time = s_arrival + buffer_time

        # Extract the waveform segment from the stream
        waveform_segment = stream.slice(start_time, end_time)

        # Add the extracted waveform segments to the new Stream object
        extracted_segments += waveform_segment

    return extracted_segments

# Example usage:
# df = predict_arrivals(...)  # Assuming predict_arrivals has been called and returns the needed DataFrame
# stream = obspy.read("path_to_mseed_file_for_the_day.mseed")  # Load your full-day stream data
# extracted_segments = extract_waveform_segments(df, stream)

