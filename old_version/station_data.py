# Dependencies
import datetime
import os
import time

# Function for downloading data from given station and returns availability
import numpy as np
import requests
from obspy import UTCDateTime, read
from obspy.clients.fdsn import Client
from obspy.clients.fdsn.header import FDSNNoDataException


# Generate a consistently formatted path using station and dates to store the files
def generate_data_path(date, station_information):
    if isinstance(date, UTCDateTime):
        date_str = date.strftime('%Y-%m-%d')
    elif isinstance(date, str):
        date_str = date
    else:
        raise ValueError("Date must be a UTCDateTime object or a string in 'YYYY-MM-DD' format")

    network, station = station_information[:2]

    # Construct the directory path
    base_dir = os.getcwd()
    full_path = os.path.join(base_dir, "data", f"{network}.{station}", date_str)

    return full_path


# Request stream from station and return path to the downloaded mseed file.
def download_stream(date, station_information, path=None, overwrite=False):
    network, station, data_provider = station_information
    location = "*"
    channel = "*Z*"

    datestr = date.strftime("%Y-%m-%d")
    if not path:
        cur_dir = os.getcwd()
        path = os.path.join(cur_dir, "data", f"{network}.{station}", datestr)

    # Construct the path but do not create the directory yet
    nslc = "{}.{}.{}.{}".format(network, station, location, channel).replace("*", "")
    client = Client(data_provider)
    fn = os.path.join(path, f"{datestr}_{nslc}.mseed")  # Filename includes date

    # Check if the file exists and the overwrite flag
    if os.path.isfile(fn) and not overwrite:
        print(f"Data for {datestr} already exist.")
        return fn  # Return the path to the existing file

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
            # Ensure the directory exists just before writing the file
            os.makedirs(path, exist_ok=True)
            st.write(fn)
            print(f"Data for {datestr} downloaded.")
            break
        except FDSNNoDataException:
            print(f"No data available for {datestr}.")
            return None
        except Exception as e:
            if "429" in str(e) or "502" in str(e) or "rate limit" in str(e).lower():
                print("Rate limit exceeded, waiting for 60 seconds.")
                time.sleep(60)
                continue
            else:
                print(f"An error occurred for {datestr}: {str(e)}")
                return None

    return fn  # Return the full file path of the downloaded data


# Load and read downloaded mseed from file path
def get_stream(date, station_information):
    network, station, _ = station_information
    cur_dir = os.getcwd()
    date_str = date.strftime('%Y-%m-%d')
    data_dir = os.path.join(cur_dir, "data", f"{network}.{station}", date_str)

    file_name = f"{network}.{station}..Z.mseed"
    file_path = os.path.join(data_dir, file_name)

    if os.path.exists(file_path):
        stream = read(file_path)
        print("Stream loaded from file.")
        print('-' * 40)
        return stream
    else:
        print("No file found for the specified date and station.")
        return None


# Download instrument response file
def download_response_file(station_information):
    network, station, base_url = station_information
    url = f"{base_url}/fdsnws/station/1/query?level=resp&network={network}&station={station}"

    cur_dir = os.getcwd()
    data_dir = os.path.join(cur_dir, "data", f"{network}.{station}")

    os.makedirs(data_dir, exist_ok=True)
    file_path = os.path.join(data_dir, f"{network}_{station}_response.xml")

    try:
        response = requests.get(url)
        response.raise_for_status()

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
