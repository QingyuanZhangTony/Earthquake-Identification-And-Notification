import os
from obspy import UTCDateTime
from obspy import read


def get_mseed_file(date, station_info):
    network, station, data_provider = station_info
    dataset_folder = f"{network}.{station}"
    cur_dir = os.getcwd()
    data_dir = os.path.join(cur_dir, dataset_folder)

    # Find the mseed file with specified date and station
    file_name = f"{date.strftime('%Y-%m-%d')}_{network}.{station}..Z.mseed"
    file_path = os.path.join(data_dir, file_name)

    if os.path.exists(file_path):
        stream = read(file_path)
        return stream
    else:
        print(f"No data available for {date.strftime('%Y-%m-%d')}")


def data_processing(mseed_file):
    mseed_file.detrend("demean")
    mseed_file.detrend("linear")

    # High-pass filter
    mseed_file.filter("highpass", freq=1.0)
    return mseed_file


# Usage Example
date = UTCDateTime("2024-04-03")
station = ['GB', 'EDMD', 'IRIS']

seismic_data = get_mseed_file(date, station)
data_processing(seismic_data)

seismic_data.plot()
