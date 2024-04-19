# Dependencies
import os
import matplotlib

matplotlib.rcParams['pdf.fonttype'] = 42  # to edit text in Illustrator
import numpy as np
from obspy import UTCDateTime
from obspy.clients.fdsn import Client
from obspy.clients.fdsn.client import FDSNNoDataException


# Function for downloading data from given station
def download_seismic_data(date, station_info):
    network, station, data_provider = station_info
    location = "*"
    channel = "*Z*"
    dataset = network + "." + station

    cur_dir = os.getcwd()
    dataset_dir = os.path.join(cur_dir, dataset)
    if not os.path.exists(dataset_dir):
        os.mkdir(dataset_dir)

    nslc = "{}.{}.{}.{}".format(network, station, location, channel).replace("*", "")
    client = Client(data_provider)
    datestr = date.strftime("%Y-%m-%d")
    # Download directly to network.station named folder
    fn = os.path.join(dataset_dir, "{}_{}.mseed".format(datestr, nslc))

    if not os.path.isfile(fn):
        print(f"Fetching data for {datestr}")
        try:
            st = client.get_waveforms(network, station, location, channel,
                                      UTCDateTime(date) - 1801, UTCDateTime(date) + 86400 + 1801,
                                      attach_response=True)
            st.merge()
            for tr in st:
                if isinstance(tr.data, np.ma.masked_array):
                    tr.data = tr.data.filled()
            st.write(fn)
            print(f"Data for {datestr} written successfully.")
        except FDSNNoDataException:
            print(f"No data available for {datestr}.")
        except Exception as e:
            print(f"An error occurred for {datestr}: {str(e)}")
    else:
        print(f"Data for {datestr} already downloaded.")

# Example Usage
# date = UTCDateTime("2024-04-01")
# station_to_download = ['GB', 'EDMD', 'IRIS']
# download_seismic_data(date, station_to_download)
