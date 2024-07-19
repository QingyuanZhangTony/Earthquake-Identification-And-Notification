import os
import numpy as np
from obspy import UTCDateTime, read, Stream
from obspy.clients.fdsn import Client
from obspy.clients.fdsn.header import FDSNNoDataException

from stream import StreamData
import os
import numpy as np
from obspy import Stream, read
from obspy.clients.fdsn import Client
import time
class Station:
    def __init__(self, network, code, url, report_date=None,latitude=None, longitude=None,):
        self.network = network
        self.code = code
        self.url = url
        self.report_date = UTCDateTime(report_date) if report_date else UTCDateTime()

        self.latitude = latitude
        self.longitude = longitude
        self.station_folder = None
        self.date_folder = None
        self.report_folder = None
        self.monitoring_folder = None

        self.stream = StreamData(self)

        self.generate_path(self.report_date)
        self.fetch_coordinates()

    def __str__(self):
        return (f"Station {self.network}.{self.code} at {self.url}\n"
                f"Location: {self.latitude}, {self.longitude}\n"
                f"Report Date: {self.report_date.strftime('%Y-%m-%d')}\n"
                f"Data Folder: {self.date_folder}\n"
                f"Report Folder: {self.report_folder}\n")

    def fetch_coordinates(self):
        retry_count = 1  # Set the number of retries
        while retry_count >= 0:
            try:
                client = Client(self.url)
                endtime = UTCDateTime()
                inventory = client.get_stations(network=self.network, station=self.code, endtime=endtime,
                                                level='station')
                self.latitude = inventory[0][0].latitude
                self.longitude = inventory[0][0].longitude
                print("Coordinates fetched successfully.")
                break  # Break the loop if success
            except Exception as e:
                if '502' in str(e):
                    print(f"HTTP 502 error encountered: Retrying after 15 seconds...")
                    time.sleep(15)  # Wait for 15 seconds before retrying
                    retry_count -= 1  # Decrement the retry counter
                else:
                    print(f"Error fetching station coordinates: {e}")
                    break  # Exit loop if the error is not related to HTTP 502

        if retry_count < 0:
            print("Failed to fetch coordinates after retrying. Error: HTTP 502 Bad Gateway")

    def generate_path(self, date):
        if isinstance(date, UTCDateTime):
            date_str = date.strftime('%Y-%m-%d')
        elif isinstance(date, str):
            date_str = date
        else:
            raise ValueError("Date must be a UTCDateTime object or a string in 'YYYY-MM-DD' format")

        # Construct the directory paths
        base_dir = os.getcwd()
        self.station_folder = os.path.join(base_dir, "data", f"{self.network}.{self.code}")
        self.date_folder = os.path.join(self.station_folder, date_str)
        self.report_folder = os.path.join(self.date_folder, "report")
        # self.monitoring_folder = os.path.join(self.date_folder, "monitoring")

        # Ensure the directories exist
        os.makedirs(self.station_folder, exist_ok=True)
        os.makedirs(self.date_folder, exist_ok=True)
        os.makedirs(self.report_folder, exist_ok=True)
        #os.makedirs(self.monitoring_folder, exist_ok=True)

    def download_day_stream(self, overwrite=True):
        channel = "*Z*"
        location = "*"
        date_str = self.report_date.strftime("%Y-%m-%d")
        path = self.date_folder

        nslc = f"{self.network}.{self.code}.{location}.{channel}".replace("*", "")
        filename = f"{date_str}_{nslc}.mseed"
        filepath = os.path.join(path, filename)

        # 初始化返回状态
        status = None
        message = ""

        if os.path.isfile(filepath) and not overwrite:
            self.stream.original_stream = read(filepath)  # Read and set the stream object
            status = "exists"
            message = f"Data for {date_str} already exists."
        else:
            client = Client(self.url)
            start_time = self.report_date - 300
            end_time = self.report_date + 86700
            duration = int((end_time - start_time) / 3)
            full_stream = Stream()
            download_successful = True

            for i in range(3):
                part_start = start_time + i * duration
                part_end = part_start + duration if i < 2 else end_time
                try:
                    partial_st = client.get_waveforms(self.network, self.code, location, channel, part_start, part_end,
                                                      attach_response=True)
                    partial_st.merge(method=0)  # Ensure no overlapping data, handle merging logic based on your data
                    for tr in partial_st:
                        if isinstance(tr.data, np.ma.masked_array):
                            tr.data = tr.data.filled(
                                fill_value=0)  # Fill masked values before adding to the full stream
                    full_stream += partial_st
                    # message += f"Part {i + 1} downloaded for {date_str}.\n"
                    print(f"Part {i + 1} downloaded for {date_str}.\n")
                except Exception as e:
                    message += f"Failed to download part {i + 1} of the data: {e}\n"
                    download_successful = False
                    break

            if download_successful and full_stream.count() > 0:
                full_stream.merge(method=0)  # Final merge before writing
                # Convert any remaining masked arrays if they exist
                for tr in full_stream:
                    if isinstance(tr.data, np.ma.masked_array):
                        tr.data = tr.data.filled(fill_value=0)
                os.makedirs(path, exist_ok=True)
                full_stream.write(filepath)
                self.stream.original_stream = full_stream
                status = "success"
            else:
                status = "error"
                if full_stream.count() == 0:
                    message += f"No data available for {date_str}."

        return {"status": status, "message": message.strip(), "filepath": filepath if status != "error" else None}
