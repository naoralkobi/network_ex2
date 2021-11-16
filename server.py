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


def file_path(relative_path):
    dir = os.path.dirname(os.path.abspath(__file__))
    split_path = relative_path.split("/")
    new_path = os.path.join(dir, *split_path)
    return new_path


def server(port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('', int(port)))
    server.listen(5)
    while True:
        client_socket, client_address = server.accept()
        print('Connection from: ', client_address)
        # get id 0
        data = client_socket.recv(1024)
        # in case the first bit(flag) is off, give new client an id
        if int(data[0:1]) == 0:
            id = ''.join(random.choices(string.ascii_lowercase + string.ascii_uppercase + string.digits, k=128))

            # print("random id: " + str(id))
            client_socket.send(id.encode("utf-8"))

            # create folder with the name : id
            os.mkdir(id)

            # TODO need to open file in id to write the data.
            file_name = client_socket.recv(1024)
            client_socket.send(b"got it")
            file_name = str(file_name)
            print(file_name)

            # get root dir.
            root_dir = os.path.abspath(os.curdir)

            file_to_write = open(root_dir + "/" + id + "/" + file_name, "wb")

            data = client_socket.recv(1024)
            while data != b'finish':
                file_to_write.write(data)
                data = client_socket.recv(1024)
            if data == b'finish':
                client_socket.send(b"got it")
                file_to_write.close()
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
