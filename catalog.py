import csv

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
    def __init__(self, station, radmin, radmax, minmag, maxmag, catalogue_providers):

        self.radmin = radmin
        self.radmax = radmax
        self.minmag = minmag
        self.maxmag = maxmag
        self.catalogue_providers = catalogue_providers

        self.station = station
        self.latitude = station.latitude
        self.longitude = station.longitude
        self.date = station.report_date

        self.events = None
        self.provider = None
        self.event_counter = 1
        self.earthquakes = []
        self.processed_earthquakes = []

    def request_catalogue(self):
        starttime = self.date - 30 * 60  # 30 minutes before midnight on the day before
        endtime = self.date + (24 * 3600) + 30 * 60  # 30 minutes after midnight on the day after

        for provider in self.catalogue_providers:
            try:
                client = Client(provider)
                catalog = client.get_events(
                    latitude=self.latitude,
                    longitude=self.longitude,
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
            self.latitude, self.longitude
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

    def generate_unique_id(self, event_date):
        # Generate a unique ID based on the date and a counter
        unique_id = f"{event_date}_{self.event_counter:02d}"
        self.event_counter += 1  # Increment the counter for the next event
        return unique_id

    def process_catalogue(self):
        if not self.events:
            print("No events to process.")
            return []

        self.earthquakes = []

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

            # Generate a unique ID using the new function
            unique_id = self.generate_unique_id(event_date)

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

            earthquake.update_distance(self.latitude, self.longitude)
            self.earthquakes.append(earthquake)

    def match_and_merge(self, detections, tolerance_p, tolerance_s, p_only=False):
        event_counter = len(self.earthquakes) + 1  # Start counter for the new unique IDs

        for earthquake in self.earthquakes:
            highest_p_confidence = 0
            highest_s_confidence = 0
            best_p_detection = None
            best_s_detection = None

            for detection in detections:
                detected_time = UTCDateTime(detection['peak_time'])
                detected_phase = detection['phase']
                detected_confidence = detection['peak_confidence']

                if detected_phase == 'P' and earthquake.p_predicted and abs(
                        detected_time - UTCDateTime(earthquake.p_predicted)) <= tolerance_p:
                    if detected_confidence > highest_p_confidence:
                        highest_p_confidence = detected_confidence
                        best_p_detection = detection['peak_time']

                if not p_only and detected_phase == 'S' and earthquake.s_predicted and abs(
                        detected_time - UTCDateTime(earthquake.s_predicted)) <= tolerance_s:
                    if detected_confidence > highest_s_confidence:
                        highest_s_confidence = detected_confidence
                        best_s_detection = detection['peak_time']

            # Update earthquake with the best detected times and confidences
            if best_p_detection:
                earthquake.p_detected = best_p_detection
                earthquake.p_confidence = highest_p_confidence
                earthquake.detected = True

            if not p_only and best_s_detection:
                earthquake.s_detected = best_s_detection
                earthquake.s_confidence = highest_s_confidence
                earthquake.detected = True

            # Filter out the matched detections to avoid re-matching
            detections = [d for d in detections if
                          not (d['peak_time'] == best_p_detection or (
                                  not p_only and d['peak_time'] == best_s_detection))]

        # Add unmatched detections as new earthquake objects
        for detection in detections:
            unique_id = f"{self.station.report_date.strftime('%Y-%m-%d')}_{event_counter:02d}"
            event_counter += 1

            new_earthquake = Earthquake(
                unique_id=unique_id,
                provider="Detection",
                event_id=None,
                time=detection['peak_time'].isoformat() if isinstance(detection['peak_time'], UTCDateTime) else
                detection[
                    'peak_time'],
                lat=None,
                long=None,
                mag=None,
                mag_type=None,
                depth=None,
                epi_distance=None,
                p_predicted=None,
                s_predicted=None,
                p_detected=detection['peak_time'].isoformat() if detection['phase'] == 'P' and isinstance(
                    detection['peak_time'], UTCDateTime) else None,
                s_detected=detection['peak_time'].isoformat() if not p_only and detection[
                    'phase'] == 'S' and isinstance(
                    detection['peak_time'], UTCDateTime) else None,
                p_confidence=detection['peak_confidence'] if detection['phase'] == 'P' else None,
                s_confidence=detection['peak_confidence'] if not p_only and detection['phase'] == 'S' else None,
                catalogued=False,
                detected=True
            )
            self.earthquakes.append(new_earthquake)

        return self.earthquakes

    def save_results(self):
        date_str = self.station.report_date.strftime('%Y-%m-%d')
        path = self.station.report_folder

        # Ensure the target directory exists
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)

        # Construct file path
        filename = f"{date_str}.processed_events.csv"
        full_path = os.path.join(path, filename)

        # Open file and write data
        with open(full_path, 'w', newline='') as file:
            writer = csv.writer(file)

            headers = ["unique_id", "provider", "event_id", "time", "lat", "long", "mag", "mag_type",
                       "depth", "epi_distance", "p_predicted", "s_predicted", "p_detected", "s_detected",
                       "p_confidence", "s_confidence", "p_error", "s_error", "catalogued", "detected"]
            writer.writerow(headers)

            for earthquake in self.processed_earthquakes:
                row = [
                    earthquake.unique_id, earthquake.provider, earthquake.event_id, earthquake.time.isoformat(),
                    earthquake.lat,
                    earthquake.long, earthquake.mag, earthquake.mag_type, earthquake.depth, earthquake.epi_distance,
                    earthquake.p_predicted.isoformat() if earthquake.p_predicted else None,
                    earthquake.s_predicted.isoformat() if earthquake.s_predicted else None,
                    earthquake.p_detected.isoformat() if earthquake.p_detected else None,
                    earthquake.s_detected.isoformat() if earthquake.s_detected else None,
                    earthquake.p_confidence, earthquake.s_confidence, earthquake.p_error, earthquake.s_error,
                    earthquake.catalogued, earthquake.detected
                ]
                writer.writerow(row)

        print(f"List saved to {full_path}")

    def print_summary(self):
        catalogued_count = len([eq for eq in self.processed_earthquakes if eq.catalogued])
        detected_count = len([eq for eq in self.processed_earthquakes if eq.detected])
        detected_not_catalogued_count = len([eq for eq in self.processed_earthquakes if eq.detected and not eq.catalogued])

        summary = (
            f"Total catalogued earthquakes: {catalogued_count}\n"
            f"Total detected earthquakes: {detected_count}\n"
            f"Detected earthquakes not in catalog: {detected_not_catalogued_count}"
        )

        return summary

    def __str__(self):
        if self.events and self.provider:
            return f"Catalog retrieved from {self.provider}. {len(self.events)} earthquakes found."
        else:
            return "No catalog data available."
