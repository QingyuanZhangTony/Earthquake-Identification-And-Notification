# Dependencies
import os
import time
from datetime import time
from datetime import timedelta

import matplotlib
import requests
from obspy import read

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
        while True:
            try:
                # Request waveform data from the service
                st = client.get_waveforms(network, station, location, channel,
                                          UTCDateTime(date) - 3600, UTCDateTime(date) + 90000,
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
                if "429" in str(e) or "rate limit" in str(e).lower():
                    print("Rate limit exceeded, waiting for 60 seconds.")
                    time.sleep(60)
                    continue
                else:
                    print(f"An error occurred for {datestr}: {str(e)}")
                    return False
    else:
        print(f"Data for {datestr} already downloaded.")
        return True


def download_response_file(station_info):
    network, station, base_url = station_info
    url = f"{base_url}/fdsnws/station/1/query?level=resp&network={network}&station={station}"

    # Define the directory path where the file will be saved
    cur_dir = os.getcwd()  # Get the current working directory
    data_dir = os.path.join(cur_dir, "data", f"{network}.{station}")

    # Create the directory if it does not exist
    os.makedirs(data_dir, exist_ok=True)

    # Define the file path
    file_path = os.path.join(data_dir, f"{network}_{station}_response.xml")

    try:
        # Send a GET request to the URL
        response = requests.get(url)
        response.raise_for_status()  # Check for HTTP errors

        # Write the content to an XML file
        with open(file_path, 'wb') as f:
            f.write(response.content)
        print(f"Response file saved as: {file_path}")
        return file_path

    except requests.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        return None
    except Exception as err:
        print(f"An error occurred: {err}")
        return None


def download_seismic_data_range(station_info, start_date, end_date, download_function):
    current_date = start_date

    while current_date <= end_date:
        utc_date = UTCDateTime(current_date)

        successful_download = download_function(utc_date, station_info)
        if not successful_download:
            print(f"Download failed for {current_date}")

        current_date += timedelta(days=1)


def get_stream(date, station_info):
    network, station, data_provider = station_info
    dataset_folder = f"{network}.{station}"
    cur_dir = os.getcwd()
    # Include the 'data' directory in the path
    data_dir = os.path.join(cur_dir, "data", dataset_folder)

    # Find the mseed file with the specified date and station
    file_name = f"{date.strftime('%Y-%m-%d')}_{network}.{station}..Z.mseed"
    file_path = os.path.join(data_dir, file_name)

    # Read the stream from the mseed file
    stream = read(file_path)
    return stream
