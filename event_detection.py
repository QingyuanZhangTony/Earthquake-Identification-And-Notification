import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from obspy.core import UTCDateTime
from obspy.signal.trigger import classic_sta_lta, trigger_onset

from utils import *


# Using STA/ LTA to detect earthquake events
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


# Using pretrained deeplearning models to detect earthquake events
def predict_and_annotate(stream, model):
    # Enable GPU for model processing
    enable_GPU(model)

    # Perform classification to extract picks
    outputs = model.classify(stream)
    predictions = []

    for pick in outputs.picks:
        pick_dict = pick.__dict__
        pick_data = {
            "peak_time": pick_dict["peak_time"],
            "peak_confidence": pick_dict["peak_value"],
            "phase": pick_dict["phase"]
        }
        predictions.append(pick_data)

    df_picks = pd.DataFrame(predictions)

    # Perform annotation to visualize the picks within the stream
    annotated_stream = model.annotate(stream)

    # Adjust channel names in the annotated stream to include the original channel plus the model suffix
    for tr in annotated_stream:
        parts = tr.stats.channel.split('_')
        if len(parts) > 1:
            tr.stats.channel = '_' + '_'.join(parts[1:])  # Join parts starting from the first underscore

    return df_picks, annotated_stream


# Filter for getting rid of false positives with a probability/ confidence threshold
def filter_confidence(df, p_threshold, s_threshold):
    # Define conditions for filtering
    p_condition = (df['phase'] == "P") & (df['peak_confidence'] < p_threshold)
    s_condition = (df['phase'] == "S") & (df['peak_confidence'] < s_threshold)

    # Combine conditions using logical OR
    combined_condition = p_condition | s_condition

    # Delete rows that meet either condition
    df = df[~combined_condition]

    return df


# Associate the detected signals with catalogued earthquakes using a time tolerance
def match_and_merge(df_catalogued, df_detected, tolerance_p, tolerance_s):
    remaining_det = df_detected.copy()

    for index, row in df_catalogued.iterrows():
        p_time = UTCDateTime(row['P_predict']) if pd.notna(row['P_predict']) else None
        s_time = UTCDateTime(row['S_predict']) if pd.notna(row['S_predict']) else None

        highest_p_confidence = 0
        highest_s_confidence = 0
        p_detected = None
        s_detected = None
        p_matched_indices = []
        s_matched_indices = []

        for d_index, d_row in remaining_det.iterrows():
            detected_time = UTCDateTime(d_row['peak_time'])
            detected_phase = d_row['phase']
            detected_confidence = d_row['peak_confidence']

            if detected_phase == 'P' and p_time and abs(detected_time - p_time) <= tolerance_p:
                if detected_confidence > highest_p_confidence:
                    highest_p_confidence = detected_confidence
                    p_detected = detected_time
                p_matched_indices.append(d_index)

            if detected_phase == 'S' and s_time and abs(detected_time - s_time) <= tolerance_s:
                if detected_confidence > highest_s_confidence:
                    highest_s_confidence = detected_confidence
                    s_detected = detected_time
                s_matched_indices.append(d_index)

        if p_detected:
            df_catalogued.at[index, 'P_detected'] = p_detected.isoformat()
            df_catalogued.at[index, 'P_peak_confidence'] = highest_p_confidence
            df_catalogued.at[index, 'detected'] = True

        if s_detected:
            df_catalogued.at[index, 'S_detected'] = s_detected.isoformat()
            df_catalogued.at[index, 'S_peak_confidence'] = highest_s_confidence
            df_catalogued.at[index, 'detected'] = True

        # Consolidate matched indices and remove duplicates
        all_matched_indices = list(set(p_matched_indices + s_matched_indices))
        remaining_det.drop(index=all_matched_indices, inplace=True, errors='ignore')

    new_rows = []
    for _, d_row in remaining_det.iterrows():
        new_row = {
            'catalogued': False,
            'detected': True,
            'P_detected': d_row['peak_time'].isoformat() if d_row['phase'] == 'P' else None,
            'S_detected': d_row['peak_time'].isoformat() if d_row['phase'] == 'S' else None,
            'P_peak_confidence': d_row['peak_confidence'] if d_row['phase'] == 'P' else None,
            'S_peak_confidence': d_row['peak_confidence'] if d_row['phase'] == 'S' else None
        }
        new_rows.append(new_row)

    if new_rows:
        df_merged = pd.concat([df_catalogued, pd.DataFrame(new_rows)], ignore_index=True)
    else:
        df_merged = df_catalogued.copy()

    # Remove the peak_confidence column
    if 'peak_confidence' in df_merged.columns:
        df_merged.drop(columns='peak_confidence', inplace=True)

    return df_merged


def calculate_matching_stats(df):
    number_catalogued = df[df['catalogued'] == True].shape[0]

    # Count detected events in the catalogue
    number_matched = df[(df['detected'] == True) & (df['catalogued'] == True)].shape[0]

    # Count undetected events in the catalogue
    number_not_detected = number_catalogued - number_matched

    # Count detected events that are not in the catalogue
    number_not_in_catalogue = df[df['catalogued'] == False].shape[0]

    number_p_identified = df[(df['detected'] == True) &
                             (df['catalogued'] == True) &
                             (df['P_detected'].notnull())].shape[0]

    number_s_identified = df[(df['detected'] == True) &
                             (df['catalogued'] == True) &
                             (df['S_detected'].notnull())].shape[0]

    return number_catalogued, number_matched, number_not_detected, number_not_in_catalogue, number_p_identified, number_s_identified


def print_event_info(earthquake_info):
    print(f"Event ID: {earthquake_info['full_id']}")
    print(f"Earthquake Time: {earthquake_info['time']}")
    print(f"Location: Lat {earthquake_info['lat']}, Long {earthquake_info['long']}")
    print(f"Magnitude: {earthquake_info['mag']} {earthquake_info['mag_type']}")
    print(f"Depth: {earthquake_info['depth']} m")
    print(f"Distance to Station: {earthquake_info['epi_distance']:.2f} km")

    p_pred_time = earthquake_info.get('predicted_p_time', 'N/A')
    s_pred_time = earthquake_info.get('predicted_s_time', 'N/A')
    p_det_time = earthquake_info.get('detected_p_time', 'N/A')
    s_det_time = earthquake_info.get('detected_s_time', 'N/A')
    p_conf = earthquake_info.get('P_peak_confidence', 'N/A')
    s_conf = earthquake_info.get('S_peak_confidence', 'N/A')

    print()
    print(f"Predicted P time: {p_pred_time}")
    print(f"Detected P time: {p_det_time}")
    print(f"Predicted S time: {s_pred_time}")
    print(f"Detected S time: {s_det_time}")
    print(f"Prediction confidence: P: {p_conf}   S: {s_conf}")
    print('-' * 40)
