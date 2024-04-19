from obspy.signal.filter import bandpass
import os
from obspy import UTCDateTime
from obspy import read


def get_stream(date, station_info):
    network, station, data_provider = station_info
    dataset_folder = f"{network}.{station}"
    cur_dir = os.getcwd()
    data_dir = os.path.join(cur_dir, dataset_folder)

    # Find the mseed file with specified date and station
    file_name = f"{date.strftime('%Y-%m-%d')}_{network}.{station}..Z.mseed"
    file_path = os.path.join(data_dir, file_name)

    stream = read(file_path)
    return stream


def data_processing(stream):
    stream.detrend("demean")
    stream.detrend("linear")

    # High-pass filter
    # mseed_file.filter("highpass", freq=1.0)
    for trace in stream:
        trace.data = bandpass(trace.data, freqmin=0.1, freqmax=40, df=trace.stats.sampling_rate, corners=5)

    return stream


def plot_graph(stream):
    stream.plot()
