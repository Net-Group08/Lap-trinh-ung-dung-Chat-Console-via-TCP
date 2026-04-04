import socket
import sys
import threading
from config import HOST, PORT

class ChatClient:
    def __init__(self):
        self.client_socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.is_running = True

    def login(self):
        while self.is_running:
            username = input("Enter your username: ")
            self.client_socket.sendall(username.encode('utf-8'))
            if self.client_socket.recv(1024).decode() == "SUCCESS":
                print("Login successful")
                return True

    def start(self):
        try:
            self.client_socket.connect((HOST, PORT))
            print(f"Connected to chat server at {HOST}:{PORT}")
        except:
            print(f"Failed to connect to chat server at {HOST}:{PORT}")
            return sys.exit(0)
        self.login()