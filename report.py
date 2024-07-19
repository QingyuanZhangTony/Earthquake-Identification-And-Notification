import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from report_asset_generation import plot_catalogue, compile_report_html, update_html_image
import account_credentials as credentials

class Report:
    def __init__(self, station, catalog, simplified=False, p_only=False, fill_map=True, create_gif=True):
        self.station = station
        self.catalog = catalog
        self.simplified = simplified
        self.p_only = p_only
        self.fill_map = fill_map
        self.create_gif = create_gif
        self.report_html = None
        self.report_html_path = None

    def generate_earthquake_plots(self):
        matched_events = [eq for eq in self.catalog.all_day_earthquakes if eq.catalogued and eq.detected]
        for earthquake in matched_events:
            earthquake.generate_plot(self.station.stream.processed_stream, self.station.stream.annotated_stream,
                                     path=self.station.report_folder, simplified=self.simplified,
                                     p_only=self.p_only)

    def compile_report_html(self):
        self.report_html,self.report_html_path = compile_report_html(self.catalog.all_day_earthquakes, self.station,
                                               self.station.stream.processed_stream, self.station.stream.annotated_stream,
                                               create_gif=self.create_gif, simplified=self.simplified,
                                               p_only=self.p_only)

    def update_html_image(self):
        if self.report_html:
            self.report_html = update_html_image(self.report_html, self.station.report_folder, self.station.report_date)

    def construct_email(self):
        self.catalog.generate_catalogue_plot(self.station, self.fill_map, self.create_gif)
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

            # Connect to SMTP server
            smtp_obj = smtplib.SMTP(credentials.SMTP_SERVER, credentials.SMTP_PORT)
            print("Connecting to SMTP server.")

            # Log in to the SMTP server
            smtp_obj.login(credentials.EMAIL_ADDRESS, credentials.EMAIL_PASSWORD)
            print("Logged in to SMTP server.")

            # Set the sender and recipient information in the email message
            msg['From'] = credentials.EMAIL_ADDRESS
            msg['To'] = recipient

            # Send the email
            smtp_obj.sendmail(credentials.EMAIL_ADDRESS, recipient, msg.as_string())
            print("Email sent successfully.")

            # Disconnect from the SMTP server
            smtp_obj.quit()
            print("Disconnected from SMTP server.")
