from obspy import UTCDateTime

from DataDownload import download_seismic_data_multiple, download_seismic_data_single
from DataProcessing import plot_mseed_data


# Set the date and station for downloading
date = UTCDateTime("2024-04-03")
station = ['GB', 'EDMD', 'IRIS']

# Download and organize data
# download_seismic_data_single(date)


graph = plot_mseed_data(date, station)
graph.plot()
