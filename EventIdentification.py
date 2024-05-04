import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from obspy.core import UTCDateTime
from obspy.signal.trigger import classic_sta_lta, trigger_onset

from utils import *


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


def pretrained_phase_picking(stream, model):
    enable_GPU(model)

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

    return df_picks


def filter_confidence(result_df, confidence_threshold):
    condition = (result_df['catalogued'] == False) & \
                (result_df['detected'] == True) & \
                (result_df['peak_confidence'] < confidence_threshold)

    # Delete rows that meet the criteria
    result_df = result_df[~condition]

    return result_df


def match_and_merge(df_catalogued, df_detected, time_tolerance):
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

            if detected_phase == 'P' and p_time and abs(detected_time - p_time) <= time_tolerance:
                if detected_confidence > highest_p_confidence:
                    highest_p_confidence = detected_confidence
                    p_detected = detected_time
                p_matched_indices.append(d_index)

            if detected_phase == 'S' and s_time and abs(detected_time - s_time) <= time_tolerance:
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
            'peak_confidence': d_row['peak_confidence']
        }
        new_rows.append(new_row)

    if new_rows:
        df_merged = pd.concat([df_catalogued, pd.DataFrame(new_rows)], ignore_index=True)
    else:
        df_merged = df_catalogued.copy()

    return df_merged


def print_matching_result(df):
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


def make_prediction(stream, model):
    enable_GPU(model)
    predictions = model.annotate(stream)
    return predictions


def plot_predictions_wave(stream, predictions, detected_p_time, detected_s_time, predicted_p_time, predicted_s_time,
                          earthquake_info):
    # Convert start and end times to UTCDateTime and add/subtract 60 seconds buffer
    starttime = UTCDateTime(predicted_p_time) - 60
    endtime = UTCDateTime(predicted_s_time) + 60

    # Slice the stream for the specific earthquake event
    trace = stream.slice(starttime=starttime, endtime=endtime)

    if not trace:
        print("No data in the trace.")
        return

    start_time = trace[0].stats.starttime
    end_time = trace[0].stats.endtime

    color_dict = {"P": "C0", "S": "C1", "Detection": "C2"}

    # Plot the trace
    fig, ax = plt.subplots(2, 1, figsize=(13, 6), sharex=True, gridspec_kw={'hspace': 0.05, 'height_ratios': [1, 1]},
                           constrained_layout=True)

    # Plot predictions
    for pred_trace in predictions:
        model_name, pred_class = pred_trace.stats.channel.split("_")
        if pred_class == "N":
            continue  # Skip noise traces
        c = color_dict.get(pred_class, "black")  # Use black as default color if not found
        offset = pred_trace.stats.starttime - start_time
        ax[1].plot(offset + pred_trace.times(), pred_trace.data, label=pred_class, c=c)

    ax[1].set_ylabel("Model Predictions")
    ax[1].legend(loc=2)
    ax[1].set_ylim(0, 1.1)

    ax[0].plot(trace[0].times(), trace[0].data / np.amax(np.abs(trace[0].data)), 'k', label=trace[0].stats.channel)

    # Plot detected and predicted P and S times as vertical lines
    times = [detected_p_time, detected_s_time, predicted_p_time, predicted_s_time]
    colors = ['C0', 'C1', 'C0', 'C1']
    styles = ['-', '-', '--', '--']  # Solid lines for detected, dashed lines for predicted
    labels = ['Detected P Arrival', 'Detected S Arrival', 'Predicted P Arrival', 'Predicted S Arrival']
    for t, color, style, label in zip(times, colors, styles, labels):
        if t:
            t_utc = UTCDateTime(t)
            ax[0].axvline(x=t_utc - start_time, color=color, linestyle=style, label=label, linewidth=0.8)

    ax[0].set_title(
        f'Earthquake on {earthquake_info["time"]} - Lat: {earthquake_info["lat"]}, Long: {earthquake_info["long"]} - Magnitude: {earthquake_info["mag"]}')
    ax[0].set_ylabel('Normalized Amplitude')
    ax[1].set_xlabel('Time [s]')
    ax[0].set_xlim(0, end_time - start_time)
    ax[0].legend(loc='upper right')

    plt.show()



