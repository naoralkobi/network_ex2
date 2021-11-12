import socket
import sys

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
    def STARTING_PORT():
        return 0

    @staticmethod
    def ENDING_PORT():
        return 65535


def connect(server_ip, server_port, folder_patch, refresh_rate):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((server_ip, int(server_port)))

    # sent a 0 flag to get new id
    s.send(b'0')

    id = s.recv(128)
    print("Server sent id: ", id)

    s.close()


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
            connect(server_ip, server_port, folder_patch, refresh_rate)
        # if len(sys.argv) == 6:
            # TODO - update folder using server

    except ValueError:
        print("Error - Wrong Arguments!")
        sys.exit(1)