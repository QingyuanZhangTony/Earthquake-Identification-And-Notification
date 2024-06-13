from obspy.signal.trigger import classic_sta_lta, trigger_onset
import pandas as pd
from Other.utils import *
from earthquake import Earthquake
import seisbench.models as sbm


# Using pretrained deeplearning models to detect earthquake events
def predict_and_annotate(stream):
    # Get pretrained model for phase picking
    model = sbm.EQTransformer.from_pretrained("original")

    # Enable GPU processing if available
    if torch.cuda.is_available():
        torch.backends.cudnn.enabled = False
        model.cuda()
        print("CUDA available. Running on GPU")
    else:
        print("CUDA not available. Running on CPU")

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

    # Perform annotation to visualize the picks within the stream
    annotated_stream = model.annotate(stream)

    # Adjust channel names in the annotated stream to include the original channel plus the model suffix
    for tr in annotated_stream:
        parts = tr.stats.channel.split('_')
        if len(parts) > 1:
            tr.stats.channel = '_' + '_'.join(parts[1:])  # Join parts starting from the first underscore

    return predictions, annotated_stream


# Filter for getting rid of false positives with a probability/ confidence threshold
def filter_confidence(detections, p_threshold, s_threshold):
    # Filter detections based on threshold conditions
    filtered_detections = [
        detection for detection in detections
        if (detection['phase'] == "P" and detection['peak_confidence'] >= p_threshold) or
           (detection['phase'] == "S" and detection['peak_confidence'] >= s_threshold)
    ]
    return filtered_detections


# Associate the detected signals with catalogued earthquakes using a time tolerance
def match_and_merge(earthquakes, detections, tolerance_p, tolerance_s, p_only=False):
    for earthquake in earthquakes:
        highest_p_confidence = 0
        highest_s_confidence = 0
        best_p_detection = None
        best_s_detection = None

        for detection in detections:
            detected_time = UTCDateTime(detection['peak_time'])
            detected_phase = detection['phase']
            detected_confidence = detection['peak_confidence']

            if detected_phase == 'P' and earthquake.p_predicted and abs(
                    detected_time - UTCDateTime(earthquake.p_predicted)) <= tolerance_p:
                if detected_confidence > highest_p_confidence:
                    highest_p_confidence = detected_confidence
                    best_p_detection = detection['peak_time']

            if not p_only and detected_phase == 'S' and earthquake.s_predicted and abs(
                    detected_time - UTCDateTime(earthquake.s_predicted)) <= tolerance_s:
                if detected_confidence > highest_s_confidence:
                    highest_s_confidence = detected_confidence
                    best_s_detection = detection['peak_time']

        # Update earthquake with the best detected times and confidences
        if best_p_detection:
            earthquake.p_detected = best_p_detection
            earthquake.p_confidence = highest_p_confidence

            earthquake.detected = True

        if not p_only and best_s_detection:
            earthquake.s_detected = best_s_detection
            earthquake.s_confidence = highest_s_confidence

            earthquake.detected = True

        # Filter out the matched detections to avoid re-matching
        detections = [d for d in detections if
                      not (d['peak_time'] == best_p_detection or (not p_only and d['peak_time'] == best_s_detection))]

    # Add unmatched detections as new earthquake objects
    for detection in detections:
        unique_time_str = detection['peak_time'].isoformat() if isinstance(detection['peak_time'], UTCDateTime) else \
            detection['peak_time']
        new_earthquake = Earthquake(
            unique_id="new_" + unique_time_str,  # Now correctly concatenating strings
            provider="Detection",
            event_id=None,
            time=detection['peak_time'].isoformat() if isinstance(detection['peak_time'], UTCDateTime) else detection[
                'peak_time'],
            lat=None,
            long=None,
            mag=None,
            mag_type=None,
            depth=None,
            epi_distance=None,
            p_predicted=None,
            s_predicted=None,
            p_detected=detection['peak_time'].isoformat() if detection['phase'] == 'P' and isinstance(
                detection['peak_time'], UTCDateTime) else None,
            s_detected=detection['peak_time'].isoformat() if not p_only and detection['phase'] == 'S' and isinstance(
                detection['peak_time'], UTCDateTime) else None,
            p_confidence=detection['peak_confidence'] if detection['phase'] == 'P' else None,
            s_confidence=detection['peak_confidence'] if not p_only and detection['phase'] == 'S' else None,
            catalogued=False,
            detected=True
        )
        earthquakes.append(new_earthquake)

    return earthquakes


def calculate_matching_stats(earthquakes):
    number_catalogued = len([eq for eq in earthquakes if eq.catalogued])
    number_matched = len([eq for eq in earthquakes if eq.detected and eq.catalogued])
    number_not_detected = number_catalogued - number_matched
    number_not_in_catalogue = len([eq for eq in earthquakes if not eq.catalogued])

    number_p_identified = len([eq for eq in earthquakes if eq.detected and eq.catalogued and eq.p_detected is not None])
    number_s_identified = len([eq for eq in earthquakes if eq.detected and eq.catalogued and eq.s_detected is not None])

    return number_catalogued, number_matched, number_not_detected, number_not_in_catalogue, number_p_identified, number_s_identified


def save_list(data_list, station, identifier):
    date_str = station.report_date.strftime('%Y-%m-%d')
    path = station.report_folder

    # Ensure the target directory exists
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

    # Construct file path
    filename = f"{date_str}.{identifier}.csv"
    full_path = os.path.join(path, filename)

    # Open file and write data
    with open(full_path, 'w', newline='') as file:
        writer = csv.writer(file)

        headers = ["unique_id", "provider", "event_id", "time", "lat", "long", "mag", "mag_type",
                   "depth", "epi_distance", "p_predicted", "s_predicted", "p_detected", "s_detected",
                   "p_confidence", "s_confidence", "p_error", "s_error", "catalogued", "detected"]
        writer.writerow(headers)

        for earthquake in data_list:
            row = [
                earthquake.unique_id, earthquake.provider, earthquake.event_id, earthquake.time, earthquake.lat,
                earthquake.long, earthquake.mag, earthquake.mag_type, earthquake.depth, earthquake.epi_distance,
                earthquake.p_predicted, earthquake.s_predicted, earthquake.p_detected, earthquake.s_detected,
                earthquake.p_confidence, earthquake.s_confidence, earthquake.p_error, earthquake.s_error,
                earthquake.catalogued, earthquake.detected
            ]
            writer.writerow(row)

    print(f"List saved to {full_path}")
