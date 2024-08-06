import socket

from settings import BASE_PORT, BUFFER_SIZE, NUM_PLAYERS


class Network:
    sock: socket.socket = {}
    player_port = 8000
    next_player_port = 8001
    player_ip = ""
    next_player_ip = ""

    has_token = 0

    def __init__(self, player_id, player_ip, next_player_ip):
        self.player_port = BASE_PORT + player_id - 1
        self.next_player_port = self.next_port(self.player_port)

        self.player_ip = player_ip
        self.next_player_ip = next_player_ip

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.player_ip, self.player_port))

    def next_port(self, current_port):
        return (current_port + 1 - BASE_PORT) % NUM_PLAYERS + BASE_PORT

    def send_message(self, message):
        if self.has_token:
            self.sock.sendto(
                message.encode(), (self.next_player_ip, self.next_player_port)
            )
            self.has_token = 0
        else:
            print("The player does not have the token to send the message")
            exit(1)

    def receive_message(self):
        self.has_token = 1
        data, _ = self.sock.recvfrom(BUFFER_SIZE)
        decoded = data.decode()
        return decoded
