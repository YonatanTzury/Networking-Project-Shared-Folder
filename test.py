import os
import time
import subprocess


def check_folders(files):
    cl1 = os.listdir('client_1')
    cl2 = os.listdir('client_1')
    if cl1 != files or cl2 != files:
        raise Exception('Wrong dir list')

def is_lock(path):
    failed = False
    try:
        f = open(path, 'w')
        f.close()
    except OSError:
        failed = True

    return failed

os.system('rm -rf server client_1 client_2')

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

    os.unlink('client_1/first')

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