import socket
import threading
from config import HOST, PORT

class ChatClient:
    def __init__(self):
        self.client_socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self):
        try:
            self.client_socket.connect((HOST, PORT))
            print(f"Connected to chat server at {HOST}:{PORT}")
        except:
            print(f"Failed to connect to chat server at {HOST}:{PORT}")
            return