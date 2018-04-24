from __future__ import print_function
import httplib2
import os
import io
import urllib.request
import json
import zlib

import apiclient
from apiclient import discovery
#from apiclient.http import MediaIoBaseDownload

from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

try:
    import argparse

    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/drive-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/drive'
#SCOPES = 'https://www.googleapis.com/auth/drive.metadata.readonly'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'GoogleDocsSaver'


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    # credential_dir = os.path.join(home_dir, '.credentials')
    credential_dir = '.credentials'
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir, 'drive-python-quickstart.json')

    if not os.path.isfile(CLIENT_SECRET_FILE):
        yandex_api_link = 'https://cloud-api.yandex.net/v1/disk/public/resources/download?public_key={0}&path=/'
        public_yandex_link = "https://yadi.sk/d/Ub2wse2h3UjiWz"
        print("Try ope: " + yandex_api_link.format(public_yandex_link))
        try:
            response = urllib.request.urlopen(yandex_api_link.format(public_yandex_link))
        except urllib.error.HTTPError as e:
            # Return code error (e.g. 404, 501, ...)
            print('HTTPError: {}'.format(e.code))
        except urllib.error.URLError as e:
            # Not an HTTP-specific error (e.g. connection refused)
            print('URLError: {}'.format(e.reason))
        else:
            print('link good')
            if response.info()['Content-Encoding'] == 'gzip':
                json_data = zlib.decompress(response, zlib.MAX_WBITS + 16)
            #url_data = response.read()
            json_result = json.load(response)['href']
            print(json_result)

            with urllib.request.urlopen(json_result) as response, open(CLIENT_SECRET_FILE, 'wb') as output_file:
                data = response.read()
                output_file.write(data)

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else:  # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials


def create_service():
    """
    Get credentials and login. Return service for work with API
    """
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    return discovery.build('drive', 'v3', http=http)


def find_folders_with_name(service, folder_name):
    results = service.files().list(
        q='name="Мнимая свобода воли" and mimeType="application/vnd.google-apps.folder"',
        fields='nextPageToken, files(id, name)',
        space="drive").execute()
    return ""

def download_doc_as_html(drive_service, file):
    request = drive_service.files().export_media(fileId=file['id'], mimeType='text/html')
    fh = io.FileIO(file['name']+".html", 'wb')
    downloader = apiclient.http.MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        print("Download %d%%." % status.progress())


def main():
    service = create_service()

    folder_request = service.files().list(
        q='name="Мнимая свобода воли" and mimeType="application/vnd.google-apps.folder"',
        fields='nextPageToken, files(id, name, createdTime, mimeType)').execute()

    folders = folder_request.get('files', [])
    if not folders:
        print('No files found.')
    else:
        for folder in folders:
            print('Folder:')
            print('{0}: {1} ({2}, {3})'.format(folder['mimeType'], folder['name'], folder['id'], folder['createdTime']))
            fileName = "ila"
            mimeType = "application/vnd.google-apps.document"
            folderID = folder['id']
            searchQ = 'name contains "{0}" and mimeType="{1}" and "{2}" in parents'.format(fileName, mimeType, folderID)
            fieldsStr = 'nextPageToken, files(id, name, createdTime, mimeType, parents)'
            files_request = service.files().list(q=searchQ, fields=fieldsStr, orderBy='name_natural').execute()
            files = files_request.get('files', [])
            print('Files:')
            for file in files:
                print('{0}: {1} ({2}, {3}) [{4}]'.format(file['mimeType'], file['name'], file['id'], file['createdTime'], file['parents']))
                #download_doc_as_html(service, file)

            print('\n')


if __name__ == '__main__':
    main()
