from email_sending import update_html_image, send_email
from report_asset_generation import *


class Report:
    def __init__(self, station, catalog, simplified=False, p_only=False, fill_map=True, create_gif=True):
        self.station = station
        self.catalog = catalog
        self.simplified = simplified
        self.p_only = p_only
        self.fill_map = fill_map
        self.create_gif = create_gif
        self.report_html = None

    def generate_catalogue_plot(self):
        return plot_catalogue(self.station, self.catalog, self.fill_map, self.create_gif)

    def generate_earthquake_plots(self):
        matched_events = [eq for eq in self.catalog.processed_earthquakes if eq.catalogued and eq.detected]
        for earthquake in matched_events:
            earthquake.generate_plot(self.station.processed_stream, self.station.annotated_stream,
                                     path=self.station.report_folder, simplified=self.simplified,
                                     p_only=self.p_only)

    def compile_report_html(self):
        self.report_html = compile_report_html(self.catalog.processed_earthquakes, self.station,
                                               self.station.processed_stream, self.station.annotated_stream,
                                               create_gif=self.create_gif, simplified=self.simplified,
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
            send_email(self.report_html, self.station.report_date, recipient)
