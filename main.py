from __future__ import print_function
import argparse
import httplib2
import os
import io
import urllib.request
import json
import zlib
import types

import apiclient
from apiclient import discovery
from apiclient import errors

from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage


class TreeNode:
    def __init__(self, value=None, nodes=None, files=None):
        self.value = value
        self.folders = nodes
        self.files = files

    def value_id(self):
        return self.value.get('id', None)

class GoogleDocsConverter:
    # If modifying these scopes, delete your previously saved credentials
    # at ~/.credentials/drive-python-quickstart.json
    SCOPES = 'https://www.googleapis.com/auth/drive'
    #SCOPES = 'https://www.googleapis.com/auth/drive.metadata.readonly'
    CLIENT_SECRET_FILE = 'client_secret.json'
    APPLICATION_NAME = 'GoogleDocsSaver'

    # Mime types descriptions
    MIME_AUDIO = 'application/vnd.google-apps.audio'
    MIME_DOCS = 'application/vnd.google-apps.document'
    MIME_DRAW = 'application/vnd.google-apps.drawing'
    MIME_FILE = 'application/vnd.google-apps.file'
    MIME_FOLDER = 'application/vnd.google-apps.folder'
    MIME_FORMS = 'application/vnd.google-apps.form'
    MIME_TABLES = 'application/vnd.google-apps.fusiontable'
    MIME_MAPS = 'application/vnd.google-apps.map'
    MIME_PHOTO = 'application/vnd.google-apps.photo'
    MIME_SLIDES = 'application/vnd.google-apps.presentation'
    MIME_APP_SCRIPTS = 'application/vnd.google-apps.script'
    MIME_SITES = 'application/vnd.google-apps.site'
    MIME_SHEETS = 'application/vnd.google-apps.spreadsheet'
    MIME_UNKNOWN = 'application/vnd.google-apps.unknown'
    MIME_VIDEO = 'application/vnd.google-apps.video'
    MIME_SDK = 'application/vnd.google-apps.drive'

    def __init__(self, params):
        self.flags = params
        self.PrintMode = {'list': self.files_print_list, 'tree': self.files_print_tree}
        self.drive_service = self.create_google_drive_service()
        pass

    def get_credentials(self):
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

        store = Storage(credential_path)
        credentials = store.get()
        if not credentials or credentials.invalid:
            flow = client.flow_from_clientsecrets(GoogleDocsConverter.CLIENT_SECRET_FILE, GoogleDocsConverter.SCOPES)
            flow.user_agent = GoogleDocsConverter.APPLICATION_NAME
            if self.flags:
                credentials = tools.run_flow(flow, store, self.flags)
            else:  # Needed only for compatibility with Python 2.6
                credentials = tools.run(flow, store)
            print('Storing credentials to ' + credential_path)
        return credentials


    def create_google_drive_service(self):
        """
        Get credentials and login. Return service for work with API
        """
        credentials = self.get_credentials()
        http = credentials.authorize(httplib2.Http())
        return discovery.build('drive', 'v3', http=http)

    def find_folders_with_name(self, folder_name):
        results = self.drive_service.files().list(
            q='name="Мнимая свобода воли" and mimeType="application/vnd.google-apps.folder"',
            fields='nextPageToken, files(id, name)',
            space="drive").execute()
        return ""

    def download_doc_as_html(self, file):
        request = self.drive_service.files().export_media(fileId=file['id'], mimeType='text/html')
        fh = io.FileIO(file['name']+".html", 'wb')
        downloader = apiclient.http.MediaIoBaseDownload(fh, request)
        done = False
        try:
            while done is False:
                status, done = downloader.next_chunk()
                print("Download %d%%." % status.progress())
        except errors.HttpError:
            print('An error occurred: %s' % errors.HttpError)

    def test_download(self):
        folder_request = self.drive_service.files().list(
            q='name="Мнимая свобода воли" and mimeType="application/vnd.google-apps.folder"',
            fields='nextPageToken, files(id, name, createdTime, mimeType)').execute()

        folders = folder_request.get('files', [])
        if not folders:
            print('No files found.')
        else:
            for folder in folders:
                print('Folder:')
                print('{0}: {1} ({2}, {3})'.format(folder['mimeType'], folder['name'], folder['id'], folder['createdTime']))
                file_name = "ila"
                mimeType = "application/vnd.google-apps.document"
                folderID = folder['id']
                searchQ = 'name contains "{0}" and mimeType="{1}" and "{2}" in parents'.format(file_name, mimeType, folderID)
                fieldsStr = 'nextPageToken, files(id, name, createdTime, mimeType, parents)'
                files_request = self.drive_service.files().list(q=searchQ, fields=fieldsStr, orderBy='name_natural').execute()
                files = files_request.get('files', [])
                print('Files:')
                for file in files:
                    print(
                        '{0}: {1} ({2}, {3}) [{4}]'.format(file['mimeType'], file['name'], file['id'], file['createdTime'],
                                                           file['parents']))
                    # download_doc_as_html(service, file)

                print('\n')

    def get_metadata(self, file_id, fields="*"):
        """Check if fileId is valid drive id
          Args:
            drive_service: Drive API service instance.
            file_id: ID of the file to get metadata for.
            fields: Metadata fields. All by default.
          """
        if file_id is None:
            return None
        try:
            return self.drive_service.files().get(fileId=file_id, fields=fields).execute()
        except errors.HttpError as e:
            return None

    def folder_walk(self, full_trees, cache, node):
        current = node
        while current is not None:
            parents = current.value.get('parents', None)
            if parents is not None and len(parents) > 0:
                parent = parents[0]
                cached_node = cache.get(parent, None)
                if cached_node is None:
                    md = self.get_metadata(parent, fields="name, id, parents")
                    new_node = TreeNode(value=md, nodes=[current])
                    cache[new_node.value_id()] = new_node
                    current = new_node
                else:
                    if cached_node.folders is not None:
                        cached_node.folders.append(current)
                    else:
                        cached_node.folders = [current]
                    return
            else:
                full_trees.append(current)
                current = None

    def build_dict_tree(self, files_list):
        init_dict = {}
        for f in files_list:
            for p in f['parents']:
                if p in init_dict:
                    init_dict[p].append(f)
                else:
                    init_dict[p] = [f]
                pass
            pass
        start_nodes = []
        cache = {}
        for k in init_dict.keys():
            fm = self.get_metadata(k, fields="name, id, parents")
            if fm is not None:
                new_node = TreeNode(value=fm, files=init_dict[k])
                start_nodes.append(new_node)
                cache[new_node.value_id()] = new_node
            else:
                print("Error process object {0} ".format(k))

        full_trees = []
        for n in start_nodes:
            self.folder_walk(full_trees, cache, n)
        return full_trees

    def show_tree(self, node, level=0):
        if node.value is not None:
            print("{0}[{1}]".format("".join(['\t']*level), node.value.get('name', None)))
        if node.files is not None:
            for f in node.files:
                print('{0}{1}{2}'.format("".join(['\t'] * (level + 1)), f.get('name', None), ".doc"))
        if node.folders is not None:
            for n in node.folders:
                self.show_tree(n, level+1)

    def files_print_tree(self, files_list):
        trees = self.build_dict_tree(files_list)
        for tree in trees:
            if tree is not None:
                self.show_tree(tree)

    def files_print_list(self, files_list):
        index = 0
        parents_cache = {}
        zero_count = len(str(len(files_list)))
        for file_meta in files_list:
            index += 1
            result = ""
            if self.flags.files_count:
                result += str(index).zfill(zero_count)+") "
            result += '"{0}" [{1}] '.format(file_meta['name'], file_meta['id'])
            if self.flags.file_date:
                result += "("+file_meta['createdTime'] + ") "
            if self.flags.file_parent:
                result += 'Parents: '
                for p in file_meta.get('parents', []):
                    if parents_cache.get(p) is None:
                        parents_cache[p] = self.get_metadata(p, fields="name").get('name', "")
                    result += '"'+parents_cache.get(p, "")+'" '
                    if self.flags.file_parent_id:
                        result += '['+p+'] '
            print(result)
        if self.flags.files_count:
            print("Total count: "+str(index))
        pass

    def files_print(self, files_list):
        self.PrintMode[self.flags.mode](files_list)

    def search_files(self, file_name, parent_id=None, mime_type=MIME_DOCS, owners=None):
        search_query = 'mimeType="{0}"'.format(mime_type)
        if file_name is not None and file_name != "*":
            search_query += ' and name contains "{0}"'.format(file_name)
        if parent_id is not None:
            if isinstance(parent_id, str) and len(parent_id) > 0:
                search_query += ' and "{0}" in parents'.format(parent_id)
            elif isinstance(parent_id, list) and len(parent_id) > 0:
                if len(parent_id) == 1:
                    search_query += ' and "{0}" in parents'.format(parent_id[0])
                else:
                    search_query += ' and ('
                    for i in range(0, len(parent_id)):
                        search_query += '"{0}" in parents'.format(parent_id[i])
                        if i < len(parent_id)-1:
                            search_query += ' or '
                    search_query += ' )'
        if owners is not None:
            if isinstance(owners, str) and len(owners) > 0:
                search_query += ' and "{0}" in owners'.format(owners)
            elif isinstance(owners, list) and len(owners) > 0:
                if len(owners) == 1:
                    search_query += ' and "{0}" in owners'.format(owners[0])
                else:
                    search_query += ' and ('
                    for i in range(0, len(owners)):
                        search_query += '"{0}" in owners'.format(owners[i])
                        if i < len(owners)-1:
                            search_query += ' or '
                    search_query += ' )'
        else:
            search_query += ' and "me" in owners'
        print('search query: {0}'.format(search_query))
        fields = 'nextPageToken, files(id, name, createdTime, mimeType, parents, owners(me, permissionId, emailAddress))'
        result = []
        try:
            request_result = self.drive_service.files().\
                list(q=search_query, fields=fields, orderBy='name_natural').execute()
            result += request_result.get('files', [])
            next_page_token = request_result.get('nextPageToken', None)
            while next_page_token is not None:
                request_result = self.drive_service.files().\
                    list(pageToken=next_page_token, q=search_query, fields=fields, orderBy='name_natural').execute()
                result += request_result.get('files', [])
                next_page_token = request_result.get('nextPageToken', None)
        except errors.HttpError as e:
            print(e)

        return result

    def process_show(self):
        """Process show behaviour
          Args:
            drive_service: Drive API service instance.
            args: argparse result dict
        """
        # Get folder metadata
        folder_metadata = self.get_metadata(self.flags.folder)
        # Get file metadata
        file_metadata = self.get_metadata(self.flags.file)

        # If both exist, check is file into folder
        if folder_metadata is not None and file_metadata is not None:
            if folder_metadata["id"] in file_metadata["parents"]:
                self.files_print(self.drive_service, [file_metadata], self.flags)
            else:
                print('File "{0}" [{1}] not exist in folder "{2}" [{3}]'.
                      format(file_metadata["name"], file_metadata["id"], folder_metadata['name'], folder_metadata['id']))
                return

        parent_folders = []
        if folder_metadata is not None:
            parent_folders = folder_metadata['id']
        elif self.flags.folder is not None:
            parent_folders += self.search_files(self.flags.folder, mime_type=GoogleDocsConverter.MIME_FOLDER)
            parent_folders = [elem['id'] for elem in parent_folders]

        # If args not contains valid id
        result = self.search_files(self.flags.file, parent_id=parent_folders)
        self.files_print(result)

    def process_download(self):
        print('download')


    def process_command(self):
        if self.flags.command == 'show':
            self.process_show()
        elif self.flags.command == 'download':
            self.process_download()


def parse_args(debug_param=None):
    main_parser = argparse.ArgumentParser(prog='GoogleDocsConverter', parents=[tools.argparser], add_help=True)
    main_parser.add_argument("file", type=str, help='File search string.')
    main_parser.add_argument("folder", type=str, nargs='?', help='Root folder search string.')

    sub_parsers = main_parser.add_subparsers(dest='command', title='subcommands', description='valid subcommands',
                                             help='additional help')

    show_files_parser = sub_parsers.add_parser('show', help="Show files command")
    show_files_parser.add_argument("-mode", '-m', choices=['list', 'tree'],
                                   default='list', help="list for list view, tree for tree view")
    show_files_parser.add_argument("-file_date", '-fd', action='store_true')
    show_files_parser.add_argument("-file_parent", '-fp', action='store_true')
    show_files_parser.add_argument("-file_parent_id", '-fpi', action='store_true')
    show_files_parser.add_argument("-files_count", '-fc', action='store_true')
    show_files_parser.add_argument("-tree_first_level", '-fl', action='store_true')
    show_files_parser.add_argument("-tree_local", '-tl', action='store_true')

    download_parser = sub_parsers.add_parser('download', help="Download files")
    download_parser.add_argument("-save-structure", '-s', help="Save folder structure")
    if debug_param is not None:
        return main_parser.parse_args(debug_param.split(','))
    else:
        return main_parser.parse_args()


def main():
    #args = parse_args('ila,Мнимая свобода воли,show,-m,tree')
    #args = parse_args('ila,show,-m,tree')
    args = parse_args('ila,show,-m,tree')
    print(args)
    #dc = GoogleDocsConverter(args)
    #dc.process_command()


if __name__ == '__main__':
    main()

