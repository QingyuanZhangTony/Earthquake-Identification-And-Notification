import os

from obspy import UTCDateTime

import os

import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image as PILImage
from matplotlib.legend_handler import HandlerLine2D
from obspy.geodetics.base import locations2degrees

def calculate_time_error(predicted, detected):
    if not predicted or not detected:
        return 'N/A'
    try:
        predicted_dt = UTCDateTime(predicted)
        detected_dt = UTCDateTime(detected)

        # Calculate the time difference in seconds
        delta = detected_dt - predicted_dt
        sign = '+' if delta > 0 else '-' if delta < 0 else ''

        return f"{sign}{abs(delta):.2f}s"
    except Exception as e:
        return f"Error: {str(e)}"


def plot_detected(stream, annotated_stream, earthquake, path=None, simplified=False):
    # Extract times directly from Earthquake object
    detected_p_time = earthquake.p_detected
    detected_s_time = earthquake.s_detected
    predicted_p_time = earthquake.p_predicted
    predicted_s_time = earthquake.s_predicted

    # Calculate the time range for slicing the stream
    start_times = [t for t in [predicted_p_time, detected_p_time] if t is not None]
    end_times = [t for t in [predicted_s_time, detected_s_time] if t is not None]
    starttime = min(start_times) - 60 if start_times else None
    endtime = max(end_times) + 60 if end_times else None

    if not starttime or not endtime:
        print("Invalid time range for slicing.")
        return None

    trace = stream.slice(starttime=starttime, endtime=endtime)
    if trace.count() == 0:
        print("No data in the trace.")
        return None

    start_time = trace[0].stats.starttime
    end_time = trace[0].stats.endtime

    fig, axes = plt.subplots(3 if not simplified else 2, 1, figsize=(13, 9 if not simplified else 6), sharex=True,
                             gridspec_kw={'hspace': 0.04, 'height_ratios': [1, 1, 1] if not simplified else [1, 1]})

    # First subplot: Normalized Waveform Plot
    axes[0].plot(trace[0].times(), trace[0].data / np.amax(np.abs(trace[0].data)), 'k', label=trace[0].stats.channel)
    axes[0].set_ylabel('Normalized Amplitude')

    if not simplified:
        # Second subplot: Prediction Confidence Plot
        for pred_trace in annotated_stream:
            model_name, pred_class = pred_trace.stats.channel.split("_")
            if pred_class == "N":
                continue  # Skip noise traces
            c = {"P": "C0", "S": "C1", "De": "#008000"}.get(pred_class,
                                                            "black")  # Use color dictionary for specific classes
            offset = pred_trace.stats.starttime - start_time
            label = "Detection" if pred_class == "De" else pred_class
            axes[1].plot(offset + pred_trace.times(), pred_trace.data, label=label, c=c)
        axes[1].set_ylabel("Prediction Confidence")
        axes[1].legend(loc='upper right')
        axes[1].set_ylim(0, 1.1)

    # Third subplot: Spectrogram
    specgram_index = 2 if not simplified else 1
    axes[specgram_index].specgram(trace[0].data, NFFT=1024, Fs=trace[0].stats.sampling_rate, noverlap=512,
                                  cmap='viridis')
    axes[specgram_index].set_ylabel('Frequency [Hz]')
    axes[specgram_index].set_xlabel('Time [s]')

    # Add vertical lines for detected and predicted seismic phases
    for t, color, style, label in [(detected_p_time, "C0", "-", "Detected P Arrival"),
                                   (detected_s_time, "C1", "-", "Detected S Arrival"),
                                   (predicted_p_time, "C0", "--", "Predicted P Arrival"),
                                   (predicted_s_time, "C1", "--", "Predicted S Arrival")]:
        if t:
            t_utc = t
            axes[0].axvline(x=t_utc - start_time, color=color, linestyle=style, label=label, linewidth=0.8)

    # Title and other details
    event_time = earthquake.time.strftime('%Y-%m-%d %H:%M:%S')
    axes[0].set_title(
        f'Detection of Event {event_time} - Lat: {earthquake.lat}, Long: {earthquake.long} - Magnitude: {earthquake.mag} {earthquake.mag_type}',
        fontsize=15)
    axes[0].set_xlim(0, end_time - start_time)

    # Values for x-axis
    x_ticks = np.arange(0, end_time - start_time + 1, 60)
    x_labels = [(start_time + t).strftime('%H:%M:%S') for t in x_ticks]
    for ax in axes:
        ax.set_xticks(x_ticks)
        ax.set_xticklabels(x_labels, rotation=0)

    # Add all labels to the legend
    handles, labels = axes[0].get_legend_handles_labels()
    axes[0].legend(handles, labels, loc='upper right')

    # Save the figure if a path is provided
    if path:
        file_path = os.path.join(path, f'{earthquake.unique_id}.png')
        plt.savefig(file_path)
        plt.close(fig)
        return file_path

    plt.close(fig)
    return None


def plot_detected_p_only(stream, annotated_stream, earthquake, path=None, simplified=False):
    # Extract P-wave times directly from Earthquake object
    detected_p_time = earthquake.p_detected
    predicted_p_time = earthquake.p_predicted

    # Calculate the time range for slicing the stream focused on P-wave
    if detected_p_time and predicted_p_time:
        starttime = min(detected_p_time, predicted_p_time) - 10
        endtime = max(detected_p_time, predicted_p_time) + 10
    else:
        print("Missing P-wave time data.")
        return None

    trace = stream.slice(starttime=starttime, endtime=endtime)
    if trace.count() == 0:
        print("No data in the trace.")
        return None

    start_time = trace[0].stats.starttime
    end_time = trace[0].stats.endtime

    fig, axes = plt.subplots(2 if simplified else 3, 1, figsize=(13, 6 if simplified else 9), sharex=True,
                             gridspec_kw={'hspace': 0.04, 'height_ratios': [1, 1] if simplified else [1, 1, 1]})

    # First subplot: Normalized Waveform Plot
    axes[0].plot(trace[0].times(), trace[0].data / np.amax(np.abs(trace[0].data)), 'k', label=trace[0].stats.channel)
    axes[0].set_ylabel('Normalized Amplitude')

    # Second subplot: Prediction Confidence Plot if not simplified
    if not simplified:
        for pred_trace in annotated_stream:
            model_name, pred_class = pred_trace.stats.channel.split("_")
            # Only display predictions for P and Detection
            if pred_class in ["P", "De"]:
                c = {"P": "C0", "De": "#008000"}.get(pred_class, "black")
                offset = pred_trace.stats.starttime - start_time
                label = "Detection" if pred_class == "De" else "P Wave"
                axes[1].plot(offset + pred_trace.times(), pred_trace.data, label=label, c=c)
        axes[1].set_ylabel("Prediction Confidence")
        axes[1].legend(loc='upper right')
        axes[1].set_ylim(0, 1.1)

    # Third subplot: Spectrogram
    specgram_index = 1 if simplified else 2
    axes[specgram_index].specgram(trace[0].data, NFFT=1024, Fs=trace[0].stats.sampling_rate, noverlap=512,
                                  cmap='viridis')
    axes[specgram_index].set_ylabel('Frequency [Hz]')
    axes[specgram_index].set_xlabel('Time [s]')

    # Add vertical lines for detected and predicted P-wave times
    for t, color, style, label in [(detected_p_time, "C0", "-", "Detected P Arrival"),
                                   (predicted_p_time, "C0", "--", "Predicted P Arrival")]:
        if t:
            t_utc = t
            axes[0].axvline(x=t_utc - start_time, color=color, linestyle=style, label=label, linewidth=0.8)

    # Title and other details
    event_time = earthquake.time.strftime('%Y-%m-%d %H:%M:%S')
    axes[0].set_title(
        f'Detection of Event {event_time} - Lat: {earthquake.lat}, Long: {earthquake.long} - Magnitude: {earthquake.mag} {earthquake.mag_type}',
        fontsize=15)
    axes[0].set_xlim(0, end_time - start_time)

    # x-axis labels
    num_ticks = 5  # Ensure 4-5 ticks regardless of time span
    x_ticks = np.linspace(0, end_time - start_time, num_ticks)
    x_labels = [(start_time + t).strftime('%H:%M:%S') for t in x_ticks]
    for ax in axes:
        ax.set_xticks(x_ticks)
        ax.set_xticklabels(x_labels, rotation=0)

    # Legend
    handles, labels = axes[0].get_legend_handles_labels()
    axes[0].legend(handles, labels, loc='upper right')

    # Save and close the plot
    if path:
        file_path = os.path.join(path, f'{earthquake.unique_id}.png')
        plt.savefig(file_path)
        plt.close(fig)
        return file_path

    plt.close(fig)
    return None


class Earthquake:
    def __init__(self, unique_id, provider, event_id, time, lat, long, mag, mag_type, depth, epi_distance,
                 p_predicted, s_predicted, p_detected=None, s_detected=None,
                 p_confidence=None, s_confidence=None, p_error=None, s_error=None, catalogued=True, detected=False):
        self.unique_id = unique_id
        self.provider = provider
        self.event_id = event_id
        self.time = UTCDateTime(time)
        self.lat = lat
        self.long = long
        self.mag = mag
        self.mag_type = mag_type
        self.depth = depth
        self.epi_distance = epi_distance
        self.p_predicted = UTCDateTime(p_predicted) if p_predicted else None
        self.s_predicted = UTCDateTime(s_predicted) if s_predicted else None

        self.p_detected = UTCDateTime(p_detected) if p_detected else None
        self.s_detected = UTCDateTime(s_detected) if s_detected else None
        self.p_confidence = p_confidence
        self.s_confidence = s_confidence
        self.p_error = p_error
        self.s_error = s_error
        self.catalogued = catalogued
        self.detected = detected
        self.plot_path = None  # Store the path of the generated plot

    def __str__(self):
        return (f"Earthquake ID: {self.unique_id}\n"
                f"Provider: {self.provider}\n"
                f"Provider Event ID: {self.event_id}\n"
                f"Time: {self.time}\n"
                f"Latitude: {self.lat}, Longitude: {self.long}\n"
                f"Depth: {self.depth} km\n"
                f"Magnitude: {self.mag} {self.mag_type}\n"
                f"Epicentral Distance: {self.epi_distance} km\n"
                f"P Predicted: {self.p_predicted}, S Predicted: {self.s_predicted}\n"
                f"P Detected: {self.p_detected}, S Detected: {self.s_detected}\n"
                f"P Confidence: {self.p_confidence}, S Confidence: {self.s_confidence}\n"
                f"P Error: {self.p_error}, S Error: {self.s_error}\n"
                f"Catalogued: {'Yes' if self.catalogued else 'No'}, Detected: {'Yes' if self.detected else 'No'}\n"
                "----------------------------------------")

    def update_errors(self):
        self.p_error = calculate_time_error(self.p_predicted, self.p_detected)
        self.s_error = calculate_time_error(self.s_predicted, self.s_detected)

    def update_distance(self, station_lat, station_lon):
        if self.lat is not None and self.long is not None:
            self.epi_distance = locations2degrees(station_lat, station_lon, self.lat, self.long) * 111.195  # Convert to km
        else:
            self.epi_distance = None

    def generate_plot(self, stream, predictions, path=None, simplified=False, p_only=False):
        if p_only:
            self.plot_path = plot_detected_p_only(stream, predictions, self, path, simplified)
        else:
            self.plot_path = plot_detected(stream, predictions, self, path, simplified)
