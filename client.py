import socket
import sys
import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# time of last update got from server
last_update = 0

# list of updates from server
clients_events = []


# holds information about the events in the folder - file, time and action
class Event:

    # constructor
    def __init__(self, new_path, time, action, old_path):
        self.new_path = new_path
        self.time = time
        self.action = action
        self.old_path = old_path

    # getter for old path
    def get_old_path(self):
        return self.old_path

    # getter for new_path
    def get_new_path(self):
        return self.new_path

    # getter for time
    def get_time(self):
        return self.time

    # getter for action
    def get_action(self):
        return self.action


# watch the folder and notify handler when change occurs
class Watcher:

    # constructor
    def __init__(self):
        self.observer = Observer()

        # watch folder that has been received in args
        self.folder = folder_path

    # run the watcher
    def run(self, queue):
        event_handler = Handler(queue)
        self.observer.schedule(event_handler, self.folder, recursive=True)
        self.observer.start()
        try:
            while True:
                # sync with server
                sync(queue)
                print("going to sleep")
                # wait the received amount of seconds and re-sync
                time.sleep(refresh_rate)
        except:
            self.observer.stop()
            print("Observer Stopped")
            self.observer.join()


# Handel every type of change in the folder
class Handler(FileSystemEventHandler):
    patterns = ["*.fits"]

    # constructor
    def __init__(self, queue):
        self.queue = queue

    # in case of new file or folder
    def on_created(self, event):

        # file name
        name = os.path.basename(event.src_path)

        # in case we dont want to save changes in queue or edited file, exit
        if name[0:14] == ".goutputstream":
            return

        if is_sent_from_server(event):
            print("pass this event: " + event.src_path)
            return

        # if it is folder - add event of new folder
        if os.path.isdir(event.src_path):
            self.queue.append(Event(event.src_path, time.time(), "createFolder", event.src_path))
        else:
            self.queue.append(Event(event.src_path, time.time(), "create", event.src_path))
        print("Watchdog received created event - % s." % event.src_path)
        # Event is created, you can process it now

    # in a file has moved in or from the folder
    def on_moved(self, event):

        # file name
        name = os.path.basename(event.src_path)

        if is_sent_from_server(event):
            print("pass this event: " + event.src_path)
            return

        # in case of edited file, delete original and send edited one
        if name[0:14] == ".goutputstream":
            self.queue.append(Event(event.dest_path, time.time(), "delete", event.dest_path))
            self.queue.append(Event(event.dest_path, time.time(), "create", event.dest_path))
            return

        # in case of the new path is not in client folder.
        if not event.dest_path.startswith(folder_path):
            self.queue.append(Event(event.src_path, time.time(), "delete", event.dest_path))

        # in case of moving folder, create event of new folder
        if event.is_directory:
            print(event.src_path)
            print(event.dest_path)
            self.queue.append(Event(event.src_path, time.time(), "moveFolder", event.dest_path))
            self.queue.append(Event(event.src_path, time.time(), "delete", event.dest_path))
        else:
            self.queue.append(Event(event.dest_path, time.time(), "move", event.src_path))
        print("Watchdog received moved event - % s." % event.src_path)
        print("event move to - % s." % event.dest_path)

    # in case of deleted file or folder
    def on_deleted(self, event):

        if is_sent_from_server(event):
            print("pass this event: " + event.src_path)
            return

        self.queue.append(Event(event.src_path, time.time(), "delete", event.src_path))
        print("Watchdog received delete event - % s." % event.src_path)


# return true if the event is already know because it is sent from server
def is_sent_from_server(event):
    for current_event in clients_events:
        print("check if already handle this event: ")
        print(current_event.file)
        if current_event.file == event.src_path:
            print("do not add to list.")
            return True
    return False


# program constants
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

    @staticmethod
    def CHUNK_SIZE():
        return 1024

    @staticmethod
    def DOTS_NUM():
        return 4

    @staticmethod
    def IP_MAX_RANGE():
        return 255

    @staticmethod
    def IP_MIN_RANGE():
        return 0


# sign new client to server, send all files in folder to it and return client id that the server sent
def sign_to_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.connect((server_ip, int(server_port)))
    with server_socket, server_socket.makefile('rb') as server_file:

        # send request to get id
        server_socket.sendall(b'\n')
        client_id = server_file.readline().decode().strip()
        print("Server sent id: ", client_id)

        global last_update
        # send every file in the folder to server
        for path, dirs, files in os.walk(folder_path):
            for file in files:

                # last update time is current time
                last_update = time.time()
                file_name = os.path.join(path, file)
                relative_path = os.path.relpath(file_name, folder_path)
                print(f'Sending {relative_path}')

                # send create new file command
                server_socket.sendall(b'create\n')

                # send file to server
                send_and_create_file(server_socket, file_name, str(last_update))
            for dir in dirs:

                # last update time is current time
                last_update = time.time()
                folder_name = os.path.join(path, dir)

                # send create new folder command
                server_socket.sendall(b'createFolder\n')

                # send new folder to server
                send_and_create_folder(server_socket, folder_name, str(last_update))

    # return the new client id
    return client_id


# send file and time of creation to the server
def send_and_create_file(server_socket, file, event_time):
    with open(file, "rb") as current_file:

        relative_path = os.path.relpath(file, folder_path)
        file_size = os.path.getsize(file)

        # send path to create file
        server_socket.sendall(relative_path.encode() + b'\n')

        # send file size
        server_socket.sendall(str(file_size).encode() + b'\n')

        # send creation event time
        server_socket.sendall(event_time.encode() + b'\n')

        # send the file in chunks
        data = current_file.read(CONST.CHUNK_SIZE())
        while data:
            server_socket.sendall(data)
            data = current_file.read(CONST.CHUNK_SIZE())
    print('Done.')


# send file and time of moving to the server
def send_and_move_file(server_socket, dest, event_time, src):
    print(dest)
    print(src)
    relative_dest = os.path.relpath(dest, folder_path)
    relative_src = os.path.relpath(src, folder_path)

    # send src path
    server_socket.sendall(relative_src.encode() + b'\n')

    # send path to move file
    server_socket.sendall(relative_dest.encode() + b'\n')

    # send creation event time
    server_socket.sendall(event_time.encode() + b'\n')

    print('Done.')


# send folder and time of creation to the server
def send_and_create_folder(server_socket, folder, event_time):
    relative_path = os.path.relpath(folder, folder_path)

    # send path to be created at
    server_socket.sendall(relative_path.encode() + b'\n')

    # send creation time event
    server_socket.sendall(event_time.encode() + b'\n')


# # send file and time of moving to the server
# def send_and_move_folder(server_socket, dest, event_time, src):
#     print(dest)
#     print(src)
#     relative_dest = os.path.relpath(dest, folder_path)
#     relative_src = os.path.relpath(src, folder_path)


# send new event to the server and it's info
def send_event_to_server(server_socket, event):
    print("action: " + event.get_action())
    # send the event action
    server_socket.sendall(event.get_action().encode() + b'\n')

    # in case of file creation, send it's event
    if event.get_action() == 'create':
        print("sending file: " + event.get_new_path())
        send_and_create_file(server_socket, event.get_new_path(), str(time.time()))

    # in case of folder creation, send it's event
    if event.get_action() == 'createFolder':
        send_and_create_folder(server_socket, event.get_new_path(), str(time.time()))

    # in case of file creation, send it's event
    if event.get_action() == 'move':
        print("moving file: " + event.get_new_path())
        send_and_move_file(server_socket, event.get_new_path(), str(time.time()), event.get_old_path())

    # in case of folder creation, send it's event
    if event.get_action() == 'moveFolder':
        send_and_move_file(server_socket, event.get_new_path(), str(time.time()), event.get_old_path())

    # in case of file or folder deletion, send it's event
    if event.get_action() == 'delete':
        print("need to to do something in delete")
        file_name = os.path.relpath(event.get_new_path(), folder_path)
        print("relative path is: " + file_name)
        server_socket.sendall(file_name.encode("utf-8") + b'\n')

        # send path to be deleted
        server_socket.sendall(str(last_update).encode() + b'\n')


# create folder with the received name in the client folder
def create_folder(folder_name):
    path = os.path.join(folder_path, folder_name)
    os.makedirs(path, exist_ok=True)


# receive and create file in the client folder
def create_file(server_source, file_name, length):
    print(f'Downloading {file_name}...\n  Expecting {length:,} bytes...', end='', flush=True)

    # new file path
    path = os.path.join(folder_path, file_name)

    # in case file's folder doesn't exist, create it
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # read current file's data
    with open(path, 'wb') as current_file:
        while length:
            current_chunk_size = min(length, CONST.CHUNK_SIZE())
            data = server_source.read(current_chunk_size)
            if not data:
                break
            current_file.write(data)
            length -= len(data)


# delete received folder and it's content
def delete_folder(folder):

    # in case it's not empty, delete all content
    if os.listdir(folder):
        dir_list = os.listdir(folder)
        for file in reversed(dir_list):
            current = os.path.join(folder, file)

            # in case current is file, remove it
            if not os.path.isdir(current):
                os.remove(current)
                continue
            # else, delete current folder
            delete_folder(current)
    # delete the folder
    os.rmdir(folder)


# delete file in received path
def delete_file(path):
    print("recived path in delete_file: ")
    print(path)
    to_be_deleted = os.path.join(folder_path, path)
    print("deleteing: ")
    print(to_be_deleted)
    # in case it doesnt exist, exit
    if not os.path.exists(to_be_deleted):
        return

    # in case path is a folder, delete it
    if os.path.isdir(to_be_deleted):
        delete_folder(to_be_deleted)

    # else, delete the file
    else:
        os.remove(to_be_deleted)


# check if server has new events to send to client
def get_events_from_server(server_socket):
    with server_socket.makefile('rb') as server_file:

        # current event action
        action = server_file.readline().strip().decode()
        print("3. received action: " + action)

        # get all new events and implement them in the client folder
        while action != '':

            # file path
            new = server_file.readline().strip().decode()
            print("path: " + new)
            old = server_file.readline().strip().decode()

            # if empty path, it's a file that already been deleted
            if new == '':

                # get next action and continue in the loop
                action = server_file.readline().strip().decode()
                print("3. received action: " + action)
                continue
            print("4. received path: " + new)
            path = os.path.join(folder_path, new)
            print("local path: " + path)
            old = os.path.join(folder_path, old)

            create_event = Event(path, time.time(), action, old)
            clients_events.append(create_event)

            # in case of new folder event, create it
            if action == "createFolder":
                create_folder(path)

            # in case of new file event, create it
            if action == "create":
                length = int(server_file.readline())
                create_file(server_file, path, length)

            # in case delete event, delete the file
            if action == "delete":
                delete_file(path)

            if action == "move":
                print("stage 1")

            if action == "moveFolder":
                print("stage 2")
            print("before getting action")

            # get next event action
            action = server_file.readline().strip().decode()
            print("action: ")
            print(action)
    global last_update

    # update the last update from server time
    last_update = time.time()
    print("no new events from client")


# sync with the server - send new event and receive new events
def sync(queue):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.connect((server_ip, int(server_port)))
    print("Connected to: " + server_ip)
    with server_socket:
        #global add_to_queue

        # when server send events, we wont add these events to the queue of events
        #add_to_queue = False
        global last_update
        global clients_events
        print("1. id sent: " + client_id)
        # send id to server
        server_socket.sendall(client_id.encode("utf-8") + b'\n')
        print("2. time sent: " + str(last_update))
        # send last update time to server
        server_socket.send(str(last_update).encode("utf-8") + b'\n')
        # get from server events that happened after last update time
        get_events_from_server(server_socket)

        # keep adding new events to queue
        #add_to_queue = True
        clients_events.clear()

        # send to server new client events
        while len(queue):
            for event in queue:
                print("deal with event")
                # send current event
                send_event_to_server(server_socket, event)

                # remove current event from queue
                queue.remove(event)
        # in case clients has no new event
        server_socket.sendall(b'\n')
    print("disconected")


# watch the client folder and, add new events to queue and sync with server
def monitor_and_sync():
    queue = []
    observer = Watcher()
    observer.run(queue)


# check if the received ip address is in correct format.
def check_ip(ip_address):
    ip = ip_address.split(".")

    # in case the address doesnt has 4 ".", it is invalid
    if len(ip) != CONST.DOTS_NUM():
        return False
    # in case one of the segments in the address isn't in the wanted range, it is invalid
    for num in ip:
        if int(num) > CONST.IP_MAX_RANGE() or int(num) < CONST.IP_MIN_RANGE():
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

        # in case of new client
        if len(sys.argv) == 5:
            client_id = sign_to_server()
            monitor_and_sync()

        # in case of existing client - sync with server
        if len(sys.argv) == 6:
            client_id = sys.argv[CONST.ARG_FIVE()]
            os.makedirs(folder_path, exist_ok=True)
            monitor_and_sync()

    except ValueError:
        print("Error - Wrong Arguments!")
        sys.exit(1)
