# Dependencies
import os
import shutil
import glob
import matplotlib

matplotlib.rcParams['pdf.fonttype'] = 42  # to edit text in Illustrator
import numpy as np
import pandas as pd
from obspy import UTCDateTime
from obspy.clients.fdsn import Client
from obspy.clients.fdsn.client import FDSNNoDataException


# Function for downloading data from given station
def download_seismic_data_multiple(start_date, end_date, station_info):
    network, station, data_provider = station_info
    datelist = pd.date_range(start_date.datetime, min(end_date, UTCDateTime()).datetime, freq="D")
    location = "*"
    channel = "*Z*"
    dataset = network + "." + station

    cur_dir = os.getcwd()
    download_dir = os.path.join(cur_dir, "downloading")  # Define the download directory
    if not os.path.exists(download_dir):
        os.mkdir(download_dir)

    nslc = "{}.{}.{}.{}".format(network, station, location, channel).replace("*", "")

    client = Client(data_provider)
    print('Initializing download for', dataset)

    for day in datelist:
        datestr = day.strftime("%Y-%m-%d")
        fn = os.path.join(download_dir, "{}_{}.mseed".format(datestr, nslc))

        if not os.path.isfile(fn):
            print(f"Fetching data for {datestr}")
            try:
                st = client.get_waveforms(network, station, location, channel,
                                          UTCDateTime(day) - 1801, UTCDateTime(day) + 86400 + 1801,
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

    organize_downloaded_files(network, station)


def download_seismic_data_single(date, station_info):
    network, station, data_provider = station_info
    location = "*"
    channel = "*Z*"
    dataset = network + "." + station

    cur_dir = os.getcwd()
    download_dir = os.path.join(cur_dir, "downloading")
    if not os.path.exists(download_dir):
        os.mkdir(download_dir)

    nslc = "{}.{}.{}.{}".format(network, station, location, channel).replace("*", "")
    client = Client(data_provider)
    datestr = date.strftime("%Y-%m-%d")
    fn = os.path.join(download_dir, "{}_{}.mseed".format(datestr, nslc))

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


# Function for organizing downloaded data
def organize_downloaded_files(network, station):
    dataset = network + "." + station
    cur_dir = os.getcwd()
    download_dir = os.path.join(cur_dir, "downloading")
    dataset_path = os.path.join(cur_dir, dataset)

    if not os.path.exists(dataset_path):
        os.mkdir(dataset_path)

    files_to_move = glob.glob(os.path.join(download_dir, "*" + dataset + '*.mseed'))
    num_files_moved = 0
    num_files_skipped = 0

    for file2mv in files_to_move:
        target_file_path = os.path.join(dataset_path, os.path.basename(file2mv))
        if not os.path.exists(target_file_path):
            shutil.move(file2mv, target_file_path)
            num_files_moved += 1
        else:
            num_files_skipped += 1
            os.remove(file2mv)  # Remove the skipped file to clear the directory

    # Clear any remaining files and the directory if it's now empty
    remaining_files = glob.glob(os.path.join(download_dir, '*'))
    for file in remaining_files:
        os.remove(file)
    if not remaining_files:  # Check again if the folder is empty to remove it
        os.rmdir(download_dir)

    print(f"Moved {num_files_moved} files to {dataset_path}")
    if num_files_skipped > 0:
        print(f"{num_files_skipped} files already existed and were skipped.")


# Example Usage
# start = UTCDateTime("2024-04-01")
# end = UTCDateTime("2024-04-03")
# station_to_download = ['GB', 'EDMD', 'IRIS']
# download_seismic_data_multiple(start, end, station_to_download)
