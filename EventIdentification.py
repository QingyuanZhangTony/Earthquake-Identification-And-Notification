import pandas as pd
import seisbench.models as sbm
from obspy.core import UTCDateTime
from obspy.signal.trigger import classic_sta_lta, trigger_onset


def detect_sta_lta(stream, sta_window, lta_window, threshold_on, threshold_off):
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


def print_detected(df_detected):
    if not df_detected.empty:
        print('Number of Earthquakes Detected :', len(df_detected))
        print()
    else:
        print('No earthquake detected or an error occurred.')
        print()


def match_and_merge(df_catalogued, df_detected, time_tolerance):
    # Copy detected data to track unmatched detections
    remaining_det = df_detected.copy()

    # Iterate over each earthquake event in the catalog
    for index, row in df_catalogued.iterrows():
        p_time = UTCDateTime(row['P_predict']) if pd.notna(row['P_predict']) else None
        s_time = UTCDateTime(row['S_predict']) if pd.notna(row['S_predict']) else None

        # Initialize variables to track the highest confidence and corresponding times
        highest_p_confidence = 0
        highest_s_confidence = 0
        p_detected = None
        s_detected = None

        # Iterate over detected earthquakes to match P and S waves
        matched_indices = []
        for d_index, d_row in remaining_det.iterrows():
            detected_time = UTCDateTime(d_row['peak_time'])
            detected_phase = d_row['phase']
            detected_confidence = d_row['peak_confidence']

            # Match P wave
            if detected_phase == 'P' and p_time and abs(detected_time - p_time) <= time_tolerance:
                if detected_confidence > highest_p_confidence:
                    highest_p_confidence = detected_confidence
                    p_detected = detected_time
                matched_indices.append(d_index)

            # Match S wave
            elif detected_phase == 'S' and s_time and abs(detected_time - s_time) <= time_tolerance:
                if detected_confidence > highest_s_confidence:
                    highest_s_confidence = detected_confidence
                    s_detected = detected_time
                matched_indices.append(d_index)

        # Update the catalog DataFrame with detected times and highest confidence
        if p_detected:
            df_catalogued.at[index, 'P_detected'] = p_detected.isoformat()
            df_catalogued.at[index, 'peak_confidence'] = highest_p_confidence
            df_catalogued.at[index, 'detected'] = True
        if s_detected:
            df_catalogued.at[index, 'S_detected'] = s_detected.isoformat()
            df_catalogued.at[index, 'peak_confidence'] = highest_s_confidence
            df_catalogued.at[index, 'detected'] = True

        # Remove matched detections from remaining detections
        remaining_det.drop(index=matched_indices, inplace=True)

    # Add unmatched detections to the catalog
    new_rows = []
    for _, d_row in remaining_det.iterrows():
        new_row = {
            'catalogued': False,
            'detected': True,
            'P_detected': d_row['peak_time'].isoformat() if d_row['phase'] == 'P' else None,
            'S_detected': d_row['peak_time'].isoformat() if d_row['phase'] == 'S' else None,
            'peak_confidence': d_row['peak_confidence']  # Directly move peak confidence
        }
        new_rows.append(new_row)

    if new_rows:
        df_merged = pd.concat([df_catalogued, pd.DataFrame(new_rows)], ignore_index=True)
    else:
        df_merged = df_catalogued.copy()

    return df_merged


def print_statistics(df):
    # Count detected events in the catalogue
    detected_in_catalogue = df[(df['detected'] == True) & (df['catalogued'] == True)].shape[0]

    # Count undetected events in the catalogue
    not_detected_in_catalogue = df[(df['detected'] == False) & (df['catalogued'] == True)].shape[0]

    # Count detected events that are not in the catalogue
    detected_not_in_catalogue = df[df['catalogued'] == False].shape[0]

    # Print the results
    print(f"Detected in Catalogue: {detected_in_catalogue}")
    print(f"Not Detected in Catalogue: {not_detected_in_catalogue}")
    print(f"Detected but Not in Catalogue: {detected_not_in_catalogue}")
    print()


def detect_pretrained_picker(stream):
    eqt_model = sbm.EQTransformer.from_pretrained("original")
    outputs = eqt_model.classify(stream)
    data = []

    for pick in outputs.picks:
        pick_dict = pick.__dict__
        pick_data = {
            #"detected_start": pick_dict["start_time"],
            #"detected_end": pick_dict["end_time"],
            "peak_time": pick_dict["peak_time"],
            "peak_confidence": pick_dict["peak_value"],
            "phase": pick_dict["phase"]
        }

        data.append(pick_data)

    df_picks = pd.DataFrame(data)

    return df_picks


def filter_confidence(result_df, confidence_threshold):
    condition = (result_df['catalogued'] == False) & \
                (result_df['detected'] == True) & \
                (result_df['peak_confidence'] < confidence_threshold)

    # Delete rows that meet the criteria
    result_df = result_df[~condition]

    return result_df
