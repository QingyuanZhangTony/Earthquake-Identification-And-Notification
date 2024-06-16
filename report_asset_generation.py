import os
from datetime import datetime
import os
from obspy import Stream, read
from datetime import datetime
from obspy.core import UTCDateTime
from IPython.display import Image, display
import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image as PILImage
from matplotlib.legend_handler import HandlerLine2D


# from catalog import plot_catalogue
def create_png_plot(earthquakes, station, title, fill_map, show_detected, file_path, detected_count, undetected_count):
    latitude = station.latitude
    longitude = station.longitude
    network = station.network
    code = station.code

    fig, ax = plt.subplots(figsize=(10, 7), subplot_kw={'projection': ccrs.PlateCarree(central_longitude=longitude)})
    ax.set_global()
    ax.coastlines()

    if fill_map:
        ax.stock_img()
        cmap = plt.get_cmap('autumn')
        station_color = '#7F27FF'
        marker_color = '#FAA300'
    else:
        cmap = plt.get_cmap('viridis')
        station_color = '#F97300'
        marker_color = '#135D66'

    ax.plot(longitude, latitude, marker='^', color=station_color, markersize=16, linestyle='None',
            transform=ccrs.Geodetic(), label=f'Station {code}')

    norm = plt.Normalize(1, 10)

    for earthquake in earthquakes:
        if earthquake.detected == show_detected:
            color = cmap(norm(earthquake.mag))
            marker = 's' if show_detected else 'o'
            ax.plot(earthquake.long, earthquake.lat, marker=marker, color=color, markersize=10, markeredgecolor='white',
                    transform=ccrs.Geodetic())

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, orientation='vertical', pad=0.02, aspect=32.5, fraction=0.015, shrink=0.9)
    cbar.set_label('Magnitude')

    plt.title(title, fontsize=15)

    detected_marker = plt.Line2D([], [], color=marker_color, marker='s', markersize=10, linestyle='None',
                                 markeredgecolor='white')
    undetected_marker = plt.Line2D([], [], color=marker_color, marker='o', markersize=10, linestyle='None',
                                   markeredgecolor='white')
    station_marker = plt.Line2D([], [], color=station_color, marker='^', markersize=10, linestyle='None',
                                markeredgecolor='white')

    plt.legend([detected_marker, undetected_marker, station_marker],
               [f'Detected Earthquake: {detected_count}', f'Undetected Earthquake: {undetected_count}',
                f'Station {code}'],
               loc='lower center', handler_map={plt.Line2D: HandlerLine2D(numpoints=1)}, ncol=3)

    plt.tight_layout()
    plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)

    plt.savefig(file_path, bbox_inches='tight', pad_inches=0)
    plt.close()


# Produce a world map with all catalogued events and station
def plot_catalogue(station,catalog, fill_map, create_gif):
    earthquakes = catalog.processed_earthquakes
    latitude = station.latitude
    longitude = station.longitude
    title_date = station.report_date.strftime('%Y-%m-%d')
    title = f"Catalogue Events on {title_date}"
    save_path = station.report_folder

    if save_path:
        detected_png_path = os.path.join(save_path, f'detected_plot_{title_date}.png')
        undetected_png_path = os.path.join(save_path, f'undetected_plot_{title_date}.png')
        gif_path = os.path.join(save_path, f'catalogued_plot_{title_date}.gif')
        output_path = os.path.join(save_path, f'catalogued_plot_{title_date}.png')

    detected_events = [eq for eq in earthquakes if eq.catalogued and eq.detected]
    undetected_events = [eq for eq in earthquakes if eq.catalogued and not eq.detected]

    if create_gif and detected_events:
        create_png_plot(detected_events, station, title, fill_map, True, detected_png_path, len(detected_events),
                        len(undetected_events))
        create_png_plot(undetected_events, station, title, fill_map, False, undetected_png_path, len(detected_events),
                        len(undetected_events))

        images = [PILImage.open(detected_png_path), PILImage.open(undetected_png_path)]
        images[0].save(gif_path, save_all=True, append_images=[images[1]], duration=1500, loop=0)
        output_path = gif_path
    else:
        fig, ax = plt.subplots(figsize=(10, 7),
                               subplot_kw={'projection': ccrs.PlateCarree(central_longitude=longitude)})
        ax.set_global()
        ax.coastlines()
        if fill_map:
            ax.stock_img()
            cmap = plt.get_cmap('autumn')
        else:
            cmap = plt.get_cmap('viridis')

        ax.plot(longitude, latitude, marker='^', color='#FF7F00', markersize=16, linestyle='None',
                transform=ccrs.Geodetic(), label=f'Station {station.code}')
        norm = plt.Normalize(1, 10)
        for eq in earthquakes:
            if eq.mag is not None:
                color = cmap(norm(eq.mag))
                marker = 's' if eq.detected else 'o'
                ax.plot(eq.long, eq.lat, marker=marker, color=color, markersize=10, markeredgecolor='white',
                        transform=ccrs.Geodetic())

        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, orientation='vertical', pad=0.02, aspect=32.5, fraction=0.015, shrink=0.9)
        cbar.set_label('Magnitude')
        plt.title(title, fontsize=15)
        plt.savefig(output_path, bbox_inches='tight', pad_inches=0)
        plt.close()

    return output_path


def html_header(date_str):
    return f"""
    <html>
    <head>
        <title>Earthquake Report for {date_str}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            img {{ width: 100%; max-width: 800px; height: auto; }}
            .catalogue-list, .event-details {{ margin-top: 20px; }}
        </style>
    </head>
    <body>
        <h1>Earthquake Report for {date_str}</h1>
    """


def html_basic_info(network, station_code, provider):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""
    <p><strong>Station:</strong> {network}.{station_code} &nbsp;&nbsp;&nbsp;
    <strong>Catalogue Provider:</strong> {provider} &nbsp;&nbsp;&nbsp;
    <strong>Issued At:</strong> {current_time}</p>
    """


def html_catalogue_map(catalog_image_path):
    return f"""
    <div class="catalogue-plot">
        <img src="{catalog_image_path}" alt="Catalogue Overview Map">
    </div>
    """


def html_catalogue_list(earthquakes, simplified=False):
    rows = []
    for eq in earthquakes:
        if eq.catalogued and (not simplified or eq.detected):
            color = "#557C55" if eq.detected else "#707070"
            rows.append(
                f"<tr style='color: {color};'><td>{eq.time.strftime('%Y-%m-%d %H:%M:%S')}</td><td>{eq.lat}, {eq.long}</td><td>{eq.mag} {eq.mag_type}</td></tr>")
    if not rows:
        return "<p><strong>No earthquake from the catalogue was detected.</strong></p>"

    return f"""
    <div class="catalogue-list">
        <table>
            <thead>
                <tr>
                    <th>Time</th>
                    <th>Location</th>
                    <th>Magnitude</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
    </div>
    """


def html_overall_stats(earthquakes, simplified=False, p_only=False):
    # Calculate statistics
    total_detected = len([eq for eq in earthquakes if eq.detected])
    total_catalogued = len([eq for eq in earthquakes if eq.catalogued])
    catalogued_detected = len([eq for eq in earthquakes if eq.catalogued and eq.detected])
    not_in_catalogue = total_detected - catalogued_detected

    event_detected_rate = (catalogued_detected / total_catalogued * 100) if total_catalogued > 0 else 0
    p_detected = len([eq for eq in earthquakes if eq.catalogued and eq.p_detected])
    s_detected = len([eq for eq in earthquakes if eq.catalogued and eq.s_detected])
    p_detected_rate = (p_detected / total_catalogued * 100) if total_catalogued > 0 else 0
    s_detected_rate = (s_detected / total_catalogued * 100) if total_catalogued > 0 else 0

    stats = f"""
    <div class="event-stats">
        <p><strong>Total Events Detected:</strong> {total_detected}</p>
        <p><strong>Catalogued Events Detected:</strong> {catalogued_detected} out of {total_catalogued}</p>
        <p><strong>Event Detected Rate:</strong> {event_detected_rate:.2f}%</p>
    """

    if not simplified:
        stats += f"""
        <p><strong>P Wave Detected Rate:</strong> {p_detected_rate:.2f}%</p>
        """
        if not p_only:
            stats += f"""
            <p><strong>S Wave Detected Rate:</strong> {s_detected_rate:.2f}%</p>
            """
        stats += f"""
        <p><strong>Detected But Not Catalogued:</strong> {not_in_catalogue}</p>
        </div>
        """
    else:
        stats += "</div>"

    return stats


def html_event_detail(earthquakes, stream, annotated_stream, path, simplified=False, p_only=False):
    if not any(eq.detected and eq.catalogued for eq in earthquakes):
        return "<p><strong>No detected catalogued earthquakes.</strong></p>"

    parts = ['<p class="section_title"><strong>Details For Detected Catalogued Events:</strong></p>']
    for eq in earthquakes:
        if eq.catalogued and eq.detected:

            # Append details to the HTML content
            parts.append(f"""
            <div class="event-details">
                <img src="{eq.plot_path}" alt="Detailed plot for earthquake {eq.unique_id}">
                <table class="statistics" border="1">
                    <tr><td>Event ID:</td><td>{eq.unique_id}</td></tr>
                    <tr><td>Provider:</td><td>{eq.provider}</td></tr>""")

            if not simplified:
                parts.append(f"<tr><td>Provider Event ID:</td><td>{eq.event_id}</td></tr>")

            parts.append(f"""
                    <tr><td>Time:</td><td>{eq.time.strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
                    <tr><td>Latitude, Longitude:</td><td>{eq.lat}, {eq.long}</td></tr>
                    <tr><td>Depth:</td><td>{eq.depth} km</td></tr>
                    <tr><td>Magnitude:</td><td>{eq.mag} {eq.mag_type}</td></tr>
                    <tr><td>Epicentral Distance:</td><td>{eq.epi_distance} km</td></tr>
                    <tr><td>P Predicted Time:</td><td>{eq.p_predicted or 'N/A'}</td></tr>
                    <tr><td>P Detected Time:</td><td>{eq.p_detected or 'N/A'}</td></tr>
                    <tr><td>P Time Error:</td><td>{getattr(eq, 'p_error', 'N/A')}</td></tr>
                    <tr><td>P Confidence:</td><td>{getattr(eq, 'p_confidence', 'N/A')}</td></tr>""")

            if not p_only:
                parts.append(f"""
                    <tr><td>S Predicted Time:</td><td>{getattr(eq, 's_predicted', 'N/A')}</td></tr>
                    <tr><td>S Detected Time:</td><td>{getattr(eq, 's_detected', 'N/A')}</td></tr>
                    <tr><td>S Time Error:</td><td>{getattr(eq, 's_error', 'N/A')}</td></tr>
                    <tr><td>S Confidence:</td><td>{getattr(eq, 's_confidence', 'N/A')}</td></tr>""")

            parts.append("</table></div><br><br>")

    return "".join(parts)


def compile_report_html(earthquakes, station, stream, annotated_stream, create_gif=True, simplified=False,
                        p_only=False):
    date_str = station.report_date.strftime('%Y-%m-%d')
    output_html_file = os.path.join(station.report_folder, f"{date_str}_report.html")

    catalog_image_filename = None
    for file in os.listdir(station.report_folder):
        if file.startswith(f"catalogued_plot_{date_str}"):
            catalog_image_filename = os.path.join(station.report_folder, file)
            break

    catalogue_provider = "Unknown"
    for eq in earthquakes:
        if eq.catalogued:
            catalogue_provider = eq.provider
            break

    # Build HTML content
    header = html_header(date_str)
    basic_info = html_basic_info(station.network, station.code, catalogue_provider)
    catalogue_map = html_catalogue_map(catalog_image_filename)
    catalogue_list = html_catalogue_list(earthquakes, simplified)
    event_stats = html_overall_stats(earthquakes, simplified, p_only)
    event_details = html_event_detail(earthquakes, stream, annotated_stream, station.date_folder, simplified, p_only)

    # Assemble all parts into the final HTML content
    html_content = f"{header}{basic_info}<hr>{catalogue_map}{catalogue_list}<hr>{event_stats}<hr>{event_details}</body></html>"

    # Save the compiled HTML report
    with open(output_html_file, 'w') as file:
        file.write(html_content)
    print(f"HTML report generated: {output_html_file}")

    return html_content
