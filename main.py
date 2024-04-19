from obspy import UTCDateTime

from DataDownload import download_seismic_data
from DataProcessing import get_mseed_file, data_processing, plot_graph

# Set the date and station for downloading
date = UTCDateTime("2024-04-03")
station = ['GB', 'EDMD', 'IRIS']

# Download and organize data
download_seismic_data(date, station)

# Data preprocessing
stream = get_mseed_file(date, station)
data_processing(stream)

plot_graph(stream)


