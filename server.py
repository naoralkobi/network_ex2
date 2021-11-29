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
                if create_file(client_file, client_id, filename, length):
                    break
            elif action == "createFolder":
                folder_name = current_line
                create_folder(client_id, folder_name)


def create_file(client_source, client_id, file_name, length):
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
            create_event = Event(file_name, time.time(), "create")
            clients_queues[client_id].append(create_event)


def delete_file(client_source, client_id):
    path = client_source.readline().strip().decode()
    print("delete in send event_to_client: ")
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
    delete_event = Event(path, time.time(), "delete")
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


def create_folder(client_id, folder_name):
    path = os.path.join(client_id, folder_name)
    os.makedirs(path, exist_ok=True)
    create_event = Event(folder_name, time.time(), "createFolder")
    clients_queues[client_id].append(create_event)


def check_for_new_events(client_socket, client_id):
    with client_socket.makefile('rb') as client_file:
        data = client_file.readline().strip().decode()
        while data != '':
            if data == "createFolder":
                folder_name = client_file.readline().strip().decode()
                create_folder(client_id, folder_name)

            if data == "create":
                filename = client_file.readline().strip().decode()
                length = int(client_file.readline())
                create_file(client_file, client_id, filename, length)

            if data == "move":
                print("move in send event_to_client")
                dest_path = client_file.readline().strip().decode()
                src_path = client_file.readline().strip().decode()
                # the new path is in the client folder
                if dest_path != b'':
                    create_event = Event(dest_path, time.time(), "create")
                    clients_queues[client_id].append(create_event)
                # delete original file.
                create_event = Event(src_path, time.time(), "delete")
                clients_queues[client_id].append(create_event)

            if data == "delete":
                delete_file(client_file, client_id)
            print("before getting data")
            data = client_file.readline().strip().decode()
            print("data: ")
            print(data)
    print("no new events from client")


def existing_client(client_socket, client_id):
    print("client id: " + client_id)
    with client_socket.makefile('rb') as client_file:
        client_last_update_time = float(client_file.readline().strip().decode())
        print("time got:")
        print(client_last_update_time)

        for event in clients_queues[client_id]:
            # in case event in queue happened after last event in client, send it to client
            if isinstance(event, Event) and client_last_update_time < event.get_time():
                print("current event time:")
                print(event.get_time())
                send_event_to_client(event, client_socket, client_id)

        client_socket.sendall(b'\n')
    # get event from client
    check_for_new_events(client_socket, client_id)


# add from here
def send_and_create_file(client_socket, file, client_id):
    relative_path = os.path.join(os.path.join(os.path.abspath(os.curdir), client_id), file)
    with open(relative_path, "rb") as current_file:
        file_size = os.path.getsize(relative_path)
        client_socket.sendall(relative_path.encode() + b'\n')

        # send file size
        client_socket.sendall(str(file_size).encode() + b'\n')

        # Send the file in chunks so large files can be handled.
        data = current_file.read(1024)
        while data:
            client_socket.sendall(data)
            data = current_file.read(1024)
    print('Done.')


def send_and_create_folder(client_socket, folder, client_id):
    relative_path = os.path.relpath(folder, os.path.join(os.path.abspath(os.curdir), client_id))
    client_socket.sendall(relative_path.encode() + b'\n')


def send_event_to_client(event, client_socket, client_id):
    print("action: " + event.get_action())
    client_socket.sendall(event.get_action().encode() + b'\n')

    if event.get_action() == 'create':
        print("sending file: " + event.get_file())
        send_and_create_file(client_socket, event.get_file(), client_id)

    if event.get_action() == 'createFolder':
        send_and_create_folder(client_socket, event.get_file(), client_id)

    if event.get_action() == 'delete':
        folder_path = os.path.join(os.path.abspath(os.curdir), client_id)
        print("need to to do something in delete")
        file_name = os.path.relpath(event.get_file(), folder_path)
        print("relative path is: " + file_name)
        client_socket.sendall(file_name.encode("utf-8") + b'\n')
# add from here


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
                existing_client(client_socket, data)
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
