"""
Handles uploading file to Google Drive
Exampe:
    upload_to_google_drive("hello_world.txt")
"""

import os
import re
import sys
import json
import logging
import functools

from apiclient import discovery
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

SCOPES = [
    'https://www.googleapis.com/auth/drive.metadata.readonly',
    'https://www.googleapis.com/auth/drive.file']


def extract_components(file_path):
    '''
    Decouple file path into folder path and file name
    Args:
        file_path: the path to decouple
    Returns:
        a tuple of decoupled components (directory, filename)
    '''
    regex = re.compile(r'(.*)/(.*\..*)')
    matcher = regex.match(file_path)
    folder_name = matcher.group(1)
    file_name = matcher.group(2)
    return (folder_name, file_name)


def get_folder_id(DRIVE, folder_name):
    '''
    Obtain folder_id for folder_name, create the folder if necessary
    Args:
        folder_name: string of name of the folder
    '''
    files = DRIVE.files().list(
        q='name = "%s" and mimeType = "application/vnd.google-apps.folder" and trashed = false' % folder_name, fields='files(id)').execute()
    if len(files['files']) >= 1:
        return files['files'][0]['id']
    else:
        print('Creating folder %s' % (folder_name, ))
        folder = DRIVE.files().create(body={
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }, fields='id').execute()
        return folder['id']


def upload_to_google_drive(file_path, remove=False):
    """
        Upload file_path to Google Drive. Will automatically
        open browser for authentication if needed.

        Args:
            file_path (str): The path of the file to upload
    """
    folder_name, file_name = extract_components(file_path)
    print(folder_name, file_name)
    creds: Credentials = google_api_auth()
    DRIVE = discovery.build('drive', 'v3', credentials=creds)
    # save the file to specific folder
    folder_id = get_folder_id(DRIVE, folder_name)
    # buffer size 512K
    media = MediaFileUpload(file_path, chunksize=512*1024, resumable=True)
    # upload to the folder specified in file_path
    uploader = DRIVE.files().create(
        body={'name': file_name, 'parents': [folder_id]},
        media_body=media)
    response = None
    last_percent = 0
    while response is None:
        status, response = uploader.next_chunk()
        # Print the progress if the percentage changed
        if status:
            percent = int(status.progress() * 100)
            if percent > last_percent:
                print("%s uploaded %.2f%%" %
                      (file_path, (status.progress() * 100)))
                last_percent = percent
    print('%s uploaded!' % (file_path,))
    if remove:
        os.remove(file_path)
        print('%s removed!' % (file_path))
    return response


@functools.lru_cache()
def google_api_auth():
    '''
    obtain authorization to use Google Drive's API
    '''
    try:
        with open('storage.json', 'r') as fp:
            creds = json.load(fp)
            return Credentials.from_authorized_user_info(creds)
    except Exception as e:
        logging.warning("Failed to load stored credential due to %s", e)

    flow = InstalledAppFlow.from_client_secrets_file(
        'client_id.json', scopes=SCOPES)
    flow.run_console()
    creds = flow.credentials
    with open('storage.json', 'w') as fp:
        fp.write(creds.to_json())
    return creds


if __name__ == '__main__':
    google_api_auth()
    for video in sys.argv[1:]:
        upload_to_google_drive(video)
