import base64
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests
from bs4 import BeautifulSoup
from obspy import UTCDateTime

import image_hosting_credentials as credentials

# today = datetime.now().strftime("%Y-%m-%d")


def upload_to_github(image_path, date):
    # Authorization with GitHub token
    headers = {'Authorization': f'token {credentials.GITHUB_TOKEN}'}

    # Append date-time to the filename to ensure uniqueness
    file_name = datetime.now().strftime("%Y%m%d%H%M%S_") + os.path.basename(image_path)
    if isinstance(date, UTCDateTime):
        date_str = date.strftime('%Y-%m-%d')
    elif isinstance(date, str):
        date_str = date
    else:
        raise ValueError("Date must be a UTCDateTime object or a string in 'YYYY-MM-DD' format")
    url = f'https://api.github.com/repos/{credentials.REPO_NAME}/contents/images/{date_str}/{file_name}'

    try:
        with open(image_path, 'rb') as image_file:
            content = base64.b64encode(image_file.read()).decode('utf-8')

        data = {
            'message': f'Upload new image {file_name}',
            'content': content
        }
        # Make a PUT request to upload the file on GitHub
        response = requests.put(url, json=data, headers=headers)
        if response.status_code in [200, 201]:  # 201 Created or 200 OK means success
            return response.json()['content']['download_url']
        else:
            print(f"Failed to upload {image_path}: {response.json().get('message')}")
    except FileNotFoundError:
        print(f"File not found: {image_path}")
    except Exception as e:
        print(f"Error uploading {image_path}: {str(e)}")


def update_html_image(html_content, content_path, date):
    # Parse HTML content to get image tags
    soup = BeautifulSoup(html_content, 'html.parser')
    images = soup.find_all('img')

    # Iterate over all image tags
    for img in images:
        src = img['src']
        # Check if the path is local and not an HTTP URL
        if not src.startswith('http'):
            # Construct the full image path
            full_image_path = os.path.join(content_path, src)
            # Upload the image to GitHub
            new_url = upload_to_github(full_image_path, date)
            # If the upload is successful, update the image src attribute in HTML
            if new_url:
                img['src'] = new_url

    # Convert the modified soup object back to string form of HTML
    return str(soup)

