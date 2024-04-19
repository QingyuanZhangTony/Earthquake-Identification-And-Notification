import sys

from obspy import UTCDateTime

from DataDownload import download_seismic_data
from DataProcessing import get_stream, data_processing, plot_graph

# Set the date and station for downloading
date = UTCDateTime("2024-04-03")
station = ['GB', 'EDMD', 'IRIS']

# Try to download data and return availability for the date
success = download_seismic_data(date, station)

# Exit if data not available
if not success:
    print("Stopping execution due to no data available.")
    sys.exit()

# Data preprocessing
stream = get_stream(date, station)
data_processing(stream)

plot_graph(stream)


