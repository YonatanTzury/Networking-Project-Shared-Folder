import os
import sys
import json
import base64

from bottle import get, post, run, request

BASE_FOLDER = '.'

def create_path(func):
    def inner(path='.', **kwargs):
        if path[0] == '/':
            path = path[1:]

        path = os.path.join(BASE_FOLDER, path)
        return json.dumps(func(path, **kwargs))

    return inner

@get('/getattr/')
@get('/getattr/<path:path>')
@create_path
def getattr(path):
    if not os.path.exists(path):
        return

    res = os.stat(path)

    return {
        'st_mode': res.st_mode,
        'st_nlink': res.st_nlink,
        'st_size': res.st_size,
        'st_ctime': res.st_atime,
        'st_mtime': res.st_mtime,
        'st_atime': res.st_atime
    }

@get('/read/<size:int>/<offset:int>/<path:path>')
@create_path
def read(path, size, offset):
    if not os.path.exists(path):
        return
    
    with open(path, 'rb') as f:
        f.seek(offset)
        data = f.read(size)

    return base64.encodebytes(data).decode()

@get('/readdir/')
@get('/readdir/<path:path>')
@create_path
def readdir(path):
    return os.listdir(path)

@get('/create/<mode:int>/<path:path>')
@create_path
def create(path, mode):
    fd = os.open(
        path=path,
        flags=(
            os.O_WRONLY  # access mode: write only
            | os.O_CREAT  # create if not exists
            | os.O_TRUNC  # truncate the file to zero
        ),
        mode=mode
    )

    os.close(fd)

@post('/write/<offset:int>/<path:path>')
@create_path
def write(path, offset):
    with open(path, 'wb') as f:
        f.seek(offset)
        data = request.body.read()
        f.write(data)

    return len(data)

@get('/mkdir/<mode:int>/<path:path>')
@create_path
def mkdir(path, mode):
    os.mkdir(path, mode=mode)

@get('/unlink/<path:path>')
@create_path
def unlink(path):
    os.unlink(path)

@get('/rmdir/<path:path>')
@create_path
def rmdir(path):
    os.rmdir(path)

@get('/rename/<path:path>')
@create_path
def rename(path):
    new = request.query['new']
    if new[0] == '/':
        new = new[1:]
        
    os.rename(path, os.path.join(BASE_FOLDER, new))

def main():
    global BASE_FOLDER

    if len(sys.argv) >= 2:
        BASE_FOLDER = sys.argv[1]

    run(host='localhost', port=8080)

if __name__ == '__main__':
    main()