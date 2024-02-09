import os
import sys
import base64
import requests
import argparse
import logging

from errno import ENOENT, EBUSY
from fuse import FUSE, FuseOSError, Operations, LoggingMixIn


class RemoteFS(LoggingMixIn, Operations):
    def __init__(self, server_url):
        self.server_url = server_url
        self.session = requests.session()
        self.init_session()

    def __del__(self):
        logging.info('Closing session server')
        self.get('/close_session')

    def get(self, path):
        if path[0] != '/':
            path = '/' + path

        res = self.session.get(self.server_url + path)
        if res.status_code != 200:
            raise Exception(f'Bed status code: {res.status_code}: {path}')

        return res.json()

    def post(self, path, data):
        if path[0] != '/':
            path = '/' + path

        res = self.session.post(self.server_url + path, data=data)
        if res.status_code != 200:
            raise Exception(f'Bed status code: {res.status_code}: {path}')

        return res.json()
    
    def init_session(self):
        logging.info('Init session with server')
        try:
            res = self.session.get(self.server_url + '/init_session')
        except Exception as e:
            sys.tracebacklimit = 0
            raise Exception(f'Failed inialise session')

        if res.status_code != 200:
            raise Exception('Failes initialise session')

        session_id = self.session.cookies.get('session-id')
        logging.info(f'Got session ID: {session_id}')

    def create(self, path, mode):
        fd = self.get(f'/create/{mode}/{path}')
        return fd

    def truncate(self, path, length, fh=None):
        return

    def open(self, path, flags):
        fd = self.get(f'/open/{flags}/{path}')
        if fd < 0:
            raise FuseOSError(EBUSY)
        return fd

    def release(self, path, fh):
        self.get(f'/release/{fh}/{path}')

    def getattr(self, path, fh=None):
        attr = self.get(f'/getattr/{path}')
        
        if attr is None:
            raise FuseOSError(ENOENT)

        return attr

    def mkdir(self, path, mode):
        self.get(f'/mkdir/{mode}/{path}')

    def read(self, path, size, offset, fh):
        return base64.decodebytes(self.get(f'/read/{fh}/{size}/{offset}/{path}').encode())

    def readdir(self, path, fh):
        files = self.get(f'/readdir/{path}')
        return ['.', '..'] + files

    def rename(self, old, new):
        self.get(f'/rename/{old}?new={new}')

    def rmdir(self, path):
        self.get(f'/rmdir/{path}')

    def unlink(self, path):
        self.get(f'/unlink/{path}')

    def write(self, path, data, offset, fh):
        return self.post(f'/write/{fh}/{offset}/{path}', data=data)


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-s', '--server-url', type=str,
                    help='remote server url', default='http://localhost:8080')
    parser.add_argument('-v', '--verbose',
                    help='print verbose logging', action='store_true')
    parser.add_argument('mount_point', type=str,
                    help='local folder path')
   
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    logging.info('Checking if mount point exists')
    if not os.path.exists(args.mount_point):
        logging.info('Mount point does not exists - creating it')
        os.mkdir(args.mount_point)

    FUSE(RemoteFS(args.server_url), args.mount_point, foreground=True)

if __name__ == '__main__':
    main()
