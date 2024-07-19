import os
import time

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from obspy.clients.fdsn import Client
from obspy.clients.fdsn.header import FDSNNoDataException, FDSNException
from obspy.core import UTCDateTime

from earthquake import Earthquake
from report_asset_generation import plot_catalogue


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

        self.provider = None
        self.event_counter = 1

        self.original_catalog = None
        self.original_catalog_earthquakes = []
        self.all_day_earthquakes = []

        self.catalog_plot_path = None

    def __str__(self):
        if self.all_day_earthquakes and self.provider:
            return f"Catalog retrieved from {self.provider}. {len(self.all_day_earthquakes)} earthquakes found."
        else:
            return "No catalog data available."

    def request_catalogue2(self):
        starttime = self.station.report_date - 30 * 60  # 30 minutes before midnight on the day before
        endtime = self.station.report_date + (24 * 3600) + 30 * 60  # 30 minutes after midnight on the day after

        for i, provider in enumerate(self.catalogue_providers):
            try:
                client = Client(provider)
                catalog = client.get_events(
                    latitude=self.station.latitude,
                    longitude=self.station.longitude,
                    minradius=self.radmin,
                    maxradius=self.radmax,
                    starttime=starttime,
                    endtime=endtime,
                    minmagnitude=self.minmag,
                    maxmagnitude=self.maxmag
                )

                if catalog.events:
                    self.provider = provider
                    self.original_catalog_earthquakes = self.process_catalogue(catalog.events)
                    self.original_catalog = catalog
                    print(f"Catalog downloaded successfully from {provider}.")
                    return None

            except FDSNNoDataException as e:
                next_provider = self.catalogue_providers[i + 1] if i + 1 < len(
                    self.catalogue_providers) else 'no more providers'
                print(f"No data available from {provider}. Trying {next_provider}")
            except FDSNException as e:
                next_provider = self.catalogue_providers[i + 1] if i + 1 < len(
                    self.catalogue_providers) else 'no more providers'
                print(f"Error fetching earthquake data from {provider}. Trying {next_provider}")
            except Exception as e:
                next_provider = self.catalogue_providers[i + 1] if i + 1 < len(
                    self.catalogue_providers) else 'no more providers'
                print(f"Unexpected error occurred when connecting to {provider}. Trying {next_provider}")

        print("Failed to retrieve earthquake data from all provided catalog sources.")
        return None


    def request_catalogue(self):
        starttime = self.station.report_date - 30 * 60  # 30 minutes before midnight on the day before
        endtime = self.station.report_date + (24 * 3600) + 30 * 60  # 30 minutes after midnight on the day after

        attempts = 0
        while attempts < 2:  # 尝试两次，首次和重试一次
            for i, provider in enumerate(self.catalogue_providers):
                try:
                    client = Client(provider)
                    catalog = client.get_events(
                        latitude=self.station.latitude,
                        longitude=self.station.longitude,
                        minradius=self.radmin,
                        maxradius=self.radmax,
                        starttime=starttime,
                        endtime=endtime,
                        minmagnitude=self.minmag,
                        maxmagnitude=self.maxmag
                    )

                    if catalog.events:
                        self.provider = provider
                        self.original_catalog_earthquakes = self.process_catalogue(catalog.events)
                        self.original_catalog = catalog
                        print(f"Catalog downloaded successfully from {provider}.")
                        return None

                except FDSNNoDataException as e:
                    next_provider = self.catalogue_providers[i + 1] if i + 1 < len(
                        self.catalogue_providers) else 'no more providers'
                    print(f"No data available from {provider}. Trying {next_provider}")
                except FDSNException as e:
                    next_provider = self.catalogue_providers[i + 1] if i + 1 < len(
                        self.catalogue_providers) else 'no more providers'
                    print(f"Error fetching earthquake data from {provider}. Trying {next_provider}")
                except Exception as e:
                    next_provider = self.catalogue_providers[i + 1] if i + 1 < len(
                        self.catalogue_providers) else 'no more providers'
                    print(f"Unexpected error occurred when connecting to {provider}. Trying {next_provider}")

            if attempts == 0:
                print("Failed to retrieve earthquake data on first attempt. Retrying in 60 seconds...")
                time.sleep(60)  # 休眠 60 秒后重试
            attempts += 1

        print("Failed to retrieve earthquake data from all provided catalog sources after retry.")
        return None

    def request_recent_catalogue(self, query_duration):
        endtime = UTCDateTime()  # Now
        starttime = endtime - query_duration * 60  # query_duration minutes ago

        latest_earthquake = []  # Initialize the list

        print(f"Querying from {starttime} to {endtime}")

        for provider in self.catalogue_providers:
            try:
                client = Client(provider)
                latest_catalog = client.get_events(
                    latitude=self.station.latitude,
                    longitude=self.station.longitude,
                    minradius=self.radmin,
                    maxradius=self.radmax,
                    starttime=starttime,
                    endtime=endtime,
                    minmagnitude=self.minmag,
                    maxmagnitude=self.maxmag
                )

                if latest_catalog.events:
                    self.provider = provider
                    latest_earthquake = self.process_catalogue(latest_catalog.events)
                    print(
                        f"Catalog downloaded successfully from {self.provider}. Number of events: {len(latest_catalog.events)}.")
                    return latest_earthquake

            except FDSNNoDataException:
                continue  # Skip to the next provider
            except FDSNException as e:
                print(f"Error fetching earthquake data from {provider}. {str(e)}")
                continue  # Skip to the next provider
            except Exception as e:
                print(f"Unexpected error occurred when connecting to {provider}. {str(e)}")
                continue  # Skip to the next provider

        return latest_earthquake

    def generate_unique_id(self, event_date):
        # Generate a unique ID based on the date and a counter
        unique_id = f"{event_date}_{self.event_counter:02d}"
        self.event_counter += 1  # Increment the counter for the next event
        return unique_id

    def process_catalogue(self, events):
        if not events:
            print("No events to process.")
            return []

        earthquakes = []

        for event in events:
            # Extract event information
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

            # Create an Earthquake object
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
                catalogued=True,
                detected=False
            )

            # Update predicted arrivals
            earthquake.update_predicted_arrivals(self.station.latitude, self.station.longitude)

            # Update epicentral distance
            earthquake.update_distance(self.station.latitude, self.station.longitude)

            # Append the earthquake object to the list
            earthquakes.append(earthquake)

        return earthquakes

    def match_and_merge(self, detections, tolerance_p, tolerance_s, p_only=False):

        self.all_day_earthquakes = []

        event_counter = len(self.original_catalog_earthquakes) + 1  # Start counter for the new unique IDs

        for earthquake in self.original_catalog_earthquakes:
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

            # 将处理过的地震对象添加到 all_day_earthquakes
            self.all_day_earthquakes.append(earthquake)

        # Add unmatched detections as new earthquake objects
        for detection in detections:
            unique_id = f"{self.station.report_date.strftime('%Y-%m-%d')}_{event_counter:02d}"
            event_counter += 1

            new_earthquake = Earthquake(
                unique_id=unique_id,
                provider="Detection",
                event_id=None,
                time=detection['peak_time'].isoformat() if isinstance(detection['peak_time'], UTCDateTime) else
                detection['peak_time'],
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
                    'phase'] == 'S' and isinstance(detection['peak_time'], UTCDateTime) else None,
                p_confidence=detection['peak_confidence'] if detection['phase'] == 'P' else None,
                s_confidence=detection['peak_confidence'] if not p_only and detection['phase'] == 'S' else None,
                catalogued=False,
                detected=True
            )
            self.all_day_earthquakes.append(new_earthquake)

        return self.all_day_earthquakes

    def match_and_merge2(self, detections, tolerance_p, tolerance_s, p_only=False, detected_merging_threshold=3.0):

        self.all_day_earthquakes = []

        event_counter = len(self.original_catalog_earthquakes) + 1  # Start counter for the new unique IDs

        for earthquake in self.original_catalog_earthquakes:
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

            # 将处理过的地震对象添加到 all_day_earthquakes
            self.all_day_earthquakes.append(earthquake)

        # Merge unmatched detections before adding them as new earthquake objects
        merged_detections = []
        for detection in detections:
            merged = False
            for merged_detection in merged_detections:
                if (abs(UTCDateTime(detection['peak_time']) - UTCDateTime(merged_detection['peak_time'])) <= detected_merging_threshold and
                        detection['phase'] == merged_detection['phase']):
                    # Merge the detections
                    merged_detection['peak_time'] = min(UTCDateTime(detection['peak_time']),
                                                        UTCDateTime(merged_detection['peak_time'])).isoformat()
                    merged_detection['peak_confidence'] = max(detection['peak_confidence'],
                                                              merged_detection['peak_confidence'])
                    merged = True
                    break
            if not merged:
                merged_detections.append(detection)

        # Add the merged detections as new earthquake objects
        for detection in merged_detections:
            unique_id = f"{self.station.report_date.strftime('%Y-%m-%d')}_{event_counter:02d}"
            event_counter += 1

            new_earthquake = Earthquake(
                unique_id=unique_id,
                provider="Detection",
                event_id=None,
                time=detection['peak_time'].isoformat() if isinstance(detection['peak_time'], UTCDateTime) else
                detection['peak_time'],
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
                    'phase'] == 'S' and isinstance(detection['peak_time'], UTCDateTime) else None,
                p_confidence=detection['peak_confidence'] if detection['phase'] == 'P' else None,
                s_confidence=detection['peak_confidence'] if not p_only and detection['phase'] == 'S' else None,
                catalogued=False,
                detected=True
            )
            self.all_day_earthquakes.append(new_earthquake)

        return self.all_day_earthquakes

    def match_signals_with_earthquake(self, detections, earthquake, tolerance_p, tolerance_s, p_only):
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

        return best_p_detection is not None or (not p_only and best_s_detection is not None)

    def save_results(self):
        date_str = self.station.report_date.strftime('%Y-%m-%d')
        path = self.station.report_folder

        # 确保目标目录存在
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)

        # 构建每日报告的文件路径
        daily_filename = f"{date_str}.processed_events.csv"
        daily_full_path = os.path.join(path, daily_filename)

        # 定义CSV文件的表头
        headers = ["date", "unique_id", "provider", "event_id", "time", "lat", "long", "mag", "mag_type",
                   "depth", "epi_distance", "p_predicted", "s_predicted", "p_detected", "s_detected",
                   "p_confidence", "s_confidence", "p_error", "s_error", "catalogued", "detected"]

        # 创建新数据的DataFrame
        new_data = pd.DataFrame([{
            "date": date_str,  # 直接使用符合格式的 date_str
            "unique_id": eq.unique_id,
            "provider": eq.provider,
            "event_id": eq.event_id,
            "time": eq.time.isoformat(),
            "lat": eq.lat,
            "long": eq.long,
            "mag": eq.mag,
            "mag_type": eq.mag_type,
            "depth": eq.depth,
            "epi_distance": eq.epi_distance,
            "p_predicted": eq.p_predicted.isoformat() if eq.p_predicted else None,
            "s_predicted": eq.s_predicted.isoformat() if eq.s_predicted else None,
            "p_detected": eq.p_detected.isoformat() if eq.p_detected else None,
            "s_detected": eq.s_detected.isoformat() if eq.s_detected else None,
            "p_confidence": eq.p_confidence,
            "s_confidence": eq.s_confidence,
            "p_error": eq.p_error,
            "s_error": eq.s_error,
            "catalogued": eq.catalogued,
            "detected": eq.detected
        } for eq in self.all_day_earthquakes], columns=headers)

        # 写入每日数据
        new_data.to_csv(daily_full_path, index=False)

        # 总结文件的路径
        total_file_path = os.path.join(self.station.station_folder, "total_events_summary.csv")

        # 读取现有数据
        if os.path.exists(total_file_path):
            existing_data = pd.read_csv(total_file_path)
            # 删除相同日期的旧记录
            existing_data = existing_data[existing_data['date'] != new_data['date'].iloc[0]]
        else:
            existing_data = pd.DataFrame(columns=headers)

        # 将新数据添加到现有数据
        updated_data = pd.concat([existing_data, new_data], ignore_index=True)
        updated_data.to_csv(total_file_path, index=False)

        print(f"Daily list saved to {daily_full_path}")
        print(f"Total summary updated in {total_file_path}")

    def print_summary(self):
        total_catalogued = len([eq for eq in self.all_day_earthquakes if eq.catalogued])
        detected_catalogued = len([eq for eq in self.all_day_earthquakes if eq.catalogued and eq.detected])
        detected_not_catalogued_count = len(
            [eq for eq in self.all_day_earthquakes if eq.detected and not eq.catalogued])

        return detected_catalogued, detected_not_catalogued_count

    def generate_catalogue_plot(self, station, fill_map=True, create_gif=True):
        self.catalog_plot_path = plot_catalogue(station, self, fill_map, create_gif)

        return self.catalog_plot_path

    def plot_interactive_map2(self):
        if not self.original_catalog_earthquakes:
            print("No earthquake data available in the catalog.")
            return None

        earthquake_data = []
        for eq in self.original_catalog_earthquakes:
            if eq.catalogued:
                earthquake_data.append({
                    'latitude': eq.lat,
                    'longitude': eq.long,
                    'magnitude': eq.mag,
                    'depth': eq.depth,
                    'time': eq.time.strftime('%Y-%m-%d %H:%M:%S'),
                    'mag_type': eq.mag_type
                })
        df = pd.DataFrame(earthquake_data)

        norm = plt.Normalize(df['depth'].min(), df['depth'].max())
        cmap = plt.get_cmap('viridis')
        df['color'] = df['depth'].apply(lambda x: mcolors.to_hex(cmap(norm(x))))

        fig = px.scatter_mapbox(
            df,
            lat="latitude",
            lon="longitude",
            size="magnitude",
            color="depth",
            hover_data={
                "mag_type": True,
                "depth": True,
                "time": True,
                "latitude": False,
                "longitude": False
            },
            color_continuous_scale=px.colors.cyclical.IceFire,
            size_max=10,
            zoom=0
        )

        fig.update_layout(
            autosize=True,
            mapbox_style="carto-positron",
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            showlegend=True,
            mapbox_center={"lat": self.latitude, "lon": self.longitude},
            coloraxis_colorbar=dict(
                title="Depth(km)",
                titleside="bottom",
                ticks="outside",
                ticklen=4,
                tickwidth=1,
                tickcolor='#000',
                showticksuffix="last",
                dtick=5,
                lenmode="fraction",
                len=0.9,
                thicknessmode="pixels",
                thickness=15,
                yanchor="middle",
                y=0.5,
                xanchor="right",
                x=1.03
            )
        )
        return fig

    def plot_interactive_map(self):
        if not self.original_catalog_earthquakes:
            print("No earthquake data available in the catalog.")
            return None

        earthquake_data = []
        for eq in self.original_catalog_earthquakes:
            if eq.catalogued:
                earthquake_data.append({
                    'latitude': eq.lat,
                    'longitude': eq.long,
                    'magnitude': eq.mag,
                    'depth': eq.depth,
                    'time': eq.time.strftime('%Y-%m-%d %H:%M:%S'),
                    'mag_type': eq.mag_type,
                    'type': 'earthquake'
                })

        df_earthquakes = pd.DataFrame(earthquake_data)

        norm = plt.Normalize(df_earthquakes['depth'].min(), df_earthquakes['depth'].max())
        cmap = plt.get_cmap('viridis')
        df_earthquakes['color'] = df_earthquakes['depth'].apply(lambda x: mcolors.to_hex(cmap(norm(x))))

        fig = px.scatter_mapbox(
            df_earthquakes,
            lat="latitude",
            lon="longitude",
            size="magnitude",
            color="depth",
            hover_data={
                "mag_type": True,
                "depth": True,
                "time": True,
                "latitude": True,
                "longitude": True
            },
            color_continuous_scale=px.colors.sequential.Viridis[::-1],
            size_max=10,
            zoom=0
        )
        fig.update_traces(
            hovertemplate='<b>Time:</b> %{customdata[0]}<br>' +
                          '<b>Magnitude:</b> %{marker.size} %{customdata[1]}<br>' +
                          '<b>Location:</b> %{lat:.2f}, %{lon:.2f}<br>' +
                          '<b>Depth:</b> %{customdata[2]} km<extra></extra>',
            customdata=df_earthquakes[['time', 'mag_type', 'depth']]
        )

        # Add station marker
        if self.station:
            station_data = {
                'latitude': [self.station.latitude],
                'longitude': [self.station.longitude],
            }
            df_station = pd.DataFrame(station_data)

            station_trace = go.Scattermapbox(
                lat=df_station['latitude'],
                lon=df_station['longitude'],
                mode='markers',
                marker=go.scattermapbox.Marker(
                    size=15,
                    symbol='triangle'
                ),
                #text=[f"Station Code: {self.station.code}"],
                hovertemplate=f'<b>Station:</b> {self.station.code}<extra></extra>',
                name=''
            )
            fig.add_trace(station_trace)

        fig.update_layout(
            autosize=True,
            mapbox_style="light",
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            showlegend=False,
            mapbox_center={"lat": self.latitude, "lon": self.longitude},
            mapbox_accesstoken='pk.eyJ1IjoiZmFudGFzdGljbmFtZSIsImEiOiJjbHlnMnMzbmEwNmQ0MmpyN2lxNDNjaTd3In0.DfylrFmLO1EgfKf8sgIrkQ',
            # 在这里添加你的Mapbox令牌
            coloraxis_colorbar=dict(
                title="Depth(km)",
                titleside="bottom",
                ticks="outside",
                ticklen=4,
                tickwidth=1,
                tickcolor='#000',
                showticksuffix="last",
                dtick=5,
                lenmode="fraction",
                len=0.9,
                thicknessmode="pixels",
                thickness=15,
                yanchor="middle",
                y=0.5,
                xanchor="right",
                x=1.03
            )
        )

        return fig
