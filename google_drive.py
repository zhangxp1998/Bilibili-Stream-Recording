"""
Handles uploading file to Google Drive
Exampe:
    upload_to_google_drive("hello_world.txt")
"""

import os
import re
import sys
from logging import debug, info

from apiclient import discovery
from googleapiclient.http import MediaFileUpload
from httplib2 import Http
from oauth2client import client, file, tools

SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly.metadata',
    'https://www.googleapis.com/auth/drive.file']

def extract_components(file_path):
    regex = re.compile(r'(.*)/(.*\..*)')
    matcher = regex.match(file_path)
    folder_name = matcher.group(1)
    file_name = matcher.group(2)
    return (folder_name, file_name)

def get_folder_id(DRIVE, folder_name):
    files = DRIVE.files().list(
        q='name = "%s" and mimeType = "application/vnd.google-apps.folder" and trashed = false' % folder_name, fields='files(id)').execute()
    if len(files['files']) >= 1:
        return files['files'][0]['id']
    else:
        debug('Creating folder %s', folder_name)
        folder = DRIVE.files().create(body={
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }, fields='files(id)').execute()
        return folder['id']

def upload_to_google_drive(file_path, remove=False):
    """
        Upload file_path to Google Drive. Will automatically
        open browser for authentication if needed.

        Args:
            file_path (str): The path of the file to upload
    """
    debug('File path: %s', file_path)
    folder_name, file_name = extract_components(file_path)
    print(folder_name, file_name)
    store = file.Storage('storage.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('client_id.json', SCOPES)
        creds = tools.run_flow(flow, store)
    DRIVE = discovery.build('drive', 'v3', http=creds.authorize(Http()))
    folder_id = get_folder_id(DRIVE, folder_name)
    debug(folder_id)
    media = MediaFileUpload(file_path, chunksize=512*1024, resumable=True)
    uploader = DRIVE.files().create(
        body={'name': file_name, 'parents': [folder_id]},
        media_body=media)
    response = None
    last_percent = 0
    while response is None:
        status, response = uploader.next_chunk()
        if status:
            percent = int(status.progress() * 100)
            if percent > last_percent:
                info("%s uploaded %.2f%%\n", file_path, (status.progress() * 100))
                last_percent = percent
    info('%s uploaded!', file_path)
    if remove:
        os.remove(file_path)
        info('%s removed!', file_path)


if __name__ == '__main__':
    for video in sys.argv[1:]:
        upload_to_google_drive(video)
