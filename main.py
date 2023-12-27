import sys
import base64
import requests

from errno import ENOENT
from fuse import FUSE, FuseOSError, Operations, LoggingMixIn

SERVER_URL = 'http://localhost:8080'

def get(path):
    if path[0] != '/':
        path = '/' + path

    res = requests.get(SERVER_URL + path)
    if res.status_code != 200:
        raise Exception(f'Bed status code: {res.status_code}: {SERVER_URL + path}')

    return res.json()

def post(path, data):
    if path[0] != '/':
        path = '/' + path

    res = requests.post(SERVER_URL + path, data=data)
    if res.status_code != 200:
        raise Exception(f'Bed status code: {res.status_code}: {SERVER_URL + path}')

    return res.json()

class RemoteFS(LoggingMixIn, Operations):
    def __init__(self):
        self.fd = 0

    def create(self, path, mode):
        get(f'/create/{mode}/{path}')

        self.fd += 1
        return self.fd

    def release(self, path, fh):
        print(f'release: {path}')

    def getattr(self, path, fh=None):
        attr = get(f'/getattr/{path}')
        
        if attr is None:
            raise FuseOSError(ENOENT)

        return attr

    def mkdir(self, path, mode):
        get(f'/mkdir/{mode}/{path}')

    def open(self, path, flags):
        print(f'open: {path} : {flags}')
        self.fd += 1
        return self.fd

    def read(self, path, size, offset, fh):
        return base64.decodebytes(get(f'/read/{size}/{offset}/{path}').encode())

    def readdir(self, path, fh):
        files = get(f'/readdir/{path}')
        return ['.', '..'] + files

    def rename(self, old, new):
        get(f'/rename/{old}?new={new}')

    def rmdir(self, path):
        get(f'/rmdir/{path}')

    def unlink(self, path):
        get(f'/unlink/{path}')

    def write(self, path, data, offset, fh):
        return post(f'/write/{offset}/{path}', data=data)


def main():
    if len(sys.argv) != 2:
        print(f'usage: {sys.argv[0]} <mountpoint>')
        return

    mount_point = sys.argv[1]
    FUSE(RemoteFS(), mount_point, foreground=True)

if __name__ == '__main__':
    main()
