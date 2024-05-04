# Dependencies
import datetime
import os
import time

import numpy as np
import requests
from obspy import UTCDateTime, read
from obspy.clients.fdsn import Client
from obspy.clients.fdsn.client import FDSNNoDataException

# Function for downloading data from given station and returns availability
import os
import numpy as np
from obspy import UTCDateTime, read
from obspy.clients.fdsn import Client
from obspy.clients.fdsn.header import FDSNNoDataException


def download_stream(date, station_information, overwrite=False):
    network, station, data_provider = station_information
    location = "*"
    channel = "*Z*"

    cur_dir = os.getcwd()
    dataset_dir = os.path.join(cur_dir, "data", f"{network}.{station}")

    os.makedirs(dataset_dir, exist_ok=True)

    nslc = "{}.{}.{}.{}".format(network, station, location, channel).replace("*", "")
    client = Client(data_provider)
    datestr = date.strftime("%Y-%m-%d")
    fn = os.path.join(dataset_dir, "{}_{}.mseed".format(datestr, nslc))

    # Check if the file exists and the overwrite flag
    if os.path.isfile(fn) and not overwrite:
        print(f"Data for {datestr} already exist.")
        return get_stream(date, station_information)

    print(f"Fetching data for {datestr}")
    while True:
        try:
            st = client.get_waveforms(network, station, location, channel,
                                      UTCDateTime(date) - 3600, UTCDateTime(date) + 90000,
                                      attach_response=True)
            st.merge()
            for tr in st:
                if isinstance(tr.data, np.ma.masked_array):
                    tr.data = tr.data.filled()
            st.write(fn)
            print(f"Data for {datestr} downloaded.")
            break
        except FDSNNoDataException:
            print(f"No data available for {datestr}.")
            return None
        except Exception as e:
            if "429" in str(e) or "rate limit" in str(e).lower():
                print("Rate limit exceeded, waiting for 60 seconds.")
                time.sleep(60)
                continue
            else:
                print(f"An error occurred for {datestr}: {str(e)}")
                return None

    return get_stream(date, station_information)


def get_stream(date, station_information):
    network, station, _ = station_information
    cur_dir = os.getcwd()
    data_dir = os.path.join(cur_dir, "data", f"{network}.{station}")

    file_name = f"{date.strftime('%Y-%m-%d')}_{network}.{station}..Z.mseed"
    file_path = os.path.join(data_dir, file_name)

    if os.path.exists(file_path):
        stream = read(file_path)
        print("Stream loaded from file.")
        print('-' * 40)
        return stream
    else:
        print("No file found for the specified date and station.")
        return None


def download_response_file(station_information):
    network, station, base_url = station_information
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


def get_coordinates(station_information):
    try:
        if len(station_information) != 3:
            raise ValueError(
                "station_info list must contain exactly three elements: network, station, and service_url.")

        network, station, service_url = station_information

        # Create an instance of the FDSN client
        client = Client(service_url)

        # Get current time for the endtime to ensure the station metadata is up-to-date
        endtime = UTCDateTime()

        # Fetch station metadata
        inventory = client.get_stations(network=network, station=station, endtime=endtime, level='station')

        # Extract latitude and longitude from the inventory
        station_information = inventory[0][0]  # Assumes only one station matches the query
        latitude = station_information.latitude
        longitude = station_information.longitude
        return (latitude, longitude)
    except Exception as e:
        print(f"Error fetching station coordinates: {e}")
        return None


# For testing
if __name__ == "__main__":

    station_info = ['AM', 'R50D6', 'https://data.raspberryshake.org']
    start_date = UTCDateTime("2023-06-19")

    end_date = UTCDateTime()
    num_days = (end_date - start_date) / (24 * 3600)
    date_list = [start_date + datetime.timedelta(days=x) for x in range(int(num_days) + 1)]

    for date in date_list:
        download_stream(date, station_info, overwrite=False)
