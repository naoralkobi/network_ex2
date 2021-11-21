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
    def __init__(self,):
        self.observer = Observer()
        self.folder = folder_path

    def run(self,id_number, queue):
        event_handler = Handler(queue)
        self.observer.schedule(event_handler, self.folder, recursive=True)
        self.observer.start()
        try:
            while True:
                connect(id_number, queue)
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


def sign_to_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.connect((server_ip, int(server_port)))
    with server_socket, server_socket.makefile('rb') as server_file:
        # send an empty message to get id
        server_socket.sendall(b'\n')
        client_id = server_file.readline().decode().strip()
        print("Server sent id: ", client_id)

        # send every file to the server
        for path, dirs, files in os.walk(folder_path):
            for file in files:
                file_name = os.path.join(path, file)
                relative_path = os.path.relpath(file_name, folder_path)
                print(f'Sending {relative_path}')
                send_and_create_file(server_socket, file_name)
                global last_update
                last_update = time.time()
        return client_id


def send_and_create_file(server_socket, file):
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


def send_event_to_server(server_socket, event):
    print("action: " + event.get_action())
    server_socket.sendall(event.get_action().encode() + b'\n')

    if event.get_action() == 'create':
        print("sending file: " + event.get_file())
        send_and_create_file(server_socket, event.get_file(), folder_path)
    if event.get_action() == 'modify':
        print("need to to do something in modify")
    if event.get_action() == 'move':
        print("need to to do something in move")
    if event.get_action() == 'delete':
        print("need to to do something in delete")
        # file_name = os.path.join(folder_path, event.get_file())
        file_name = os.path.relpath(event.get_file(), folder_path)
        print("realative path is: " + file_name)
        server_socket.send(file_name.encode("utf-8"))


# def get_events_from_server(server_socket):
#     print("get_events_from_server")
#     file_path = server_socket.recv(128).decode('utf-8')
#     print(file_path)
#     file_size = server_socket.recv(128).decode('utf-8')
#     print(file_size)
#     # open file in client dir and write the data.
#     path = os.path.join(folder_path, file_path)
#     print(path)
#     with open(path, 'wb') as current_file:
#         data = server_socket.recv(128).decode('utf-8')
#         while data:
#             current_file.write(data)
#             data = server_socket.recv(128).decode('utf-8')


def connect(id_number, queue):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.connect((server_ip, int(server_port)))
    print("Connected to: " + server_ip)
    with server_socket:
        # global last_update
        # # send id to server
        server_socket.sendall(id_number.encode("utf-8") + b'\n')
        # print("timer sent: ")
        # print(last_update)
        # server_socket.send(str(last_update).encode("utf-8"))
        # get_events_from_server()

        # update server with client events
        while len(queue):
            for event in queue:
                print("deal with event")
                send_event_to_server(server_socket, event, folder_path)
                queue.remove(event)
        # in case clients has no new event
        server_socket.sendall(b'\n')
    print("disconected")


def monitor_and_connect(id_number):
    queue = []
    observer = Watcher(folder_path)
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
        folder_path = sys.argv[CONST.ARG_THREE()]
        refresh_rate = int(sys.argv[CONST.ARG_FOUR()])

        # in case the port or ip address arent valid, exit
        if int(server_port) < CONST.STARTING_PORT() or int(server_port) > CONST.ENDING_PORT() \
                or not check_ip(server_ip):
            raise ValueError

        # run client
        if len(sys.argv) == 5:
            client_id = sign_to_server(server_ip, server_port, folder_path)
            monitor_and_connect(server_ip, server_port, folder_path, refresh_rate, client_id)

        if len(sys.argv) == 6:
            client_id = sys.argv[CONST.ARG_FIVE()]
            monitor_and_connect(server_ip, server_port, folder_path, refresh_rate, client_id)

    except ValueError:
        print("Error - Wrong Arguments!")
        sys.exit(1)
