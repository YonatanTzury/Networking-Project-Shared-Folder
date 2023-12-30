import os
import json
import base64
import argparse

import uuid
from bottle import get, post, run, request, response
from dataclasses import dataclass

BASE_FOLDER = '.'
SESSION_COOKIE_NAME = 'session-id'

@dataclass
class FD():
    path: str
    is_write: bool = False
@dataclass
class Handle():
    def __init__(self):
        self.readers = dict() # Mapping[str, Sequence[int]] -- session_id -> fds
        self.writer = None
class FileAccessManagment(object):
    """
    The FileAccessManagment (FAM) class respsosible for control the access to files on the server from diffrenct clients.
    The main functionality of the FAM is to prevent multiple edits to the same file (both from the same client or diffrent ones)

    The FAM use 2 internals datastructure:
    1. sessions - dict with the sessions as the key,
        each session value is a list of Handles storing the path to the file and if the handle use for write or only read
        the index of the handle in the session list is the fd returned to the client
    2. handles - dict ith the path as key
        each path store another dict with the session ids as key
        and a list of indexes of handles point to this path of the specific session

    Known Issues:
    1. should add lock since the server is async
    """

    def __init__(self):
        self.sessions = dict() # Mapping[str, Sequence[FD]] -- session_id -> list of Handle(Path, is_write)
        self.handles = dict() # Mapping[str, Handle] -- path -> Handle(writer=session_id, readers=(SessionId, fd))

    def init_session(self):
        new_session_uuid = str(uuid.uuid1())

        for i in range(100):
            if new_session_uuid not in self.sessions:
                break

            new_session_uuid = str(uuid.uuid1())
        
        if i == 99:
            raise(Exception('Could not found new session id'))

        self.sessions[new_session_uuid] = []

        return new_session_uuid
    
    def close_session(self, session_id):
        if not self.is_valid_session(session_id):
            return

        for fd in self.sessions[session_id]:
            if fd is None:
                continue

            if fd.is_write:
                self.handles[fd.path].writer = None
                continue
            
            del self.handles[fd.path].readers[session_id]
        
        del self.sessions[session_id]

    def is_valid_session(self, session_id):
        return self.sessions.get(session_id) is not None

    def open_for_write(self, session_id, path):
        cur_handle =  self.handles.get(path, Handle())
        
        if cur_handle.writer is not None:
            return -1

        cur_handle.writer = session_id
        self.handles[path] = cur_handle

        self.sessions[session_id].append(FD(path, True))
        cur_fd = len(self.sessions[session_id]) - 1

        return cur_fd

    def open_for_read(self, session_id, path):
        self.sessions[session_id].append(FD(path))
        cur_fd = len(self.sessions[session_id]) - 1

        cur_handle =  self.handles.get(path, Handle())
        cur_path_session_readers = cur_handle.readers.get(session_id, set())
        
        cur_path_session_readers.add(cur_fd)

        cur_handle.readers[session_id] = cur_path_session_readers
        self.handles[path] = cur_handle

        return cur_fd

    def is_valid_handle(self, session_id, fd, path, is_write=False):
        if not self.is_valid_session(session_id):
            raise Exception('Not valid session')

        if fd < 0 or fd >= len(self.sessions[session_id]):
            raise Exception('Not valid handle')
        
        if self.sessions[session_id][fd] is None:
            raise Exception('Already closed handle')

        if self.sessions[session_id][fd].path != path:
            raise Exception('Handle does not match path')
        
        if is_write and not self.sessions[session_id][fd].is_write:
            return False

        return True

    def is_any_handle(self, path):
        handle = self.handles.get(path)
        if handle is None:
            return False
        
        if handle.writer is not None:
            return True
    
        if len(handle.readers) > 0:
            return True
    
        return False

    def close(self, session_id, fd, path):
        if not self.is_valid_handle(session_id, fd, path):
            raise Exception('Not valid handle')
        
        if self.sessions[session_id][fd].is_write:
            self.handles[path].writer = None
        else:
            self.handles[path].readers[session_id].remove(fd)
        
        self.sessions[session_id][fd] = None

fam = FileAccessManagment()

def request_wrapper(func):
    def inner(path='.', **kwargs):
        global fam

        session_id = request.get_cookie(SESSION_COOKIE_NAME)
        if session_id is None:
            response.status = 403
            return

        if not fam.is_valid_session(session_id):
            response.status = 403
            return

        if path[0] == '/':
            path = path[1:]

        path = os.path.join(BASE_FOLDER, path)

        return json.dumps(func(session_id, path, **kwargs))

    return inner    

@get('/init_session')
def init_session():
    global fam

    new_session_uuid = fam.init_session()

    response.set_cookie(SESSION_COOKIE_NAME, new_session_uuid, path='/')

@get('/close_session')
def init_session():
    global fam

    session_id = request.get_cookie(SESSION_COOKIE_NAME)
    if session_id is None:
        return

    fam.close_session(session_id)

@get('/create/<mode:int>/<path:path>')
@request_wrapper
def create(session_id, path, mode):
    global fam

    v_fd = fam.open_for_write(session_id, path)

    if v_fd < 0:
        return v_fd

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

    return v_fd

@get('/open/<flags:int>/<path:path>')
@request_wrapper
def open_file(session_id, path, flags):
    global fam

    if flags & (os.O_WRONLY | os.O_APPEND | os.O_RDWR):
        return fam.open_for_write(session_id, path)

    return fam.open_for_read(session_id, path)

@get('/release/<fd:int>/<path:path>')
@request_wrapper
def release(session_id, path, fd):
    global fam

    fam.close(session_id, fd, path)

@get('/read/<fd:int>/<size:int>/<offset:int>/<path:path>')
@request_wrapper
def read(session_id, path, fd, size, offset):
    global fam

    if not fam.is_valid_handle(session_id, fd, path):
        response.status = 403
        return

    if not os.path.exists(path):
        response.status = 400
        return
    
    with open(path, 'rb') as f:
        f.seek(offset)
        data = f.read(size)

    return base64.encodebytes(data).decode()

@post('/write/<fd:int>/<offset:int>/<path:path>')
@request_wrapper
def write(session_id, path, fd, offset):
    if not fam.is_valid_handle(session_id, fd, path, True):
        response.status = 403
        return

    with open(path, 'wb') as f:
        f.seek(offset)
        data = request.body.read()
        f.write(data)

    return len(data)

@get('/getattr/')
@get('/getattr/<path:path>')
@request_wrapper
def getattr(_, path):
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

@get('/readdir/')
@get('/readdir/<path:path>')
@request_wrapper
def readdir(_, path):
    return os.listdir(path)

@get('/mkdir/<mode:int>/<path:path>')
@request_wrapper
def mkdir(_, path, mode):
    # Known issue - should handle edge cases better
    os.mkdir(path, mode=mode)

@get('/unlink/<path:path>')
@request_wrapper
def unlink(_, path):
    global fam

    if fam.is_any_handle(path):
        return -1

    os.unlink(path)
    return 0

@get('/rmdir/<path:path>')
@request_wrapper
def rmdir(path):
    # Known issue - should handle edge cases better
    os.rmdir(path)

@get('/rename/<path:path>')
@request_wrapper
def rename(path):
    global fam

    new = request.query['new']
    if new[0] == '/':
        new = new[1:]

    if fam.is_any_handle(path) or fam.is_any_handle(new):
        return -1
        
    os.rename(path, os.path.join(BASE_FOLDER, new))
    return 0

def main():
    global BASE_FOLDER

    parser = argparse.ArgumentParser()
    parser.add_argument('-b', '--bind-address', type=str,
                    help='listening address', default='localhost')
    parser.add_argument('-p', '--port', type=int,
                    help='listentting port', default=8080)
    parser.add_argument('mount_point', type=str,
                    help='local folder path')
   
    args = parser.parse_args()

    BASE_FOLDER = args.mount_point

    if not os.path.exists(BASE_FOLDER):
        os.mkdir(BASE_FOLDER)

    run(host=args.bind_address, port=args.port)

if __name__ == '__main__':
    main()
