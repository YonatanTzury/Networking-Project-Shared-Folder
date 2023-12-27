import os
import base64
import requests
import argparse

from errno import ENOENT
from fuse import FUSE, FuseOSError, Operations, LoggingMixIn


class RemoteFS(LoggingMixIn, Operations):
    def __init__(self, server_url):
        self.server_url = server_url
        self.fd = 0

    def get(self, path):
        if path[0] != '/':
            path = '/' + path

        res = requests.get(self.server_url + path)
        if res.status_code != 200:
            raise Exception(f'Bed status code: {res.status_code}: {path}')

        return res.json()

    def post(self, path, data):
        if path[0] != '/':
            path = '/' + path

        res = requests.post(self.server_url + path, data=data)
        if res.status_code != 200:
            raise Exception(f'Bed status code: {res.status_code}: {path}')

        return res.json()

    def create(self, path, mode):
        self.get(f'/create/{mode}/{path}')

        self.fd += 1
        return self.fd

    def release(self, path, fh):
        pass

    def getattr(self, path, fh=None):
        attr = self.get(f'/getattr/{path}')
        
        if attr is None:
            raise FuseOSError(ENOENT)

        return attr

    def mkdir(self, path, mode):
        self.get(f'/mkdir/{mode}/{path}')

    def open(self, path, flags):
        self.fd += 1
        return self.fd

    def read(self, path, size, offset, fh):
        return base64.decodebytes(self.get(f'/read/{size}/{offset}/{path}').encode())

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
        return self.post(f'/write/{offset}/{path}', data=data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--server-url', type=str,
                    help='remote server url', default='http://localhost:8080')
    parser.add_argument('mount_point', type=str,
                    help='local folder path')
   
    args = parser.parse_args()

    if not os.path.exists(args.mount_point):
        os.mkdir(args.mount_point)

    FUSE(RemoteFS(args.server_url), args.mount_point, foreground=True)

if __name__ == '__main__':
    main()
