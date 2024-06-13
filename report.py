import os
from obspy import Stream
from datetime import datetime
from obspy.core import UTCDateTime
from IPython.display import Image, display
import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image as PILImage
from matplotlib.legend_handler import HandlerLine2D

from html_generation import *
from email_sending import *


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
def plot_catalogue(earthquakes, station, fill_map, create_gif):
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


class Report:
    def __init__(self, station, earthquakes, processed_stream, annotated_stream, simplified=False, p_only=False,
                 fill_map=True, create_gif=True):
        self.station = station
        self.earthquakes = earthquakes
        self.processed_stream = processed_stream
        self.annotated_stream = annotated_stream
        self.simplified = simplified
        self.p_only = p_only
        self.fill_map = fill_map
        self.create_gif = create_gif
        self.report_html = None

    def generate_catalogue_plot(self):
        return plot_catalogue(self.earthquakes, self.station, self.fill_map, self.create_gif)

    def generate_earthquake_plots(self):
        matched_events = [eq for eq in self.earthquakes if eq.catalogued and eq.detected]
        for earthquake in matched_events:
            if matched_events:
                # Generate the plot for each earthquake
                earthquake.generate_plot(self.processed_stream, self.annotated_stream, path=self.station.report_folder,
                                         simplified=self.simplified, p_only=self.p_only)

    def compile_report_html(self):
        self.report_html = compile_report_html(self.earthquakes, self.station, self.processed_stream,
                                               self.annotated_stream, create_gif=self.create_gif, simplified=self.simplified,
                                               p_only=self.p_only)

    def update_html_image(self):
        if self.report_html:
            self.report_html = update_html_image(self.report_html, self.station.report_folder, self.station.report_date)

    def construct_email(self):
        self.generate_catalogue_plot()
        self.generate_earthquake_plots()
        self.compile_report_html()
        self.update_html_image()

    def send_email(self, recipient):
        if self.report_html:
            # Create email message
            msg = MIMEMultipart('related')
            msg['Subject'] = f"Event Report For {self.station.report_date.strftime('%Y-%m-%d')}"
            msg.attach(MIMEText(self.report_html, 'html'))
            print("Email message compiled successfully.")

            # SMTP server settings
            smtp_server = "smtp.126.com"
            smtp_port = 25
            smtp_obj = smtplib.SMTP(smtp_server, smtp_port)
            print("Connecting to SMTP server...")

            # User login information
            email_address = 'seismicreport@126.com'
            password = 'LKBYSOWAVLDGUOBN'  # mds.project.2024

            # Log in to the SMTP server
            smtp_obj.login(email_address, password)
            print("Logged in to SMTP server.")

            # Set the sender and recipient information in the email message
            msg['From'] = email_address
            msg['To'] = recipient

            # Send the email
            smtp_obj.sendmail(email_address, recipient, msg.as_string())
            print("Email sent successfully.")

            # Disconnect from the SMTP server
            smtp_obj.quit()
            print("Disconnected from SMTP server.")
