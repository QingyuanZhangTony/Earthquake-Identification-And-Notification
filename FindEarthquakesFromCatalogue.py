import obspy
from obspy.clients.fdsn import Client
from obspy import UTCDateTime

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
