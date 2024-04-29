import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.dates import DateFormatter
from matplotlib.ticker import MaxNLocator
from obspy import UTCDateTime
from obspy.signal.trigger import classic_sta_lta, trigger_onset


def detect_earthquakes(stream, sta_window, lta_window, threshold_on, threshold_off):
    # This list will store the dictionaries with start and end times of all detected earthquakes
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
            detected_earthquakes.append({
                "detected_start": start.isoformat(),
                "detected_end": end.isoformat()
            })

    # Create a DataFrame from the list of dictionaries
    df = pd.DataFrame(detected_earthquakes)
    return df


def match_and_merge(df_catalogued, df_detected):
    time_tolerance = 10  # Tolerance for time difference in seconds

    # Iterate over each earthquake in the catalog
    for index, row in df_catalogued.iterrows():
        p_time = UTCDateTime(row['P_predict']) if pd.notna(row['P_predict']) else None
        s_time = UTCDateTime(row['S_predict']) if pd.notna(row['S_predict']) else None

        # Initialize the earliest and latest times for matched earthquakes
        earliest_time = None
        latest_time = None

        # Iterate over detected earthquakes
        matched_indices = []
        for d_index, d_row in df_detected.iterrows():
            detected_start = UTCDateTime(d_row['detected_start'])
            detected_end = UTCDateTime(d_row['detected_end'])

            # Check the time difference
            if (p_time and abs(detected_start - p_time) <= time_tolerance) or \
                    (s_time and abs(detected_start - s_time) <= time_tolerance):
                # Update the earliest and latest times
                if earliest_time is None or detected_start < earliest_time:
                    earliest_time = detected_start
                if latest_time is None or detected_end > latest_time:
                    latest_time = detected_end

                # Record the indices of matched detections for later removal
                matched_indices.append(d_index)

        # If matched earthquakes are found, update the catalog record
        if earliest_time and latest_time:
            df_catalogued.at[index, 'detected'] = True
            df_catalogued.at[index, 'detected_start'] = earliest_time.isoformat()
            df_catalogued.at[index, 'detected_end'] = latest_time.isoformat()

        # Remove matched detection records
        df_detected.drop(index=matched_indices, inplace=True)

    # Unmatched detected records are added as new entries to the catalog
    unmatched_earthquakes = df_detected.copy()
    unmatched_earthquakes['catalogued'] = False
    unmatched_earthquakes['detected'] = True  # Ensure 'detected' is set to True

    # Merge the catalog DataFrame with unmatched detected DataFrame
    df_all_events = pd.concat([df_catalogued, unmatched_earthquakes], ignore_index=True)

    return df_all_events


def print_statistics(df):
    # Count detected events in the catalogue
    detected_in_catalogue = df[(df['detected'] == True) & (df['catalogued'] == True)].shape[0]

    # Count undetected events in the catalogue
    not_detected_in_catalogue = df[(df['detected'] == False) & (df['catalogued'] == True)].shape[0]

    # Count detected events that are not in the catalogue
    detected_not_in_catalogue = df[df['catalogued'] == False].shape[0]

    # Print the results
    print("Earthquake Detection Statistics:")
    print("-------------------------------")
    print(f"Detected in Catalogue: {detected_in_catalogue}")
    print(f"Not Detected in Catalogue: {not_detected_in_catalogue}")
    print(f"Detected but Not in Catalogue: {detected_not_in_catalogue}")
