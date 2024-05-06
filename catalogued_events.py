import cartopy.crs as ccrs
import matplotlib.pyplot as plt
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

    # File naming using latitude and longitude
    latitude, longitude = station_location
    lat_lon_str = f"{latitude:.2f}_{longitude:.2f}".replace(".", "p")

    for provider in catalogue_providers:
        filename = f"{datestr}_{provider}.catalogue.xml"
        filepath = os.path.join(path, filename)

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

        except FDSNNoDataException as e:
            print(f"No data available from {provider} for the requested parameters: {e}")
        except FDSNException as e:
            print(f"Error fetching earthquake data from {provider}: {e}")
        except Exception as e:
            print(f"Unexpected error occurred when connecting to {provider}: {e}")

    print("Failed to retrieve earthquake data from all provided catalog sources.")
    return None


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


# Produce a world map with all catalogued events and station marked for displaying or saving to file.
def plot_catalogue(earthquake_catalogue, station_information, catalogue_date, fill_map=False, path=None, show=False,
                   save=False):
    network, station, data_provider = station_information  # Extract station details
    latitude, longitude = get_coordinates(station_information)  # Assuming function exists to get coordinates

    fig, ax = plt.subplots(figsize=(10, 7), subplot_kw={
        'projection': ccrs.PlateCarree(central_longitude=longitude)
    })
    ax.set_global()
    ax.coastlines()

    # Optional map filling
    if fill_map:
        ax.stock_img()  # Adding a simple stock image
        text_color = 'white'  # Text color when map is filled
        station_color = '#7F27FF'  # Station color when map is filled
    else:
        text_color = 'black'  # Text color without fill
        station_color = '#7F27FF'  # Station color without fill

    # Plotting the station location with a special marker
    ax.plot(longitude, latitude, marker='^', color=station_color, markersize=12, linestyle='None',
            transform=ccrs.Geodetic(), label=f'Station {station}')

    # Setup colormap and normalization
    cmap = plt.get_cmap('viridis')
    norm = plt.Normalize(1, 10)  # Fixed range from 1 to 10 for magnitude

    for event in earthquake_catalogue:
        if event.origins and event.magnitudes and event.origins[0] and event.origins[0].time:
            origin = event.origins[0]
            magnitude = event.magnitudes[0].mag
            color = cmap(norm(magnitude))  # Get color from magnitude
            ax.plot(origin.longitude, origin.latitude, marker='o', color=color, markersize=10,
                    transform=ccrs.Geodetic())

    # Prepare colorbar and set its position and size
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, orientation='vertical', pad=0.02, aspect=50, fraction=0.01, shrink=0.7)
    cbar.set_label('Magnitude')

    title_date = catalogue_date.strftime('%Y-%m-%d')
    title = f"Catalogued Events for {network}.{station} on {title_date}"
    plt.title(title)

    # Adding legend to show station marker
    ax.legend(loc='upper right')

    if save and path:
        file_path = os.path.join(path, f'catalogued_plot_{title_date}.png')
        plt.tight_layout()
        plt.savefig(file_path, bbox_inches='tight', pad_inches=0)
        print(f"Saved plot to {file_path}")
        plt.close()

    if show:
        plt.tight_layout()

        plt.show()


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
def process_catalogue(catalog, station_coordinates):
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
