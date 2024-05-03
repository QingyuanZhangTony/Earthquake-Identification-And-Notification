import os

import matplotlib.pyplot as plt
import obspy
import obspy.geodetics.base
import obspy.geodetics.base
import pandas as pd
from obspy import read_events, UTCDateTime
from obspy.clients.fdsn import Client
from obspy.clients.fdsn.header import FDSNException
from obspy.taup import TauPyModel


def request_catalogue(catalogue_providers, coordinates, date, radmin, radmax, minmag, maxmag, overwrite=False):
    # Convert the date from string to UTCDateTime
    try:
        base_date = UTCDateTime(date)
    except Exception as e:
        print(f"Error parsing date '{date}': {e}")
        return None

    starttime = base_date - 30 * 60  # 23:30 the day before
    endtime = base_date + (24 * 3600) + (30 * 60)  # 00:30 the day after

    # Directory path
    cur_dir = os.getcwd()
    data_dir = os.path.join(cur_dir, "data", "catalogue")
    os.makedirs(data_dir, exist_ok=True)

    # File naming using latitude and longitude
    latitude, longitude = coordinates
    lat_lon_str = f"{latitude:.2f}_{longitude:.2f}".replace(".", "p")
    datestr = base_date.strftime("%Y-%m-%d")

    for provider in catalogue_providers:
        filename = f"{datestr}_{provider}.xml"
        filepath = os.path.join(data_dir, filename)

        # Check file existence and overwrite parameter
        if os.path.isfile(filepath) and not overwrite:
            print(f"Catalogue for {datestr} already exists.")
            return filepath

        # Attempt to fetch data from each provider
        try:
            client = Client(provider)
            catalog = client.get_events(
                latitude=latitude,
                longitude=longitude,
                minradius=radmin,
                maxradius=radmax,
                starttime=starttime,
                endtime=endtime,
                minmagnitude=minmag,
                maxmagnitude=maxmag
            )

            if catalog:
                # Save the catalog as a QuakeML file
                catalog.write(filepath, format="QUAKEML")
                print(f"Catalog saved to {filepath}")
                return filepath
            else:
                print(f"No earthquakes found using the specified parameters from {provider}.")

        except FDSNException as e:
            print(f"Error fetching earthquake data from {provider}: {e}")
        except Exception as e:
            print(f"Unexpected error occurred when connecting to {provider}: {e}")

    print("Failed to retrieve earthquake data from all provided catalog sources.")
    return None


def load_earthquake_catalog(filepath):
    # Check if the specified file exists
    if os.path.isfile(filepath):
        print(f"Loading catalogue from path.")
        try:
            # Read the QuakeML file
            catalog = read_events(filepath)
            return catalog
        except Exception as e:
            print(f"Failed to read the catalog file: {e}")
            return None
    else:
        print(f"No catalog file found at {filepath}")
        return None


def print_catalogued(catalogued_earthquakes):
    if catalogued_earthquakes:
        print(catalogued_earthquakes)
        print()
    else:
        print('No earthquake data was returned or an error occurred.')
        print()


def plot_catalogued(catalogued_earthquakes):
    if catalogued_earthquakes:
        catalogued_earthquakes.plot()
        plt.show()
        plt.close()  # Ensure that the matplotlib window closes after plotting.
    else:
        print('No earthquake data was returned or an error occurred.')
        print()


def predict_arrival(event, station_coordinates):
    model = TauPyModel(model="iasp91")
    station_latitude, station_longitude = station_coordinates

    event_latitude = event.origins[0].latitude
    event_longitude = event.origins[0].longitude
    event_time = event.origins[0].time

    # Calculate the distance and azimuth between the earthquake and the station
    distance_deg = obspy.geodetics.base.gps2dist_azimuth(
        event_latitude, event_longitude,
        station_latitude, station_longitude
    )[0] / 1000.0 / 111.195  # Convert meters to degrees

    # Get predicted arrival times
    arrivals = model.get_ray_paths(
        source_depth_in_km=event.origins[0].depth / 1000.0,
        distance_in_degree=distance_deg,
        phase_list=["P", "S"]
    )

    p_arrival, s_arrival = None, None
    for arrival in arrivals:
        if arrival.name == "P":
            p_arrival = event_time + arrival.time
        elif arrival.name == "S":
            s_arrival = event_time + arrival.time

    return p_arrival, s_arrival


def create_df_with_prediction(catalog, station_coordinates):
    earthquake_info_list = []

    # Loop through each earthquake in the catalog
    for event in catalog:
        event_latitude = event.origins[0].latitude
        event_longitude = event.origins[0].longitude
        event_time = event.origins[0].time
        event_magnitude = event.magnitudes[0].mag
        event_mag_type = event.magnitudes[0].magnitude_type

        # Predict arrival times
        p_arrival, s_arrival = predict_arrival(event, station_coordinates)

        # Collect earthquake data in a dictionary
        earthquake_data = {
            "time": event_time.isoformat(),
            "lat": event_latitude,
            "long": event_longitude,
            "mag": event_magnitude,
            "mag_type": event_mag_type,
            "P_predict": p_arrival.isoformat(),
            "S_predict": s_arrival.isoformat(),
            "catalogued": True,
            "detected": False,
            "P_detected": None,
            "S_detected": None
        }

        # Append the dictionary to the list
        earthquake_info_list.append(earthquake_data)

    # Convert the list of dictionaries to a DataFrame
    df = pd.DataFrame(earthquake_info_list)
    return df
