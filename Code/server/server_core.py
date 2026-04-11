import socket
import threading
from config import HOST, PORT, ADMIN_PASS
from server import ban_manager

class ChatServer:
    def __init__(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.clients = {}
        self.lock = threading.Lock()

     def broadcast(self, message, sender_name=None):
        with self.lock:
            for username, client_socket in self.clients.items():
                if username != sender_name:
                    try:
                        client_socket.send(message.encode('utf-8'))
                    except:
                        pass

    def start(self):
        self.server_socket.bind((HOST, PORT))
        self.server_socket.listen(10)
        print(f"Chat server started on {HOST}:{PORT}")

        while True:
            conn, addr = self.server_socket.accept()
            # print(f"New connection from {addr}")
            threading.Thread(target=self.handle_client, args=(conn, addr)).start()
                    
    def process_login(self, conn):
        try:
            username = conn.recv(1024).decode('utf-8').strip()
            if not username: return None

            if ban_manager.is_banned(username):
                conn.send("ERROR: Tài khoản của bạn đã bị cấm!".encode('utf-8'))
                return None
            
            if username == 'admin':
                conn.send("REQ_PASS".encode('utf-8'))
                password = conn.recv(1024).decode('utf-8')
                if password != ADMIN_PASS:
                    conn.send("ERROR: Sai mật khẩu admin!".encode('utf-8'))
                    return None
                
            with self.lock:
                if username in self.clients:
                    conn.send("ERROR: Tên đăng nhập đã tồn tại!".encode('utf-8'))
                    return None
                self.clients[username] = conn

            conn.send("SUCCESS".encode('utf-8'))
            print(f"[+] {username} đã đăng nhập từ {conn.getpeername()}.")
            self.broadcast(f"[SERVER] {username} đã tham gia phòng chat.",username)
            return username
        except:
            return None

    def handle_client(self, conn, addr):
        username = self.process_login(conn)
        if not username: return
        
        while True:
            data = conn.recv(1024)
            if not data: break
            msg = data.decode('utf-8').strip()
            self.process_command(msg, username, conn)

    def process_command(self, msg, sender, conn):
        if msg == "/list":
            with self.lock: users = ", ".join(self.clients.keys())
            conn.send(f"[SERVER] Online: {users}".encode('utf-8'))
            
        elif msg.startswith("/msg "):
            parts = msg.split(' ', 2)
            if len(parts) == 3:
                target, content = parts[1], parts[2]
                with self.lock:
                    if target in self.clients:
                        self.clients[target].send(f"\n[From {sender}]: {content}".encode('utf-8'))

        elif msg.startswith("/all "):
            parts = msg.split(' ', 1)
            if len(parts) == 2 and parts[1].strip():
                content = parts[1]
                with self.lock:
                    for user, sock in list(self.clients.items()):
                        if user != sender:
                            sock.send(f"\n[{sender}]: {content}".encode('utf-8'))
