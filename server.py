import socket
import sys
import string
import random
import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class Watcher:
    def __init__(self, folder_path):
        self.observer = Observer()
        self.folder = folder_path

    def run(self):
        event_handler = Handler()
        self.observer.schedule(event_handler, self.folder, recursive=True)
        self.observer.start()
        try:
            while True:
                time.sleep(5)
        except:
            self.observer.stop()
            print("Observer Stopped")

        self.observer.join()


class Handler(FileSystemEventHandler):
    patterns = ["*.fits"]

    def on_created(self, event):
        print("Watchdog received created event - % s." % event.src_path)
        # Event is created, you can process it now

    def on_modified(self, event):
        print("Watchdog received modified event - % s." % event.src_path)
        # Event is modified, you can process it now

    def on_moved(self, event):
        pass

    def on_deleted(self, event):
        pass


class CONST:
    @staticmethod
    def ARG_ONE():
        return 1

    @staticmethod
    def STARTING_PORT():
        return 0

    @staticmethod
    def ENDING_PORT():
        return 65535


def new_client(client_socket):
    # create new random id for client
    id = ''.join(random.choices(string.ascii_lowercase + string.ascii_uppercase + string.digits, k=128))

    # send id to client
    client_socket.send(id.encode("utf-8"))

    # create folder with the name : id
    os.mkdir(id)
    with client_socket, client_socket.makefile('rb') as clientfile:
        while True:

            # read line from client
            current_line = clientfile.readline()

            # if there are no more files, exit.
            if not current_line:
                break

            filename = current_line.strip().decode()
            length = int(clientfile.readline())

            print(f'Downloading {filename}...\n  Expecting {length:,} bytes...', end='', flush=True)

            # new file path
            path = os.path.join(id, filename)

            # in case file's folder doesn't exist, create it
            os.makedirs(os.path.dirname(path), exist_ok=True)

            # read current file's data
            with open(path, 'wb') as f:
                while length:
                    current_chunk_size = min(length, 1024)
                    data = clientfile.read(current_chunk_size)
                    if not data:
                        break
                    f.write(data)
                    length -= len(data)
                else:  # only runs if while doesn't break and length==0
                    print('Complete')
                    continue

            # socket was closed early.
            print('Incomplete')
            break


def server(port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('', int(port)))
    server.listen(5)
    while True:
        client_socket, client_address = server.accept()
        print('Connection from: ', client_address)
        with client_socket:
            # get id 0
            data = client_socket.recv(1024)
            # in case the first bit(flag) is off, give new client an id
            if int(data[0:1]) == 0:
                new_client(client_socket)

            # in case of an already existing client
            # else:
            # TODO - update the client folder
        print('Client disconnected')


if __name__ == '__main__':
    try:
        port_number = sys.argv[CONST.ARG_ONE()]
        # in case the port or ip address arent valid, exit
        if int(port_number) < CONST.STARTING_PORT() or int(port_number) > CONST.ENDING_PORT():
            raise ValueError

        # run server
        server(port_number)
    except ValueError:
        print("Error - Wrong Arguments!")
        sys.exit(1)
