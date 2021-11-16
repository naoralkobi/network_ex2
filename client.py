import socket
import sys
import string
import random
import time
import os


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


def sign_to_server(server_ip, server_port, folder_path, refresh_rate):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.connect((server_ip, int(server_port)))
    with server_socket:
        # sent a 0 flag to get new id
        server_socket.send(b'0')
        client_id = server_socket.recv(128)
        print("Server sent id: ", client_id)

        # sent every file to the server
        for path, dirs, files in os.walk(folder_path):
            for file in files:
                filename = os.path.join(path, file)
                relpath = os.path.relpath(filename, folder_path)
                filesize = os.path.getsize(filename)

                print(f'Sending {relpath}')

                # open file to be read in binary according to absolute path
                with open(filename, 'rb') as f:

                    # send relative path to the file
                    server_socket.send(relpath.encode() + b'\n')

                    # send file size
                    server_socket.send(str(filesize).encode() + b'\n')

                    data = f.read(1024)

                    # send file's data to the server
                    while not data:
                        server_socket.send(data)
                        data = f.read(1024)
            print('Done.')


def connect(server_ip, server_port, folder_patch, refresh_rate, id_number):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((server_ip, int(server_port)))


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
        refresh_rate = sys.argv[CONST.ARG_FOUR()]

        # in case the port or ip address arent valid, exit
        if int(server_port) < CONST.STARTING_PORT() or int(server_port) > CONST.ENDING_PORT() \
                or not check_ip(server_ip):
            raise ValueError

        # run client
        if len(sys.argv) == 5:
            sign_to_server(server_ip, server_port, folder_patch, refresh_rate)

        if len(sys.argv) == 6:
            client_id = sys.argv[CONST.ARG_FIVE()]
            connect(server_ip, server_port, folder_patch, refresh_rate, client_id)

    except ValueError:
        print("Error - Wrong Arguments!")
        sys.exit(1)
