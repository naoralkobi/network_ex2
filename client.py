import socket
import sys
import string
import random
import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class Event:
    def __init__(self, file, time, action):
        self.file = file
        self.time = time
        self.action = action

    def run(self):
        # TODO - run each action
        pass


class Watcher:
    def __init__(self, folder_path, queue):
        self.observer = Observer()
        self.folder = folder_path
        self.queue = queue

    def run(self):
        event_handler = Handler(self.queue)
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

    def __init__(self, queue):
        self.queue = queue

    def on_created(self, event):
        self.queue.append(Event(event.src_path, time.time(), "create"))
        print("Watchdog received created event - % s." % event.src_path)
        # Event is created, you can process it now

    def on_modified(self, event):
        self.queue.append(Event(event.src_path, time.time(), "modify"))
        print("Watchdog received modified event - % s." % event.src_path)
        # Event is modified, you can process it now

    def on_moved(self, event):
        self.queue.append(Event(event.src_path, time.time(), "move"))
        print("Watchdog received moved event - % s." % event.src_path)

    def on_deleted(self, event):
        self.queue.append(Event(event.src_path, time.time(), "delete"))
        print("Watchdog received delete event - % s." % event.src_path)


class CONST:
    @staticmethod
    def ARG_ONE():
        return 1

    @staticmethod
    def ARG_TWO():
        return 2

    @staticmethod
    def ARG_THREE():
        return 3

    @staticmethod
    def ARG_FOUR():
        return 4

    @staticmethod
    def ARG_FIVE():
        return 5

    @staticmethod
    def STARTING_PORT():
        return 0

    @staticmethod
    def ENDING_PORT():
        return 65535


def sign_to_server(server_ip, server_port, folder_path, refresh_rate):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.connect((server_ip, int(server_port)))
    with server_socket:
        # send an empty message to get id
        server_socket.send(b' ')
        client_id = server_socket.recv(128)
        print("Server sent id: ", client_id)

        # sent every file to the server
        for path, dirs, files in os.walk(folder_path):
            for file in files:
                filename = os.path.join(path, file)
                relpath = os.path.relpath(filename, folder_path)
                filesize = os.path.getsize(filename)

                print(f'Sending {relpath}')

                # open file to be read in binary according to absolute path
                with open(filename, 'rb') as f:

                    # send relative path to the file
                    server_socket.sendall(relpath.encode() + b'\n')

                    # send file size
                    server_socket.sendall(str(filesize).encode() + b'\n')

                    # Send the file in chunks so large files can be handled.
                    data = f.read(1024)
                    while data:
                        server_socket.sendall(data)
                        data = f.read(1024)
        print('Done.')


def connect(server_ip, server_port, folder_patch, refresh_rate, id_number):
    queue = []

    # watch the folder and enter events to queue
    watchdog = Watcher(folder_patch, queue)

    while True:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.connect((server_ip, int(server_port)))
        with server_socket:

            # send id to server
            server_socket.send(id_number.encode("utf-8"))

        # time.sleep(refresh_rate)


# check if the received ip address is in correct format.
def check_ip(ip_address):
    ip = ip_address.split(".")

    # in case the address doesnt has 4 ".", it is invalid
    if len(ip) != 4:
        return False
    # in case one of the segments in the address isn't in the wanted range, it is invalid
    for num in ip:
        if int(num) > 255 or int(num) < 0:
            return False
    return True


# runs the client program
if __name__ == '__main__':
    try:
        server_ip = sys.argv[CONST.ARG_ONE()]
        server_port = sys.argv[CONST.ARG_TWO()]
        folder_patch = sys.argv[CONST.ARG_THREE()]
        refresh_rate = sys.argv[CONST.ARG_FOUR()]

        # in case the port or ip address arent valid, exit
        if int(server_port) < CONST.STARTING_PORT() or int(server_port) > CONST.ENDING_PORT() \
                or not check_ip(server_ip):
            raise ValueError

        # run client
        if len(sys.argv) == 5:
            sign_to_server(server_ip, server_port, folder_patch, refresh_rate)

        if len(sys.argv) == 6:
            client_id = sys.argv[CONST.ARG_FIVE()]
            connect(server_ip, server_port, folder_patch, refresh_rate, client_id)

    except ValueError:
        print("Error - Wrong Arguments!")
        sys.exit(1)
