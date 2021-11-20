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

    @staticmethod
    def send_event_to_client(event, client_socket, client_id):
        if event.get_action() == "create":
            with open(os.path.join(client_id, event.get_file()), 'rb') as current_file:
                # send relative path to the file
                client_socket.sendall(event.get_file().encode() + b'\n')
                file_size = os.path.getsize(os.path.join(client_id, event.get_file()))
                # send file size
                client_socket.sendall(str(file_size).encode() + b'\n')
                # Send the file in chunks so large files can be handled.
                data = current_file.read(1024)
                while data:
                    client_socket.sendall(data)
                    data = current_file.read(1024)

        if event.get_action() == "modify":
            pass  # TODO
        if event.get_action() == "move":
            pass  # TODO
        if event.get_action() == "delete":
            pass  # TODO

        print('Done.')


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
            current_line = client_file.readline()

            # if there are no more files, exit.
            if not current_line:
                break

            filename = current_line.strip().decode()
            length = int(client_file.readline())

            print(f'Downloading {filename}...\n  Expecting {length:,} bytes...', end='', flush=True)

            # new file path
            path = os.path.join(client_id, filename)

            # in case file's folder doesn't exist, create it
            os.makedirs(os.path.dirname(path), exist_ok=True)

            # read current file's data
            with open(path, 'wb') as current_file:
                while length:
                    current_chunk_size = min(length, 1024)
                    data = client_file.read(current_chunk_size)
                    if not data:
                        break
                    current_file.write(data)
                    length -= len(data)
                else:  # only runs if while doesn't break and length==0
                    print('Complete')
                    create_event = Event(filename, time.time(), "create")
                    clients_queues[client_id].append(create_event)
                    # print(clients_queues)
                    continue

            # socket was closed early.
            print('Incomplete')
            break


def check_for_new_events(client_socket, client_id):
    with client_socket.makefile('rb') as client_file:
        data = client_file.readline().strip().decode()
        while data != '':
            if data == "create":

                filename = client_file.readline().strip().decode()
                length = int(client_file.readline())

                print(f'Downloading {filename}...\n  Expecting {length:,} bytes...', end='', flush=True)

                # new file path
                path = os.path.join(client_id, filename)

                # in case file's folder doesn't exist, create it
                os.makedirs(os.path.dirname(path), exist_ok=True)

                # read current file's data
                with open(path, 'wb') as current_file:
                    while length:
                        current_chunk_size = min(length, 1024)
                        data = client_file.read(current_chunk_size)
                        if not data:
                            break
                        current_file.write(data)
                        length -= len(data)
                    else:  # only runs if while doesn't break and length==0
                        print('Complete')
                        create_event = Event(filename, time.time(), "create")
                        clients_queues[client_id].append(create_event)
            print("before getting data")
            data = client_file.readline().strip().decode()
            print("data: ")
            print(data)

    print("no new events from client")


def existing_client(client_socket, client_id):
    print("client id: " + client_id)
    # client_last_update_time = float(client_socket.recv(1024).decode("utf-8"))
    # print(client_last_update_time)
    # for event in clients_queues[client_id]:
    #     # in case event in queue happened after last event in client, send it to client
    #     if isinstance(event, Event) and client_last_update_time > event.get_time():
    #         Event.send_event_to_client(event, client_socket, client_id)
    # get event from client
    check_for_new_events(client_socket, client_id)


def server(port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('', int(port)))
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
        server(port_number)
    except ValueError:
        print("Error - Wrong Arguments!")
        sys.exit(1)
