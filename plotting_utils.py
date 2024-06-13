import os

import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image as PILImage
from matplotlib.legend_handler import HandlerLine2D


# Creates single PNG plots for earthquake events with markers
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
def plot_catalogue(earthquakes, station, fill_map=False, create_gif=True):
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

