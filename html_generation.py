import os
from datetime import datetime


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
            # Generate plot for the earthquake
            eq.generate_plot(stream, annotated_stream, path, simplified=simplified, p_only=p_only)

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


def compile_report_html(earthquakes, station, stream, annotated_stream, create_gif=True, simplified=False, p_only=False):
    date_str = station.report_date.strftime('%Y-%m-%d')
    output_html_file = os.path.join(station.report_folder, f"{date_str}_report.html")

    if create_gif:
        catalog_image_filename = os.path.join(station.report_folder, f"catalogued_plot_{date_str}.gif")
    else:
        catalog_image_filename = os.path.join(station.report_folder, f"catalogued_plot_{date_str}.png")

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
