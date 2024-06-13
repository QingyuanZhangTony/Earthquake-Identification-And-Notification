import os

import numpy as np
import requests
from obspy.clients.fdsn import Client
from obspy.core import UTCDateTime
from obspy import read, Stream
from obspy.clients.fdsn.header import FDSNNoDataException


class Station:
    def __init__(self, network, code, url, report_date):
        self.network = network
        self.code = code
        self.url = url
        self.latitude = None
        self.longitude = None
        self.date_folder = None
        self.report_date = UTCDateTime(report_date)
        self.report_folder = None
        # self.instrument_response = None

        self.generate_path(report_date)
        self.fetch_coordinates()

    def generate_path(self, date):
        if isinstance(date, UTCDateTime):
            date_str = date.strftime('%Y-%m-%d')
        elif isinstance(date, str):
            date_str = date
        else:
            raise ValueError("Date must be a UTCDateTime object or a string in 'YYYY-MM-DD' format")

        # Construct the directory paths
        base_dir = os.getcwd()
        self.date_folder = os.path.join(base_dir, "data", f"{self.network}.{self.code}", date_str)
        self.report_folder = os.path.join(self.date_folder, "report")

        # Ensure the directories exist
        os.makedirs(self.date_folder, exist_ok=True)
        os.makedirs(self.report_folder, exist_ok=True)

    def download_stream_data(self, overwrite=True):
        channel = "*Z*"
        location = "*"
        date_str = self.report_date.strftime("%Y-%m-%d")
        path = self.date_folder

        nslc = f"{self.network}.{self.code}.{location}.{channel}".replace("*", "")
        filename = f"{date_str}_{nslc}.mseed"
        filepath = os.path.join(path, filename)

        if os.path.isfile(filepath) and not overwrite:
            print(f"Data for {date_str} already exists.")
            return filepath

        client = Client(self.url)
        start_time = self.report_date - 3600
        end_time = self.report_date + 90000
        duration = int((end_time - start_time) / 3)
        full_stream = Stream()

        for i in range(3):
            part_start = start_time + i * duration
            part_end = part_start + duration if i < 2 else end_time
            try:
                partial_st = client.get_waveforms(self.network, self.code, location, channel, part_start, part_end,
                                                  attach_response=True)
                partial_st.merge()
                for tr in partial_st:
                    if isinstance(tr.data, np.ma.masked_array):
                        tr.data = tr.data.filled(fill_value=0)
                full_stream += partial_st
                print(f"Part {i + 1} downloaded for {date_str}.")
            except Exception as e:
                print(f"Failed to download part {i + 1} of the data: {e}")
                return None

        full_stream.merge()
        os.makedirs(path, exist_ok=True)
        full_stream.write(filepath)
        print(f"Data for {date_str} successfully downloaded and combined.")
        return filepath

    def download_response_file(self):
        url = f"{self.url}/fdsnws/station/1/query?level=response&network={self.network}&station={self.code}"
        path = os.path.join(os.getcwd(), "data", f"{self.network}.{self.code}")
        filepath = os.path.join(path, f"{self.network}_{self.code}_response.xml")

        try:
            response = requests.get(url)
            response.raise_for_status()
            with open(filepath, 'wb') as file:
                file.write(response.content)
            print(f"Response file saved as: {filepath}")
            return filepath
        except requests.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
            return None
        except Exception as err:
            print(f"An error occurred: {err}")
            return None

    def fetch_coordinates(self):
        try:
            client = Client(self.url)
            endtime = UTCDateTime()
            inventory = client.get_stations(network=self.network, station=self.code, endtime=endtime, level='station')
            self.latitude = inventory[0][0].latitude
            self.longitude = inventory[0][0].longitude
        except Exception as e:
            print(f"Error fetching station coordinates: {e}")


    def __str__(self):
        return (f"Station {self.network}.{self.code} at {self.url}\n"
                f"Location: {self.latitude}, {self.longitude}\n"
                f"Report Date: {self.report_date.strftime('%Y-%m-%d')}\n"
                f"Data Folder: {self.date_folder}\n"
                f"Report Folder: {self.report_folder}\n")

