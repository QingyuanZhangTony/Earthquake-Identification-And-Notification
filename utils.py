from obspy.clients.fdsn import Client
from obspy import UTCDateTime


def get_coordinates(station_info):
    try:
        if len(station_info) != 3:
            raise ValueError("station_info list must contain exactly three elements: network, station, and service_url.")

        network, station, service_url = station_info

        # Create an instance of the FDSN client
        client = Client(service_url)

        # Get current time for the endtime to ensure the station metadata is up-to-date
        endtime = UTCDateTime()

        # Fetch station metadata
        inventory = client.get_stations(network=network, station=station, endtime=endtime, level='station')

        # Extract latitude and longitude from the inventory
        station_info = inventory[0][0]  # Assumes only one station matches the query
        latitude = station_info.latitude
        longitude = station_info.longitude
        return (latitude, longitude)
    except Exception as e:
        print(f"Error fetching station coordinates: {e}")
        return None

