import altair as alt
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from main import load_config, read_total_events_summary

# Load default settings
default_config = load_config()
# Initialize session state variables
for key, value in default_config.items():
    if key not in st.session_state:
        st.session_state[key] = value
# Simulate save settings on startup
if 'settings_initialized' not in st.session_state:
    st.session_state.settings_initialized = True
    for key, value in default_config.items():
        st.session_state[key] = value

# Read dataset csv
if 'df' not in st.session_state:
    st.session_state.df = read_total_events_summary(
        network=st.session_state.network,
        code=st.session_state.station_code,
        url=st.session_state.data_provider_url
    )

# Page title
st.title("Earthquake Monitoring And Report")
st.divider()

# System Status Placeholder
system_status_container = st.container()
with system_status_container:
    '''
    ## Intro
    This program is designed and implemented for my MDS dissertation project.\n
    It has two parts:\n
    1. Daily Catalog Monitoring And Earthquake Detection.\n
    2. Real-time Catalog Monitoring And Earthquake Detection.\n
    The second part is currently under construction and not included in this GUI.\n

    ## Version Notes
    Known Issues:\n
    1. When the codes finished execution after a button click, the page might return to top and you have to manually scroll down to where you were. \n
    
    '''
st.divider()

st.header(f"Deployment Statistics for {st.session_state.station_code}")

# Container for Total No. Detect Over Station Life Time
detection_lifetime = st.container()
with detection_lifetime:
    df = st.session_state.df

    if df is not None and not df.empty:
        df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date

        # Ensure data is sorted by date
        df = df.sort_values(by='date')

        # Total number of detected events over station life time (cumulative count)
        df['cumulative_detected'] = df['detected'].cumsum()

        # Ensure cumulative count is non-decreasing
        df['cumulative_detected'] = df['cumulative_detected'].cummax()

        cumulative_detected = df.groupby('date')['cumulative_detected'].last().reset_index()
        cumulative_detected_chart = alt.Chart(cumulative_detected).mark_line().encode(
            x=alt.X('date:T', title='Date'),
            y=alt.Y('cumulative_detected:Q', title='Cumulative No. Detect'),
            tooltip=['date:T', 'cumulative_detected:Q']
        ).properties(
            height=300,
            width=700,
            title='Cumulative No. Detect Over Station Life Time'
        )

        st.altair_chart(cumulative_detected_chart, use_container_width=True)
    else:
        st.error("Failed to load data or data is empty.")

# Container for % of Catalogued Events Detected
detection_percentage = st.container()
with detection_percentage.container():
    df = st.session_state.df

    if df is not None and not df.empty:
        # Percentage of catalogued events detected
        total_catalogued = df[df['catalogued']].groupby('date').size().reset_index(name='count')
        detected_catalogued = df[df['detected'] & df['catalogued']].groupby('date').size().reset_index(name='count')
        percentage_detected = pd.merge(total_catalogued, detected_catalogued, on='date', how='left',
                                       suffixes=('_catalogued', '_detected'))
        percentage_detected['percentage'] = (percentage_detected['count_detected'] / percentage_detected[
            'count_catalogued']) * 100
        percentage_detected_chart = alt.Chart(percentage_detected).mark_bar().encode(
            x=alt.X('date:T', title='Date'),
            y=alt.Y('percentage:Q', title='% of Catalogued Events Detected'),
            tooltip=['date:T', 'percentage:Q']
        ).properties(
            height=300,
            width=700,
            title='% of Catalogued Events Detected'
        )

        st.altair_chart(percentage_detected_chart, use_container_width=True)
    else:
        st.error("Failed to load data or data is empty.")

# Scatter Plot for Detected Earthquakes Only
scatterplot_container = st.container()
with scatterplot_container:
    df = st.session_state.df

    if df is not None and not df.empty:
        df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date

        # Ensure 'detected' and 'catalogued' are boolean
        df['detected'] = df['detected'].astype(bool)
        df['catalogued'] = df['catalogued'].astype(bool)

        # Ensure 'p_error' and 's_error' are string
        df['p_error'] = df['p_error'].astype(str)
        df['s_error'] = df['s_error'].astype(str)

        # Replace NaN values in 'p_error' and 's_error' with 'N/A'
        df.loc[:, 'p_error'] = df['p_error'].replace('nan', 'N/A')
        df.loc[:, 's_error'] = df['s_error'].replace('nan', 'N/A')

        # Replace NaN values in 's_confidence' with 'N/A'
        df.loc[:, 's_confidence'] = df['s_confidence'].fillna('N/A')

        # Filter for detected and catalogued events
        df_detected = df[(df['catalogued'] == True) & (df['detected'] == True)].copy()

        # Confidence slider
        confidence_threshold = st.slider(
            'Confidence Threshold',
            min_value=0.0,
            max_value=1.0,
            value=0.3,
            step=0.01,
            key='confidence_slider'
        )

        # Filter based on confidence threshold
        df_filtered = df_detected[df_detected['p_confidence'] >= confidence_threshold].copy()

        # Calculate the maximum magnitude and adjust the Y-axis domain
        max_magnitude = df_filtered['mag'].max()
        y_max = (max_magnitude // 1) + 1  # Round up to the nearest whole number

        base_chart = alt.Chart(df_filtered).mark_point(
            filled=True,
            opacity=1,
            size=50
        ).encode(
            x=alt.X('epi_distance:Q', title=f'Epicentral Distance To Station {st.session_state.station_code} (km)'),
            y=alt.Y('mag:Q', title='Magnitude', scale=alt.Scale(zero=False, domain=[0, y_max]),
                    axis=alt.Axis(tickCount=int(y_max + 1))),
            color=alt.Color('p_confidence:Q', scale=alt.Scale(scheme='blues'), legend=alt.Legend(
                title='Confidence  ', titleOrient='left', orient='right', titleLimit=0, gradientLength=300
            )),
            order=alt.Order(
                'detected',  # Ensures detected events are drawn on top of not detected ones
                sort='ascending'
            ),
            tooltip=[
                alt.Tooltip('time:T', title='Date and Time', format='%Y-%m-%d %H:%M:%S'),
                alt.Tooltip('mag:Q', title='Magnitude'),
                alt.Tooltip('mag_type:N', title='Magnitude Type'),
                alt.Tooltip('lat:Q', title='Latitude'),
                alt.Tooltip('long:Q', title='Longitude'),
                alt.Tooltip('unique_id:N', title='Unique ID'),
                alt.Tooltip('epi_distance:Q', title='Epicentral Distance (km)'),
                alt.Tooltip('depth:Q', title='Depth (km)'),
                alt.Tooltip('p_confidence:Q', title='P-Wave Confidence'),
                alt.Tooltip('p_error:N', title='P-Wave Error'),
                alt.Tooltip('s_confidence:N', title='S-Wave Confidence'),
                alt.Tooltip('s_error:N', title='S-Wave Error')
            ]
        ).properties(
            height=500,
            title='Catalogued Earthquake Detection Overview'
        )

        st.altair_chart(base_chart, use_container_width=True)
    else:
        st.error("Failed to load data or data is empty.")

# Interactive Map
interactive_map_container = st.container()
with interactive_map_container:
    st.subheader(f"Detected Catalogued Earthquakes Map Plot")

    df = st.session_state.df

    if df is not None and not df.empty:
        df['time'] = pd.to_datetime(df['time'], errors='coerce')
        df = df.dropna(subset=['time'])

        # Create a 'Location' column
        df['Location'] = df.apply(lambda row: f"{row['lat']:.2f}, {row['long']:.2f}", axis=1)

        # Combine magnitude and magnitude type into one column for tooltip
        df['Magnitude'] = df.apply(lambda row: f"{row['mag']} {row['mag_type']}", axis=1)

        # Ensure 'p_confidence' and 's_confidence' are numeric
        df['p_confidence'] = pd.to_numeric(df['p_confidence'], errors='coerce')
        df['s_confidence'] = pd.to_numeric(df['s_confidence'], errors='coerce')

        # Create a 'Prediction Confidence' column as the maximum of p_confidence and s_confidence
        df['Prediction Confidence'] = df.apply(
            lambda row: row['p_confidence'] if pd.isnull(row['s_confidence']) else max(row['p_confidence'],
                                                                                       row['s_confidence']),
            axis=1
        )

        # Format 'time' column for tooltip
        df['formatted_time'] = df['time'].dt.strftime('%Y-%m-%d %H:%M:%S')

        successfully_detected = df[(df['catalogued'] == True) & (df['detected'] == True)].copy()

        fig = px.scatter_mapbox(
            successfully_detected,
            lat="lat",
            lon="long",
            size="mag",
            color="mag",  # Change color to use magnitude
            hover_data={
                "Magnitude": True,
                "Location": True,
                "unique_id": True,
                "epi_distance": True,
                "depth": True,
                "Prediction Confidence": True
            },
            color_continuous_scale=px.colors.sequential.Sunset,  # Changed color scale
            size_max=7,
            zoom=0
        )
        fig.update_traces(
            hovertemplate='<b>Date and Time:</b> %{customdata[0]}<br>' +
                          '<b>Magnitude:</b> %{customdata[1]}<br>' +
                          '<b>Location:</b> %{customdata[2]}<br>' +
                          '<b>Unique ID:</b> %{customdata[3]}<br>' +
                          '<b>Epicentral Distance (km):</b> %{customdata[4]:.2f}<br>' +
                          '<b>Depth (km):</b> %{customdata[5]}<br>' +
                          '<b>Prediction Confidence:</b> %{customdata[6]:.2f}<extra></extra>',
            customdata=successfully_detected[
                ['formatted_time', 'Magnitude', 'Location', 'unique_id', 'epi_distance', 'depth',
                 'Prediction Confidence']]
        )

        # Optionally add a station marker
        if 'station' in st.session_state and st.session_state.station:
            station_data = {
                'latitude': [st.session_state.station['latitude']],
                'longitude': [st.session_state.station['longitude']],
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
                hovertemplate=f'<b>Station:</b> {st.session_state.station["code"]}<extra></extra>',
                name=''
            )
            fig.add_trace(station_trace)

        fig.update_layout(
            autosize=True,
            mapbox_style="light",
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            showlegend=False,
            mapbox_center={"lat": successfully_detected['lat'].mean(), "lon": successfully_detected['long'].mean()},
            mapbox_accesstoken='pk.eyJ1IjoiZmFudGFzdGljbmFtZSIsImEiOiJjbHlnMnMzbmEwNmQ0MmpyN2lxNDNjaTd3In0.DfylrFmLO1EgfKf8sgIrkQ',
            coloraxis_colorbar=dict(
                title="Magnitude",
                titleside="bottom",
                ticks="outside",
                ticklen=4,
                tickwidth=1,
                tickcolor='#000',
                showticksuffix="last",
                dtick=0.6,  # Adjust tick spacing for magnitude
                lenmode="fraction",
                len=0.9,
                thicknessmode="pixels",
                thickness=15,
                yanchor="middle",
                y=0.5,
                xanchor="right",
                x=1.04
            )
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("Failed to load data or data is empty.")
