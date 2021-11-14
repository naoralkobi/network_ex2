import socket
import sys
import string
import random
import time
import watchdog
import os


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
    clients = {}
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('', int(port)))
    server.listen(5)
    while True:
        client_socket, client_address = server.accept()
        print('Connection from: ', client_address)

        data = client_socket.recv(100)
        print('Received: ', data)

        # in case the first bit(flag) is off, give new client an id
        if int(data[0:1]) == 0:
            id = ''.join(random.choices(string.ascii_lowercase + string.ascii_uppercase + string.digits, k=128))
            clients[id] = None
            print("random i: " + str(id))
            client_socket.send(id.encode("utf-8"))

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
