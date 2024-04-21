# Dependencies
import os
from datetime import timedelta

import matplotlib
import requests

matplotlib.rcParams['pdf.fonttype'] = 42  # to edit text in Illustrator
import numpy as np
from obspy import UTCDateTime
from obspy.clients.fdsn import Client
from obspy.clients.fdsn.client import FDSNNoDataException


# Function for downloading data from given station and returns availability
def download_seismic_data(date, station_info):
    network, station, data_provider = station_info
    location = "*"
    channel = "*Z*"
    # Define the path for the 'data' directory within the current working directory
    cur_dir = os.getcwd()
    dataset_dir = os.path.join(cur_dir, "data", f"{network}.{station}")

    # Create the 'data/dataset' directory if it does not exist, including any intermediate directories
    os.makedirs(dataset_dir, exist_ok=True)

    # Format the filename string
    nslc = "{}.{}.{}.{}".format(network, station, location, channel).replace("*", "")
    # Create a client object to interact with the FDSN web service
    client = Client(data_provider)
    # Format the date string
    datestr = date.strftime("%Y-%m-%d")
    # Create the full path for the miniSEED file
    fn = os.path.join(dataset_dir, "{}_{}.mseed".format(datestr, nslc))

    # Check if the file already exists
    if not os.path.isfile(fn):
        print(f"Fetching data for {datestr}")
        try:
            # Request waveform data from the service
            st = client.get_waveforms(network, station, location, channel,
                                      UTCDateTime(date) - 1801, UTCDateTime(date) + 86400 + 1801,
                                      attach_response=True)
            # Merge any split traces
            st.merge()
            # Fill any gaps in the data
            for tr in st:
                if isinstance(tr.data, np.ma.masked_array):
                    tr.data = tr.data.filled()
            # Write the data to a miniSEED file
            st.write(fn)
            print(f"Data for {datestr} written successfully.")
            return True
        except FDSNNoDataException:
            print(f"No data available for {datestr}.")
            return False
        except Exception as e:
            print(f"An error occurred for {datestr}: {str(e)}")
            return False
    else:
        print(f"Data for {datestr} already downloaded.")
        return True


def download_seismic_data_all_channel(date, station_info):
    network, station, data_provider = station_info
    location = "*"
    channel = "*Z*"
    # Define the path for the 'data' directory within the current working directory
    cur_dir = os.getcwd()
    dataset_dir = os.path.join(cur_dir, "data", f"{network}.{station}")

    # Create the 'data/dataset' directory if it does not exist, including any intermediate directories
    os.makedirs(dataset_dir, exist_ok=True)

    nslc = "{}.{}.{}.{}".format(network, station, location, channel).replace("*", "")
    client = Client(data_provider)
    datestr = date.strftime("%Y-%m-%d")
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
            return True
        except FDSNNoDataException:
            print(f"No data available for {datestr}.")
            return False
        except Exception as e:
            print(f"An error occurred for {datestr}: {str(e)}")
            return False
    else:
        print(f"Data for {datestr} already downloaded.")
        return True


def download_from_raspberryshake(date, station_info):
    network, station, service_url = station_info
    location = ""
    channel = "Z"  # Adjust based on the actual channel you need to fetch

    # Directory and file naming
    dataset = f"{network}.{station}"
    cur_dir = os.getcwd()
    dataset_dir = os.path.join(cur_dir, dataset)
    if not os.path.exists(dataset_dir):
        os.makedirs(dataset_dir)

    # Construct filename and path
    datestr = date.strftime("%Y-%m-%d")
    filename = f"{datestr}_{network}.{station}..{channel}.mseed"
    filepath = os.path.join(dataset_dir, filename)

    # Check if the file already exists
    if os.path.isfile(filepath):
        print(f"Data for {datestr} already downloaded.")
        return True

    # Calculate start and end times
    start_time = date - timedelta(days=0, minutes=30)  # 23:30 the day before
    end_time = date + timedelta(days=1, minutes=30)  # 00:30 the day after

    # Format times for the URL and filename
    start_time_str = start_time.strftime('%Y-%m-%dT%H_%M_%S')
    end_time_str = end_time.strftime('%Y-%m-%dT%H_%M_%S')

    # Build the request URL
    base_url = f"{service_url}/fdsnws/dataselect/1/query"
    url = f"{base_url}?starttime={start_time_str}&endtime={end_time_str}&network={network}&station={station}"

    try:
        # Send request to download data
        response = requests.get(url)
        if response.status_code == 200 and response.content:
            # Save the MiniSEED file
            with open(filepath, 'wb') as f:
                f.write(response.content)
            print(f"Downloaded MiniSEED data to {filepath}")
            return True
        else:
            print("No data returned from the server.")
            return False
    except requests.RequestException as e:
        print(f"Failed to download MiniSEED data: {e}")
        return False
