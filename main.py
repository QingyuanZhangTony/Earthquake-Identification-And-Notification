# Dependencies
from DataDownload import *
from PreProcessing import *
from EventIdentification import *
from CataloguedEvents import *
from PostProcessing import *
import matplotlib.pyplot as plt
from obspy import UTCDateTime

# Set parameters for downloading
date = UTCDateTime("2024-02-07")
station = ['AM', 'R50D6', 'https://data.raspberryshake.org']
# Set global earthquake catalogue provider
catalogue = 'USGS'
# Get the coordination for the station
station_coordinates = get_coordinates(station)

# Try to download data and return availability for the date
data_available = download_seismic_data(date, station)
# Get and process stream from file
processed_stream = stream_process(get_stream(date, station))

# Detect earthquakes from downloaded data
df_detected = detect_earthquakes(
    processed_stream,
    sta_window=0.5,  # Short-time window in seconds
    lta_window=10.0,  # Long-time window in seconds
    threshold_on=3,  # STA/LTA threshold for triggering
    threshold_off=1  # STA/LTA threshold for turning off the trigger
)
print_detected(df_detected)

# Request catalogued earthquakes
catalogued_earthquakes = find_earthquakes(
    catalogue_provider=catalogue,
    coordinates=station_coordinates,
    date=date,
    radmin=0,
    radmax=90,
    minmag=5,
    maxmag=10
)
print_catalogued(catalogued_earthquakes)
# Create a DF with catalogued earthquakes
df_catalogued = create_df_with_prediction(catalogued_earthquakes, station_coordinates)

# Compare DataFrames And Merge Events Detected In Catalogue
result_df = match_and_merge(df_catalogued, df_detected)
print_statistics(result_df)
