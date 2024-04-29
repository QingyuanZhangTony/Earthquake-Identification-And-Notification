import matplotlib.pyplot as plt
import obspy
import obspy.geodetics.base
import obspy.geodetics.base
import pandas as pd
from obspy import UTCDateTime
from obspy.clients.fdsn import Client
from obspy.clients.fdsn.header import FDSNException
from obspy.taup import TauPyModel


def find_earthquakes(catalogue_provider, latitude, longitude, date, radmin, radmax, minmag, maxmag):
    # Load client for the FDSN web service
    try:
        client = Client(catalogue_provider)
    except Exception as e:
        print(f"Failed to connect to FDSN service at {catalogue_provider}: {e}")
        return None

    # Convert the base date from string to UTCDateTime and calculate start and end times
    base_date = UTCDateTime(date)
    starttime = base_date - 30 * 60  # 23:30 the day before (30 minutes to the previous day)
    endtime = base_date + (24 * 3600) + (30 * 60)  # 00:30 the day after (24 hours + 30 minutes)

    try:
        # Query the client for earthquakes based on the calculated time window and other parameters
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

        # Check if the catalog is empty
        if not catalog:
            print(f"No earthquakes found for the given parameters.")
            return None

        return catalog

    except FDSNException as e:
        print(f"Error fetching earthquake data: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


def print_catalogued(catalogued_earthquakes):
    if catalogued_earthquakes:
        print('Number of Identified Earthquakes:', len(catalogued_earthquakes))
        print(catalogued_earthquakes)
        catalogued_earthquakes.plot()
        plt.show()
        plt.close()  # Ensure that the matplotlib window closes after plotting.
    else:
        print('No earthquake data was returned or an error occurred.')


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
    )[0] / 1000.0 / 111.32  # Convert meters to degrees

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
            "P_predict": p_arrival.isoformat() if p_arrival else None,
            "S_predict": s_arrival.isoformat() if s_arrival else None,
            "catalogued": True,
            "detected": False,
            "detected_start": None,
            "detected_end": None
        }

        # Append the dictionary to the list
        earthquake_info_list.append(earthquake_data)

    # Convert the list of dictionaries to a DataFrame
    df = pd.DataFrame(earthquake_info_list)
    return df


