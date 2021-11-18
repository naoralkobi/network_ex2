import socket
import sys
import string
import random
import time
import os


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

clients_queues = {}

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
    id = ''.join(random.choices(string.ascii_lowercase + string.ascii_uppercase + string.digits, k=128))

    # send id to client
    client_socket.send(id.encode("utf-8"))

    # create folder with the name : id
    os.mkdir(id)
    clients_queues[id] = []
    with client_socket, client_socket.makefile('rb') as clientfile:
        while True:

            # read line from client
            current_line = clientfile.readline()

            # if there are no more files, exit.
            if not current_line:
                break

            filename = current_line.strip().decode()
            length = int(clientfile.readline())

            print(f'Downloading {filename}...\n  Expecting {length:,} bytes...', end='', flush=True)

            # new file path
            path = os.path.join(id, filename)

            # in case file's folder doesn't exist, create it
            os.makedirs(os.path.dirname(path), exist_ok=True)

            # read current file's data
            with open(path, 'wb') as current_file:
                while length:
                    current_chunk_size = min(length, 1024)
                    data = clientfile.read(current_chunk_size)
                    if not data:
                        break
                    current_file.write(data)
                    length -= len(data)
                else:  # only runs if while doesn't break and length==0
                    print('Complete')
                    create_event = Event(filename, time.time(), "create")
                    clients_queues[id].append(create_event)
                    print(clients_queues)
                    continue

            # socket was closed early.
            print('Incomplete')
            break


def existing_client(client_socket, client_id):
    print("client id: " + client_id)
    client_last_update_time = float(client_socket.recv(1024).decode("utf-8"))
    print(client_last_update_time)
    for event in clients_queues[client_id]:
        if isinstance(event) == Event:
            print("good")
        # if client_last_update_time > (Event)event.


def server(port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('', int(port)))
    server.listen(1)
    while True:
        client_socket, client_address = server.accept()
        print('Connection from: ', client_address)
        with client_socket:

            # get empty byte or id number from client
            data = client_socket.recv(128)

            # in case of empty byte, give new client an id
            if data == b' ':
                new_client(client_socket)

            # in case of an already existing client
            else:
                existing_client(client_socket, data.decode("utf-8"))
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
