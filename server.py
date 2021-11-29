import socket
import sys
import string
import random
import time
import os

clients_queues = {}


class Event:
    def __init__(self, f, t, a):
        self.file = f
        self.time = t
        self.action = a

    def get_file(self):
        return self.file

    def get_time(self):
        return self.time

    def get_action(self):
        return self.action


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
    client_id = ''.join(random.choices(string.ascii_lowercase + string.ascii_uppercase + string.digits, k=128))

    # send id to client
    client_socket.sendall(client_id.encode("utf-8") + b'\n')

    # create folder with the name : id
    os.mkdir(client_id)
    clients_queues[client_id] = []
    with client_socket, client_socket.makefile('rb') as client_file:
        while True:

            # read line from client
            action = client_file.readline().strip().decode()

            # if there are no more files, exit.
            if not action:
                break

            current_line = client_file.readline().strip().decode()
            if action == "create":
                filename = current_line
                length = int(client_file.readline())
                event_time = float(client_file.readline().strip().decode())
                if create_file(client_file, client_id, filename, length, event_time):
                    break
            elif action == "createFolder":
                folder_name = current_line
                event_time = float(client_file.readline().strip().decode())
                create_folder(client_id, folder_name, event_time)


def create_file(client_source, client_id, file_name, length, event_time):
    print(f'Downloading {file_name}...\n  Expecting {length:,} bytes...', end='', flush=True)

    # new file path
    path = os.path.join(client_id, file_name)

    # in case file's folder doesn't exist, create it
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # read current file's data
    with open(path, 'wb') as current_file:
        while length:
            current_chunk_size = min(length, 1024)
            data = client_source.read(current_chunk_size)
            if not data:
                break
            current_file.write(data)
            length -= len(data)
        else:  # only runs if while doesn't break and length==0
            print('Complete')
            create_event = Event(file_name, event_time, "create")
            clients_queues[client_id].append(create_event)


def delete_file(client_source, client_id):
    path = client_source.readline().strip().decode()
    print("delete in send event_to_client: ")
    event_time = float(client_source.readline().strip().decode())
    root_dir = os.path.abspath(os.curdir)
    folder = os.path.join(root_dir, client_id)
    to_be_deleted = os.path.join(folder, path)
    print(path)
    print(to_be_deleted)
    # in case folder is empty
    if not os.path.exists(to_be_deleted):
        return
    if os.path.isdir(to_be_deleted):
        delete_folder(to_be_deleted, client_id)
    else:
        os.remove(to_be_deleted)
    for event in clients_queues[client_id]:
        if event.get_file == path and event.get_action != "delete":
            clients_queues[client_id].remove(event.get_file)
    delete_event = Event(path, event_time, "delete")
    clients_queues[client_id].append(delete_event)


def delete_folder(folder_path, client_id):
    dir_list = os.listdir(folder_path)
    if dir_list:
        for file in reversed(dir_list):
            current = os.path.join(folder_path, file)
            if not os.path.isdir(current):
                os.remove(current)
                delete_event = Event(current, time.time(), "delete")
                clients_queues[client_id].append(delete_event)
                continue
            delete_folder(current, client_id)
    os.rmdir(folder_path)
    delete_event = Event(folder_path, time.time(), "delete")
    clients_queues[client_id].append(delete_event)


def create_folder(client_id, folder_name, event_time):
    path = os.path.join(client_id, folder_name)
    os.makedirs(path, exist_ok=True)
    create_event = Event(folder_name, event_time, "createFolder")
    clients_queues[client_id].append(create_event)


def check_for_new_events(client_socket, client_id):
    with client_socket.makefile('rb') as client_file:
        data = client_file.readline().strip().decode()
        while data != '':
            if data == "createFolder":
                folder_name = client_file.readline().strip().decode()
                event_time = float(client_file.readline().strip().decode())
                create_folder(client_id, folder_name, event_time)

            if data == "create":
                filename = client_file.readline().strip().decode()
                length = int(client_file.readline())
                event_time = float(client_file.readline().strip().decode())
                create_file(client_file, client_id, filename, length, event_time)

            if data == "delete":
                delete_file(client_file, client_id)
            print("before getting data")
            data = client_file.readline().strip().decode()
            print("data: ")
            print(data)
    print("no new events from client")


def existing_client(client_socket, client_id, client_last_update_time):
    print("1. client id got: " + client_id)
    with client_socket.makefile('rb') as client_file:
        print("2. time got:" + str(client_last_update_time))

        for event in clients_queues[client_id]:
            # in case event in queue happened after last event in client, send it to client
            if isinstance(event, Event) and client_last_update_time < event.get_time():
                print("current event time:" + str(event.get_time()))
                send_event_to_client(event, client_socket, client_id)

        client_socket.sendall(b'\n')
    # get event from client
    check_for_new_events(client_socket, client_id)


# add from here
def send_and_create_file(client_socket, file, client_id):
    current_file_path = os.path.join(os.path.join(os.path.abspath(os.curdir), client_id), file)
    try:
        with open(current_file_path, "rb") as current_file:
            file_size = os.path.getsize(current_file_path)

            client_socket.sendall(file.encode() + b'\n')

            # send file size
            client_socket.sendall(str(file_size).encode() + b'\n')

            # Send the file in chunks so large files can be handled.
            data = current_file.read(1024)
            while data:
                client_socket.sendall(data)
                data = current_file.read(1024)
    except IOError:
        client_socket.sendall(b'\n')
    print('Done.')


def send_event_to_client(event, client_socket, client_id):
    print("3. action sent: " + event.get_action())
    client_socket.sendall(event.get_action().encode() + b'\n')
    print("4. path sent: " + event.get_file())
    
    if event.get_action() == 'create':
        send_and_create_file(client_socket, event.get_file(), client_id)

    else:
        client_socket.sendall(event.get_file().encode() + b'\n')
# add to here


def server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('', int(port_number)))
    server_socket.listen(1)
    while True:
        client_socket, client_address = server_socket.accept()
        print('Connection from: ', client_address)
        with client_socket, client_socket.makefile('rb') as client_file:

            # get empty byte or id number from client
            data = client_file.readline().strip().decode()

            # in case of empty byte, give new client an id
            if data == '':
                new_client(client_socket)

            # in case of an already existing client
            else:
                client_last_update_time = float(client_file.readline().strip().decode())
                existing_client(client_socket, data, client_last_update_time)
        print('Client disconnected')


if __name__ == '__main__':
    try:
        port_number = sys.argv[CONST.ARG_ONE()]
        # in case the port or ip address arent valid, exit
        if int(port_number) < CONST.STARTING_PORT() or int(port_number) > CONST.ENDING_PORT():
            raise ValueError

        # run server
        server()
    except ValueError:
        print("Error - Wrong Arguments!")
        sys.exit(1)
