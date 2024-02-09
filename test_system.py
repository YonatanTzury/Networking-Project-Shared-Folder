import os
import time
import pytest
import shutil
import subprocess

AMOUNT_OF_CLIENTS = 2
TEST_FOLDER = '.test'
TEST_LOGS = '.test_logs'

CLIENTS = [os.path.join(TEST_FOLDER, f'client_{i}') for i in range(AMOUNT_OF_CLIENTS)]

def is_lock(path):
    failed = False
    try:
        with open(path, 'w') as f:
            pass
    except OSError:
        failed = True

    return failed

# TODO FIX PATHS
def setup_test():
    # Test client and server root folder
    if os.path.exists(TEST_FOLDER):
        shutil.rmtree(TEST_FOLDER)

    os.mkdir(TEST_FOLDER)
    
    # Test logs folder
    if os.path.exists(TEST_LOGS):
        for f in os.listdir(TEST_LOGS):
            os.remove(os.path.join(TEST_LOGS,f))
    else:
        os.mkdir(TEST_LOGS)

    print('[+] Ruuning server')
    log = open(os.path.join(TEST_LOGS, 'server.log'), 'w')
    procs = [subprocess.Popen(['python3', '/tmp/Networking-Project-Shared-Folder/server.py', os.path.join(TEST_FOLDER, 'server')], stdout=log, stderr=log)]

    for client_path in CLIENTS:
        print(f'[+] Ruuning client \'{client_path}\'')
        log = open(os.path.join(TEST_LOGS, f'{client_path[-1]}.log'), 'w')
        procs.append(subprocess.Popen(['python3', '/tmp/Networking-Project-Shared-Folder/client.py', '-v', client_path], stdout=log, stderr=log))

    time.sleep(3)

    return procs

def finish_test(procs):
    for proc in procs[::-1]:
        print(f'[+] Stopping process: {proc.args[-1]}')
        proc.terminate()
        time.sleep(1)

    print('[+] Deleting test folder')
    shutil.rmtree(TEST_FOLDER)

@pytest.fixture(scope="session", autouse=True)
def resource():
    if AMOUNT_OF_CLIENTS < 2:
        raise Exception('AMOUNT_OF_CLIENTS should be 2 or more')

    procs = setup_test()
    yield "resource"
    finish_test(procs)

def test_empty_folder():
    for client in CLIENTS:
        assert os.listdir(client) == []

def test_text_file():
    file_name = 'test.txt'
    text = 'TEST'
    
    client_0 = CLIENTS[0]
    
    with open(os.path.join(client_0, file_name), 'w') as f:
        f.write(text)

    for client in CLIENTS[1:]:
        with open(os.path.join(client, file_name), 'r') as f:
            assert text == f.read()

def test_binary_file():
    file_name = 'test.bin'
    binary = b'0xde0xad0xbe0xef'
    
    client_0 = CLIENTS[0]
    
    with open(os.path.join(client_0, file_name), 'wb') as f:
        f.write(binary)

    for client in CLIENTS[1:]:
        with open(os.path.join(client, file_name), 'rb') as f:
            assert binary == f.read()

def test_not_empty_folder():
   for client in CLIENTS:
       assert set(os.listdir(client)) == {'test.txt', 'test.bin'}

def test_create_folder():
    folder_name = 'folder'

    os.mkdir(os.path.join(CLIENTS[0], folder_name))

    for client in CLIENTS:
        assert os.path.isdir(os.path.join(client, folder_name))

def test_lock():
    lock_name = 'lock'

    f = open(os.path.join(CLIENTS[0], lock_name), 'w')

    for client in CLIENTS[1:]:
        assert is_lock(os.path.join(client, lock_name))

def test_delete_all():
    for f in os.listdir(CLIENTS[0]):
        cur = os.path.join(CLIENTS[0], f)
        if os.path.isdir(cur):
            shutil.rmtree(cur)
        else:
            os.remove(cur)

    for client in CLIENTS[1:]:
        assert os.listdir(client) == []


"""


def check_folders(files):
    for client in iterate_clients:
        cur_files = os.listdir(client)
        if cur_files != files:
            raise Exception('Wrong dir list')



def main():
    pass

os.system('rm -rf server client_*')

p1 = subprocess.Popen(['python3', 'server.py', 'server'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
p2 = subprocess.Popen(['python3', 'main.py', 'client_1'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
p3 = subprocess.Popen(['python3', 'main.py', 'client_2'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

time.sleep(1)

try:
    with open('client_1/first', 'w') as f:
        f.write('TEST')

    time.sleep(1)
    with open('client_2/first', 'r') as f:
        if 'TEST' != f.read():
            raise Exception('Wrong text')

    time.sleep(1)
    check_folders(['first'])

    os.remove('client_1/first')

    time.sleep(1)
    check_folders([])

    f1 = open('client_1/lock', 'w')
    f1.write('lock 1')

    time.sleep(1)
    if not is_lock('client_1/lock'):
        raise Exception('should be locked')

    time.sleep(1)
    if not is_lock('client_2/lock'):
        raise Exception('should be locked')

    f1.close()

    time.sleep(1)
    if is_lock('client_1/lock'):
        raise Exception('should not be locked')

    time.sleep(1)
    if is_lock('client_2/lock'):
        raise Exception('should not be locked')


finally:
    p1.terminate()
    p2.terminate()
    p3.terminate()
"""