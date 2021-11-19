import socket
import sys
import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

last_update = 0


class Event:
    def __init__(self, file, time, action):
        self.file = file
        self.time = time
        self.action = action

    def get_file(self):
        return self.file

    def get_time(self):
        return self.time

    def get_action(self):
        return self.action


class Watcher:
    def __init__(self, folder_path):
        self.observer = Observer()
        self.folder = folder_path

    def run(self, server_ip, server_port, refresh_rate, id_number, queue):
        event_handler = Handler(queue)
        self.observer.schedule(event_handler, self.folder, recursive=True)
        self.observer.start()
        try:
            while True:
                connect(server_ip, server_port, folder_patch, refresh_rate, id_number, queue)
                print("going to sleep")
                time.sleep(refresh_rate)
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
        # self.queue.append(Event(event.src_path, time.time(), "modify"))
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


def sign_to_server(server_ip, server_port, folder_path):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.connect((server_ip, int(server_port)))
    with server_socket:
        # send an empty message to get id
        server_socket.send(b' ')
        client_id = server_socket.recv(128).decode('utf-8')
        print("Server sent id: ", client_id)

        # send every file to the server
        for path, dirs, files in os.walk(folder_path):
            for file in files:
                file_name = os.path.join(path, file)
                relative_path = os.path.relpath(file_name, folder_path)
                print(f'Sending {relative_path}')
                send_and_create_file(server_socket, file_name, folder_path)
                global last_update
                last_update = time.time()
        return client_id


def send_and_create_file(server_socket, file, folder_path):
    with open(file, "rb") as current_file:
        relative_path = os.path.relpath(file, folder_path)
        file_size = os.path.getsize(file)
        server_socket.sendall(relative_path.encode() + b'\n')

        # send file size
        server_socket.sendall(str(file_size).encode() + b'\n')

        # Send the file in chunks so large files can be handled.
        data = current_file.read(1024)
        while data:
            server_socket.sendall(data)
            data = current_file.read(1024)
    print('Done.')


def send_event_to_server(server_socket, event, folder_path):
    print("action: " + event.get_action())
    server_socket.send(event.get_action().encode("utf-8"))
    ack = server_socket.recv(1024)
    if ack == b' ':
        print("got ack")

    if event.get_action() == 'create':
        print("sending file: " + event.get_file())
        send_and_create_file(server_socket, event.get_file(), folder_path)


def get_events_from_server():
    pass
    # TODO


def connect(server_ip, server_port, folder_path, refresh_rate, id_number, queue):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.connect((server_ip, int(server_port)))
    print("Connected to: " + server_ip)
    with server_socket:
        # global last_update
        # # send id to server
        server_socket.send(id_number.encode("utf-8"))
        # print("timer sent: ")
        # print(last_update)
        # server_socket.send(str(last_update).encode("utf-8"))
        # get_events_from_server()

        # update server with client events
        while len(queue):
            for event in queue:
                send_event_to_server(server_socket, event, folder_path)
                queue.remove(event)
        # in case clients has no new event
        server_socket.send(b' ')
        ack = server_socket.recv(1024)
        if ack == b' ':
            print("got finishing ack")
    print("disconected")


def monitor_and_connect(server_ip, server_port, folder_patch, refresh_rate, id_number):
    queue = []
    observer = Watcher(folder_patch)
    observer.run(server_ip, server_port, refresh_rate, id_number, queue)


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
        refresh_rate = int(sys.argv[CONST.ARG_FOUR()])

        # in case the port or ip address arent valid, exit
        if int(server_port) < CONST.STARTING_PORT() or int(server_port) > CONST.ENDING_PORT() \
                or not check_ip(server_ip):
            raise ValueError

        # run client
        if len(sys.argv) == 5:
            client_id = sign_to_server(server_ip, server_port, folder_patch)
            monitor_and_connect(server_ip, server_port, folder_patch, refresh_rate, client_id)

        if len(sys.argv) == 6:
            client_id = sys.argv[CONST.ARG_FIVE()]
            monitor_and_connect(server_ip, server_port, folder_patch, refresh_rate, client_id)

    except ValueError:
        print("Error - Wrong Arguments!")
        sys.exit(1)
