import numpy as np
import seisbench.models as sbm
import torch
from Other.utils import *
from obspy.core import AttribDict
from obspy.signal.filter import bandpass


class StreamData:
    def __init__(self, station, stream=None):
        self.station = station
        self.original_stream = stream
        self.processed_stream = None
        self.annotated_stream = None
        self.picked_signals = None

    def process_stream(self, detrend_demean=True, detrend_linear=True, remove_outliers=True,
                       apply_bandpass=True, taper=True, denoise=True):
        if self.original_stream is None:
            raise ValueError("Original stream is not set.")

        # Create a copy of the original stream to process
        stream_to_process = self.original_stream.copy()

        if detrend_demean:
            # Remove the mean from the data
            stream_to_process.detrend("demean")

        if detrend_linear:
            # Remove the linear trend from the data
            stream_to_process.detrend("linear")

        for trace in stream_to_process:
            if remove_outliers:
                # Remove outliers from the trace
                trace = self.remove_outliers(trace)

            if apply_bandpass:
                # Apply a bandpass filter to the trace data
                freqmin = 1
                freqmax = 40
                corners = 5
                df = trace.stats.sampling_rate
                trace.data = bandpass(trace.data, freqmin=freqmin, freqmax=freqmax, df=df, corners=corners)

        if taper:
            for trace in stream_to_process:
                trace.taper(max_percentage=0.05, type="hann")

        if denoise:
            stream_to_process = self.denoise(stream_to_process)

        self.processed_stream = stream_to_process

    def denoise(self, stream):
        return denoise_stream(stream)

    def remove_outliers(self, trace, threshold_factor=2):
        return remove_outliers_threshold(trace, threshold_factor)

    def predict_and_annotate(self):
        self.picked_signals, self.annotated_stream = predict_and_annotate(self.processed_stream)

    def filter_confidence(self, p_threshold, s_threshold):
        # Filter detections based on threshold conditions
        self.picked_signals = [
            detection for detection in self.picked_signals
            if (detection['phase'] == "P" and detection['peak_confidence'] >= p_threshold) or
               (detection['phase'] == "S" and detection['peak_confidence'] >= s_threshold)
        ]

    def save_stream(self, station, stream_to_save, identifier="processed", path=None):
        if not stream_to_save:
            raise ValueError("No stream to save.")

        channel = "*Z*"
        location = "*"

        # Format the filename with NSLC and suffix based on file_type
        nslc = f"{station.network}.{station.code}.{location}.{channel}".replace("*", "")
        filename = f"{station.report_date.strftime('%Y-%m-%d')}_{nslc}.{identifier}.mseed"

        # Determine the target directory
        target_path = path if path else station.date_folder

        filepath = os.path.join(target_path, filename)

        # Ensure the directory exists
        os.makedirs(target_path, exist_ok=True)

        # 确认数据的 dtype
        dtype = stream_to_save[0].data.dtype
        encoding = None

        # 根据数据类型选择合适的编码
        if dtype == 'int32':
            encoding = 'STEIM2'
        elif dtype == 'float32':
            encoding = 'FLOAT32'
        elif dtype == 'float64':
            encoding = 'FLOAT64'
        elif dtype == 'int16':
            encoding = 'STEIM1'
        else:
            raise ValueError(f"Unsupported data type: {dtype}")

        # 设置每个 trace 的编码
        for trace in stream_to_save:
            if not hasattr(trace.stats, 'mseed'):
                trace.stats.mseed = AttribDict()
            trace.stats.mseed.encoding = encoding

        # Write the stream to a MiniSEED file
        stream_to_save.write(filepath, format='MSEED')
        print(f"Stream saved to {filepath}")


# Denoise stream with pretrained DeepDenoiser
def denoise_stream(stream):
    # Get pretrained model for denosing
    model = sbm.DeepDenoiser.from_pretrained("original")

    # Enable GPU processing if available
    if torch.cuda.is_available():
        torch.backends.cudnn.enabled = False
        model.cuda()
        print("CUDA available. Denosing using GPU")
    else:
        print("CUDA not available. Denosing using CPU")

    # Save original channel names
    original_channels = [tr.stats.channel for tr in stream]

    # Apply denoising model
    annotations = model.annotate(stream)

    # Restore original channel names
    for tr, channel in zip(annotations, original_channels):
        tr.stats.channel = channel

    return annotations


def remove_outliers_threshold(trace, threshold_factor=2):
    # Calculate global mean and standard deviation for the trace
    global_mean = trace.data.mean()
    global_std = trace.data.std()

    # Identify outliers as points beyond the threshold times the standard deviation from the mean
    outliers = np.abs(trace.data - global_mean) > (threshold_factor * global_std)
    trace.data[outliers] = global_mean  # Replace outliers with the global mean
    return trace


def predict_and_annotate(processed_stream):
    # Get pretrained model for phase picking
    model = sbm.EQTransformer.from_pretrained("original")

    # Enable GPU processing if available
    if torch.cuda.is_available():
        torch.backends.cudnn.enabled = False
        model.cuda()
        print("CUDA available. Phase-picking using GPU")
    else:
        print("CUDA not available. Phase-picking using CPU")

    # Perform classification to extract picks
    outputs = model.classify(processed_stream)
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
    annotated_stream = model.annotate(processed_stream)

    # Adjust channel names in the annotated stream to include the original channel plus the model suffix
    for tr in annotated_stream:
        parts = tr.stats.channel.split('_')
        if len(parts) > 1:
            tr.stats.channel = '_' + '_'.join(parts[1:])  # Join parts starting from the first underscore

    return predictions, annotated_stream


# Methods for removing outliers

def remove_outliers_IQR(trace, threshold_factor=2):
    # Calculate outliers using the median and IQR
    median = np.median(trace.data)
    quartile1 = np.percentile(trace.data, 25)
    quartile3 = np.percentile(trace.data, 75)
    iqr = quartile3 - quartile1
    lower_bound = median - (threshold_factor * iqr)
    upper_bound = median + (threshold_factor * iqr)

    # Identify data points that are outside the boundaries
    outliers = (trace.data < lower_bound) | (trace.data > upper_bound)
    # Replace outliers with the median, or consider other replacement strategies
    trace.data[outliers] = median
    return trace


def remove_outliers_window(trace, window_size=10, threshold_factor=1.5):
    # Prepare an empty array to store the processed data
    filtered_data = np.copy(trace.data)

    # Iterate through the data, processing each window
    for i in range(len(trace.data)):
        # Calculate the start and end index for the window
        start_index = max(0, i - window_size // 2)
        end_index = min(len(trace.data), i + window_size // 2)

        # Extract data within the window
        window_data = trace.data[start_index:end_index]

        # Compute median and IQR within the window
        median = np.median(window_data)
        quartile1 = np.percentile(window_data, 25)
        quartile3 = np.percentile(window_data, 75)
        iqr = quartile3 - quartile1

        # Calculate boundaries for outliers
        lower_bound = median - (threshold_factor * iqr)
        upper_bound = median + (threshold_factor * iqr)

        # Check if the current point is an outlier and replace it if necessary
        if trace.data[i] < lower_bound or trace.data[i] > upper_bound:
            filtered_data[i] = median  # Replace outlier with window median

    # Update original data
    trace.data = filtered_data
    return trace


