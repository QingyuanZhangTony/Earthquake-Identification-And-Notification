import requests
from obspy.clients.fdsn import Client
from obspy.clients.fdsn.header import FDSNNoDataException, FDSNException
from obspy.core import UTCDateTime
from obspy.taup import TauPyModel
from obspy.geodetics import gps2dist_azimuth, locations2degrees
from earthquake import Earthquake
import os

import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image as PILImage
from matplotlib.legend_handler import HandlerLine2D


class Catalog:
    def __init__(self, station, radmin, radmax, minmag, maxmag):
        self.lat = station.latitude
        self.lon = station.longitude
        self.date = station.report_date
        self.radmin = radmin
        self.radmax = radmax
        self.minmag = minmag
        self.maxmag = maxmag
        self.events = None
        self.provider = None
        self.station = station

    def request_catalogue(self, catalogue_providers):
        starttime = self.date - 30 * 60  # 30 minutes before midnight on the day before
        endtime = self.date + (24 * 3600) + 30 * 60  # 30 minutes after midnight on the day after

        for provider in catalogue_providers:
            try:
                client = Client(provider)
                catalog = client.get_events(
                    latitude=self.lat,
                    longitude=self.lon,
                    minradius=self.radmin,
                    maxradius=self.radmax,
                    starttime=starttime,
                    endtime=endtime,
                    minmagnitude=self.minmag,
                    maxmagnitude=self.maxmag
                )

                if catalog.events:
                    self.events = catalog
                    self.provider = provider
                    return None

            except FDSNNoDataException as e:
                print(f"No data available from {provider} for the requested parameters: {e}")
            except FDSNException as e:
                print(f"Error fetching earthquake data from {provider}: {e}")
            except Exception as e:
                print(f"Unexpected error occurred when connecting to {provider}: {e}")

        print("Failed to retrieve earthquake data from all provided catalog sources.")
        return None

    def predict_arrivals(self, event):
        model = TauPyModel(model="iasp91")
        distance_deg = gps2dist_azimuth(
            event.origins[0].latitude, event.origins[0].longitude,
            self.lat, self.lon
        )[0] / 1000.0 / 111.195  # Convert meters to degrees

        arrivals = model.get_ray_paths(
            source_depth_in_km=event.origins[0].depth / 1000.0,
            distance_in_degree=distance_deg,
            phase_list=["P", "S"]
        )

        p_arrival, s_arrival = None, None
        for arrival in arrivals:
            if arrival.name == "P":
                p_arrival = event.origins[0].time + arrival.time
            elif arrival.name == "S":
                s_arrival = event.origins[0].time + arrival.time

        return p_arrival, s_arrival

    def process_catalogue(self):
        if not self.events:
            print("No events to process.")
            return []

        earthquakes = []
        event_counter = 1  # Start counter for the unique ID

        for event in self.events:
            p_arrival, s_arrival = self.predict_arrivals(event)

            event_id = str(event.resource_id)
            event_time = event.origins[0].time
            event_date = event_time.strftime("%Y-%m-%d")
            event_latitude = event.origins[0].latitude
            event_longitude = event.origins[0].longitude
            event_magnitude = event.magnitudes[0].mag
            event_mag_type = event.magnitudes[0].magnitude_type.lower()
            event_depth = event.origins[0].depth / 1000  # Convert depth to kilometers if needed

            # Generate a unique ID based on the date and a counter
            unique_id = f"{event_date}_{event_counter:02d}"
            event_counter += 1  # Increment the counter for the next event

            # Create an Earthquake object and append to the list
            earthquake = Earthquake(
                unique_id=unique_id,
                provider=self.provider,
                event_id=event_id,
                time=event_time.isoformat(),
                lat=event_latitude,
                long=event_longitude,
                mag=event_magnitude,
                mag_type=event_mag_type,
                depth=event_depth,
                epi_distance=None,
                p_predicted=p_arrival.isoformat() if p_arrival else None,
                s_predicted=s_arrival.isoformat() if s_arrival else None,
                catalogued=True,
                detected=False
            )

            earthquake.update_distance(self.lat, self.lon)
            earthquakes.append(earthquake)

        return earthquakes

    def __str__(self):
        if self.events and self.provider:
            return f"Catalog retrieved from {self.provider}. {len(self.events)} earthquakes found."
        else:
            return "No catalog data available."
