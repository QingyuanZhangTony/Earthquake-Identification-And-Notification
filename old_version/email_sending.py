import base64
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests
from bs4 import BeautifulSoup

GITHUB_TOKEN = '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'
REPO_NAME = 'QingyuanZhangTony/ImageHosting'
today = datetime.now().strftime("%Y-%m-%d")
REPO_PATH = 'images/'


def parse_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    images = soup.find_all('img')
    return soup, images


def process_and_update_html(html_content, content_path, date):
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


def upload_to_github(image_path, date):
    # Authorization with GitHub token
    headers = {'Authorization': f'token {GITHUB_TOKEN}'}

    # Append date-time to the filename to ensure uniqueness
    file_name = datetime.now().strftime("%Y%m%d%H%M%S_") + os.path.basename(image_path)
    date_str = date.strftime("%Y-%m-%d")
    url = f'https://api.github.com/repos/{REPO_NAME}/contents/images/{date_str}/{file_name}'

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


def prepare_email(html_content, date):
    msg = MIMEMultipart('related')
    msg['Subject'] = f"Event Report For {date.strftime('%Y-%m-%d')}"
    msg.attach(MIMEText(html_content, 'html'))

    return msg


# Send the emails to the designated email
def send_email(email_message, recipient):
    print("Preparing to send an email...")

    # SMTP server settings
    smtp_server = "smtp.126.com"
    smtp_port = 25
    smtp_obj = smtplib.SMTP(smtp_server, smtp_port)
    print("SMTP server connected.")

    # User login information
    email_address = 'seismicreport@126.com'
    password = 'LKBYSOWAVLDGUOBN'  # mds.project.2024

    # Log in to the SMTP server
    smtp_obj.login(email_address, password)
    print("Logged in to the SMTP server.")

    # Set the sender and recipient information in the email message
    email_message['From'] = email_address
    email_message['To'] = recipient
    print("Sender and recipient set.")

    # Send the email
    smtp_obj.sendmail(email_address, recipient, email_message.as_string())
    print("Email sent.")

    # Disconnect from the SMTP server
    smtp_obj.quit()
    print("Disconnected from the SMTP server.")
