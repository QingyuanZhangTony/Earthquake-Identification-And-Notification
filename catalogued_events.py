import obspy
import obspy.geodetics.base
import obspy.geodetics.base
import pandas as pd
from obspy import read_events
from obspy.clients.fdsn.header import FDSNException
from obspy.geodetics import gps2dist_azimuth
from obspy.taup import TauPyModel

from station_data import *


# Request catalogue from provider and return path to the downloaded catalogue.
def request_catalogue(catalogue_providers, station_information, station_location, date, radmin, radmax, minmag, maxmag,
                      path,
                      overwrite=False):
    base_date = UTCDateTime(date)
    starttime = base_date - 30 * 60  # 23:30 the day before
    endtime = base_date + (24 * 3600) + (30 * 60)  # 00:30 the day after

    # Determine the directory path
    network, station, _ = station_information
    datestr = base_date.strftime("%Y-%m-%d")
    if not path:
        cur_dir = os.getcwd()
        path = os.path.join(cur_dir, "data", f"{network}.{station}", datestr)

    os.makedirs(path, exist_ok=True)

    for provider in catalogue_providers:
        filename = f"{datestr}_{provider}.catalogue.xml"
        filepath = os.path.join(path, filename)

        # Check file existence and overwrite parameter
        if os.path.isfile(filepath) and not overwrite:
            print(f"Catalogue for {datestr} already exists.")
            continue  # Continue trying next provider instead of returning

        # Attempt to fetch data from each provider
        try:
            client = Client(provider)
            catalog = client.get_events(
                latitude=station_location[0],
                longitude=station_location[1],
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
                return filepath, provider  # Return both filepath and provider
            else:
                print(f"No earthquakes found using the specified parameters from {provider}.")

        except FDSNNoDataException as e:
            print(f"No data available from {provider} for the requested parameters: {e}")
        except FDSNException as e:
            print(f"Error fetching earthquake data from {provider}: {e}")
        except Exception as e:
            print(f"Unexpected error occurred when connecting to {provider}: {e}")

    print("Failed to retrieve earthquake data from all provided catalog sources.")
    return None, None  # If no data is found or saved, return None for both


# Load and read downloaded catalogue from file path
def load_earthquake_catalog(filepath):
    # Check if the specified file exists
    if os.path.isfile(filepath):
        print("Reading catalogue from path.")
        print('-' * 40)
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


# Print catalogued and handles exceptions
def print_catalogued(catalogued):
    if catalogued:
        print(catalogued)
        print()
    else:
        print('No earthquake data was returned or an error occurred.')
        print()


# Predict P and S wave arrival times using TauPy
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


# Calculate epicentral distance from events to station
def calculate_distance(station_coordinates, epicenter_coordinates):
    distance_meters, azimuth, back_azimuth = gps2dist_azimuth(
        station_coordinates[0], station_coordinates[1],  # Station latitude and longitude
        epicenter_coordinates[0], epicenter_coordinates[1]  # Epicenter latitude and longitude
    )
    distance_kilometers = distance_meters / 1000.0
    return distance_kilometers


# Create a DataFrame of the catalogued events adding predicted times and various info from the cataloguee
def process_catalogue(catalog, station_coordinates, catalogue_provider):
    earthquake_info_list = []

    # Loop through each earthquake in the catalog
    for event in catalog:
        event_id = str(event.resource_id)
        event_time = event.origins[0].time
        event_latitude = event.origins[0].latitude
        event_longitude = event.origins[0].longitude
        event_magnitude = event.magnitudes[0].mag
        event_mag_type = event.magnitudes[0].magnitude_type.lower()
        event_depth = event.origins[0].depth
        epicentral_distance = calculate_distance(station_coordinates, [event_latitude, event_longitude])

        # Predict arrival times
        p_arrival, s_arrival = predict_arrival(event, station_coordinates)

        # Collect earthquake data in a dictionary
        earthquake_data = {
            "provider": catalogue_provider,
            "event_id": event_id,
            "time": event_time.isoformat(),
            "lat": event_latitude,
            "long": event_longitude,
            "mag": event_magnitude,
            "mag_type": event_mag_type,
            "depth": event_depth,
            "epi_distance": epicentral_distance,
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
