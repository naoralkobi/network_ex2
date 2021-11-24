import socket
import sys
import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

last_update = time.time()
add_to_queue = True


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
    def __init__(self):
        self.observer = Observer()
        self.folder = folder_path

    def run(self, queue):
        event_handler = Handler(queue)
        self.observer.schedule(event_handler, self.folder, recursive=True)
        self.observer.start()
        try:
            while True:
                connect(queue)
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
        if not add_to_queue:
            return
        if os.path.isdir(event.src_path):
            self.queue.append(Event(event.src_path, time.time(), "createFolder"))
        else:
            self.queue.append(Event(event.src_path, time.time(), "create"))
        print("Watchdog received created event - % s." % event.src_path)
        # Event is created, you can process it now

    def on_moved(self, event):
        if not add_to_queue:
            return
        # old_path = os.path.relpath(os.path.basename(event.src_path))
        # new_path = os.path.relpath(os.path.basename(event.src_dest))
        # if old_path == new_path:
        #     self.queue.append(Event(event.src_dest, time.time(), "rename"))

        self.queue.append(Event(event.src_path, time.time(), "delete"))
        if event.dest_path.startswith(folder_path) and os.path.isdir(event.dest_path):
            self.queue.append(Event(event.dest_path, time.time(), "createFolder"))
        else:
            self.queue.append(Event(event.dest_path, time.time(), "create"))
        print("Watchdog received moved event - % s." % event.src_path)

    def on_deleted(self, event):
        if not add_to_queue:
            return
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
                server_socket.sendall(b'create\n')
                send_and_create_file(server_socket, file_name)
                global last_update
                last_update = time.time()
            for dir in dirs:
                folder_name = os.path.join(path, dir)
                server_socket.sendall(b'createFolder\n')
                send_and_create_folder(server_socket, folder_name)

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


def send_and_create_folder(server_socket, folder):
    relative_path = os.path.relpath(folder, folder_path)
    server_socket.sendall(relative_path.encode() + b'\n')


def send_event_to_server(server_socket, event):
    print("action: " + event.get_action())
    server_socket.sendall(event.get_action().encode() + b'\n')

    if event.get_action() == 'create':
        print("sending file: " + event.get_file())
        send_and_create_file(server_socket, event.get_file())

    if event.get_action() == 'createFolder':
        send_and_create_folder(server_socket, event.get_file())

    if event.get_action() == 'delete':
        print("need to to do something in delete")
        file_name = os.path.relpath(event.get_file(), folder_path)
        print("relative path is: " + file_name)
        server_socket.sendall(file_name.encode("utf-8") + b'\n')

# add from here
def create_folder(folder_name):
    path = os.path.join(folder_path, folder_name)
    os.makedirs(path, exist_ok=True)


def create_file(server_source, file_name, length):
    print(f'Downloading {file_name}...\n  Expecting {length:,} bytes...', end='', flush=True)

    # new file path
    path = os.path.join(folder_path, file_name)

    # in case file's folder doesn't exist, create it
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # read current file's data
    with open(path, 'wb') as current_file:
        while length:
            current_chunk_size = min(length, 1024)
            data = server_source.read(current_chunk_size)
            if not data:
                break
            current_file.write(data)
            length -= len(data)
        else:  # only runs if while doesn't break and length==0
            print('Complete')


def delete_folder(folder):
    if os.listdir(folder):
        dir_list = os.listdir(folder)
        for file in reversed(dir_list):
            current = os.path.join(folder, file)
            if not os.path.isdir(current):
                os.remove(current)
                continue
            delete_folder(current)
    os.rmdir(folder)


def delete_file(server_source):
    path = server_source.readline().strip().decode()
    print("delete in send event_to_client: ")
    to_be_deleted = os.path.join(folder_path, path)
    print(path)
    print(to_be_deleted)
    # in case folder is empty
    if not os.path.exists(to_be_deleted):
        return
    if os.path.isdir(to_be_deleted):
        delete_folder(to_be_deleted)
    else:
        os.remove(to_be_deleted)


def get_events_from_server(server_socket):
    with server_socket.makefile('rb') as server_file:
        data = server_file.readline().strip().decode()
        while data != '':
            if data == "createFolder":
                folder_name = server_file.readline().strip().decode()
                create_folder(folder_name)

            if data == "create":
                filename = server_file.readline().strip().decode()
                length = int(server_file.readline())
                create_file(server_file, filename, length)

            if data == "delete":
                delete_file(server_file)
            print("before getting data")
            data = server_file.readline().strip().decode()
            print("data: ")
            print(data)
    print("no new events from client")
# add to here


def connect(queue):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.connect((server_ip, int(server_port)))
    print("Connected to: " + server_ip)
    with server_socket:
        global add_to_queue
        add_to_queue = False
        global last_update
        # send id to server
        server_socket.sendall(client_id.encode("utf-8") + b'\n')
        print("timer sent: ")
        print(last_update)
        server_socket.send(str(last_update).encode("utf-8") + b'\n')
        get_events_from_server(server_socket)
        add_to_queue = True

        # update server with client events
        while len(queue):
            for event in queue:
                print("deal with event")
                send_event_to_server(server_socket, event)
                queue.remove(event)
        # in case clients has no new event
        server_socket.sendall(b'\n')
    print("disconected")


def monitor_and_connect(id_number):
    queue = []
    observer = Watcher()
    observer.run(queue)


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
            client_id = sign_to_server()
            monitor_and_connect(client_id)

        if len(sys.argv) == 6:
            client_id = sys.argv[CONST.ARG_FIVE()]
            os.makedirs(folder_path, exist_ok=True)
            monitor_and_connect(client_id)

    except ValueError:
        print("Error - Wrong Arguments!")
        sys.exit(1)
