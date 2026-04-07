import socket
import threading
from config import HOST, PORT

class ChatServer:
    def __init__(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.clients = {}
        self.lock = threading.Lock()

    def start(self):
        self.server_socket.bind((HOST, PORT))
        self.server_socket.listen(10)
        print(f"Chat server started on {HOST}:{PORT}")

        while True:
            conn, addr = self.server_socket.accept()
            # print(f"New connection from {addr}")
            threading.Thread(target=self.handle_client, args=(conn, addr)).start()

    def process_login(self, conn):
        data = conn.recv(1024)
        if not data:
            return None
        username = data.decode().strip()
        
        with self.lock:
            if username in self.clients:
                conn.send("Username already taken!".encode('utf-8'))
                return None
            self.clients[username] = conn
        conn.send("SUCCESS".encode('utf-8'))
        print(f"[+]{username} logged in")
        return username

    def handle_client(self, conn, addr):
        username = self.process_login(conn)
        if not username:
            conn.close()