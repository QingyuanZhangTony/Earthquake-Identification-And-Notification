import obspy
import obspy.geodetics.base
import obspy.geodetics.base
import obspy.geodetics.base
import obspy.geodetics.base
import pandas as pd
from obspy import UTCDateTime
from obspy.clients.fdsn import Client
from obspy.taup import TauPyModel


def find_earthquakes(fromwhere, latitude, longitude, date, radmin, radmax, minmag, maxmag):
    # Load client for the FDSN web service
    client = Client(fromwhere)

    # Convert the base date from string to UTCDateTime and calculate start and end times
    base_date = UTCDateTime(date)
    starttime = base_date - 30 * 60  # 23:30 the day before (30 minutes to the previous day)
    endtime = base_date + (24 * 3600) + (30 * 60)  # 00:30 the day after (24 hours + 30 minutes)

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

    return catalog


def predict_arrivals(catalog, station_coordinates):
    # Load the TauP model for travel time predictions
    model = TauPyModel(model="iasp91")

    # Extract latitude and longitude from the coordinates tuple
    station_latitude, station_longitude = station_coordinates

    # Prepare a list to collect all earthquake data
    earthquake_info_list = []

    # Loop through each earthquake in the catalog
    for event in catalog:
        event_latitude = event.origins[0].latitude
        event_longitude = event.origins[0].longitude
        event_time = event.origins[0].time
        event_magnitude = event.magnitudes[0].mag
        event_mag_type = event.magnitudes[0].magnitude_type

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

        # Initialize P and S arrival times
        p_arrival, s_arrival = None, None

        # Extract P and S arrival times
        for arrival in arrivals:
            if arrival.name == "P":
                p_arrival = event_time + arrival.time
            elif arrival.name == "S":
                s_arrival = event_time + arrival.time

        # Collect earthquake data in a dictionary
        earthquake_data = {
            "time": event_time.isoformat(),
            "lat": event_latitude,
            "long": event_longitude,
            "mag": event_magnitude,
            "mag_type": event_mag_type,
            "P_arrival": p_arrival.isoformat() if p_arrival else None,
            "S_arrival": s_arrival.isoformat() if s_arrival else None,
            "catalogued": True,
            "detected": False  # Initial value set as False
        }

        # Append the dictionary to the list
        earthquake_info_list.append(earthquake_data)

    # Convert the list of dictionaries to a DataFrame
    df = pd.DataFrame(earthquake_info_list)
    return df

# Example usage:
# catalog = ...  # Your catalog data goes here
# station_coordinates = (latitude, longitude)  # Your station coordinates
# df = predict_arrivals(catalog, station_coordinates)
# print(df)
