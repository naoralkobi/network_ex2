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


def server(port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('', int(port)))
    server.listen(5)
    flag = True
    while True:
        client_socket, client_address = server.accept()
        print('Connection from: ', client_address)
        # get id 0
        data = client_socket.recv(1024)
        # in case the first bit(flag) is off, give new client an id
        if int(data[0:1]) == 0:
            id = ''.join(random.choices(string.ascii_lowercase + string.ascii_uppercase + string.digits, k=128))

            print("random id: " + str(id))
            client_socket.send(id.encode("utf-8"))

            folder_path = client_socket.recv(1024)
            print(str(folder_path))
            path = os.path.join(path, str(id))
            os.mkdir(id)

            file_path = client_socket.recv(1024)
            name, extension = os.path.splitext(file_path)
            print("the file name: ")
            print(name)
            print("the file extension: ")
            print(extension)
            file_name = os.path.basename(name)
            f = open(file_name + extension, "w")


            data = client_socket.recv(1024)
            print(data.decode('utf-8'), end='')

        # in case of an already existing client
        # else:
        # TODO - update the client folder
        client_socket.close()
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
