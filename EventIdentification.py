import obspy
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


