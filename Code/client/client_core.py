import socket, threading, os
from config import HOST, PORT
from client.ui_helpers import print_help_menu, print_incoming_message

class ChatClient:
    def __init__(self):
        self.client_socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.is_running = True
        self.username = None

    def login(self):
        while self.is_running:
            username = input("Input username: ")
            self.client_socket.send(username.encode('utf-8'))
            if self.client_socket.recv(1024).decode('utf-8') == "SUCCESS":
                print("Login successful")
                self.username = username
                return True
            
    def receive_messages(self):
        while self.is_running:
            try:
                msg = self.client_socket.recv(1024).decode('utf-8')
                if not msg: break
                print_incoming_message(msg)
            except: break
        
        print("\n[!] Connection closed by server.")
        self.is_running = False
        os._exit(0)

    def start(self):
        try:
            self.client_socket.connect((HOST, PORT))
        except ConnectionRefusedError:
            print("[!] Failed to connect to the server")
            return

        if self.login():
            print_help_menu(is_admin=(self.username == 'admin'))
            threading.Thread(target=self.receive_messages, daemon=True).start()

            while self.is_running:
                try:
                    cmd = input(">> ")
                    if cmd == "/quit": break
                    self.client_socket.send(cmd.encode('utf-8'))
                except (KeyboardInterrupt, EOFError):
                    break
        self.is_running = False
        self.client_socket.close();
        print("\nDisconnected from server.")
        os._exit(0)