import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, AutoDateLocator
from obspy import UTCDateTime
from DataDownload import *
from obspy.geodetics import gps2dist_azimuth
from EventIdentification import *


def plot_spectrogram(trace):
    fig = plt.figure(figsize=(9, 3))
    trace.spectrogram(log=True, title='Spectrogram')
    plt.show()


def get_event_info(row):
    earthquake_info = {
        "time": row['time'],
        "lat": row['lat'],
        "long": row['long'],
        "mag": row['mag'],
        "mag_type": row['mag_type'],
        "P_peak_confidence": row.get('P_peak_confidence', None),
        "S_peak_confidence": row.get('S_peak_confidence', None),
        "epi_distance": row.get('epi_distance', None),
        "depth": row.get('depth', None),
    }
    return earthquake_info


def print_event_statistics(earthquake_info):
    print(f"Earthquake Time: {earthquake_info['time']}")
    print(f"Location: Lat {earthquake_info['lat']}, Long {earthquake_info['long']}")
    print(f"Magnitude: {earthquake_info['mag']} {earthquake_info['mag_type']}")
    print(f"Depth: {earthquake_info['depth']} m")
    print(f"Distance to Station: {earthquake_info['epi_distance']:.2f} km")

    if 'P_peak_confidence' in earthquake_info:
        print(f"P wave Confidence: {earthquake_info['P_peak_confidence']}")
    if 'S_peak_confidence' in earthquake_info:
        print(f"S wave Confidence: {earthquake_info['S_peak_confidence']}")
    print('-' * 40)


