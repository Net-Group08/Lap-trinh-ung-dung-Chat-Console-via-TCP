import socket
import threading
from config import HOST, PORT

class ChatServer:
    def __init__(self):
        self.server_socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR ,1)

    def start(self):
        self.server_socket.bind((HOST,PORT))
        self.server_socket.listen(10)
        print(f"Chat server started on {HOST}:{PORT}")

        while True:
            conn, addr = self.server_socket.accept()
            print(f"New connection from {addr}")