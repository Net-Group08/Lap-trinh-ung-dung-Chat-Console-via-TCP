import socket
import threading
from config import HOST, PORT, ADMIN_PASS
from server  import ban_manager

class ChatServer:
    def __init__(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.clients = {}
        self.lock = threading.Lock()
    
    def broadcast(self, message, sender_name=None):

        with self.lock:
            for usename, client_socket in self.clients.items():
                if usename != sender_name:
                    try:
                        client_socket.send(message.encode('utf-8'))
                    except:
                        pass # Bỏ qua nếu client đã ngắt kết nối


    def process_login(self, conn):
        try:
            username = conn.recv(1024).decode('utf-8').strip()
            if not username: return None

            if ban_manager.is_banned(username):
                conn.send("ERROR: Tài khoản của bạn đã bị cấm!".encode('utf-8'))
                return None
            
            if username == 'admin':
                conn.send("REQ_PASS".encode('utf-8'))
                admin_pass = conn.recv(1024).decode('utf-8').strip()
                if admin_pass != ADMIN_PASS:
                    conn.send("ERROR: Sai mật khẩu admin!".encode('utf-8'))
                    return None
         
            with self.lock:
                if username in self.clients:
                    conn.send("ERROR: Tên đăng nhập đã tồn tại!".encode('utf-8'))
                    return None
                self.clients[username] = conn

            conn.send("SUCCESS".encode('utf-8'))
            print(f"[+] {username} đã đăng nhập từ {conn.getpeername()}.")
            self.broadcast(f"[server] {username} đã tham gia phòng chat.", username)
            return username
        except:
            return None
        
    def process_command(self, msg, sender, conn):
        if msg == "/list":
            with self.lock: users = ", ".join(self.clients.keys())
            conn.send(f"[SERVER] Online: {users}".encode('utf-8'))
        elif msg.startswith("/msg "):
            parts = msg.split(' ', 2)
            if len(parts) < 3: return conn.send("[SERVER] Lỗi: /msg <tên> <nội dung>".encode('utf-8'))
            target, content = parts[1], parts[2]
            with self.lock:
                if target in self.clients:
                    self.clients[target].send(f"[Tin nhắn riêng từ {sender}]: {content}".encode('utf-8'))
                else: conn.send(f"[SERVER] Người dùng '{target}' không tồn tại.".encode('utf-8'))
        elif msg.startswith("/all "):
            parts = msg.split(' ', 1)
            if len(parts) < 2 or not parts[1].strip(): return conn.send("[SERVER] Lỗi: /all <nội dung>".encode('utf-8'))
            content = parts[1]
            self.broadcast(f"[{sender} -> all]: {content}", sender)
        elif msg.startswith("/kick ") and sender == 'admin':
            target = msg.split(' ', 1)[1]
            with self.lock:
                if target in self.clients and target != 'admin':
                    self.clients[target].send("[SERVER] Bạn đã bị admin kick!".encode('utf-8'))
                    self.clients[target].close()
                    conn.send(f"[ADMIN] Đã kick {target}.".encode('utf-8'))
                else: conn.send(f"[ADMIN] Không tìm thấy hoặc không thể kick '{target}'.".encode('utf-8'))
        elif msg.startswith("/ban ") and sender == 'admin':
            target = msg.split(' ', 1)[1]
            if target != 'admin':
                ban_manager.ban_user(target)
                conn.send(f"[ADMIN] Đã cấm vĩnh viễn {target}.".encode('utf-8'))
                with self.lock:
                    if target in self.clients:
                        self.clients[target].send("[SERVER] Bạn đã bị admin cấm vĩnh viễn!".encode('utf-8'))
                        self.clients[target].close()
            else: conn.send("[ADMIN] Không thể tự cấm chính mình.".encode('utf-8'))
        else:
            conn.send("[SERVER] Lệnh không hợp lệ hoặc bạn không có quyền.".encode('utf-8'))

    def handle_client(self, conn, addr):
        print(f"[+] Có kết nối TCP từ {addr}")
        username = None
        try:
            username = self.process_login(conn)
            if not username: return
            
            while True:
                data = conn.recv(1024)
                if not data: break
                msg = data.decode('utf-8').strip()
                if msg: self.process_command(msg, username, conn)
        except (ConnectionResetError, BrokenPipeError):
            print(f"[!] Kết nối với {username if username else addr} bị ngắt đột ngột.")
        finally:
            if username:
                with self.lock:
                    if username in self.clients:
                        del self.clients[username]
                        print(f"[-] {username} đã ngắt kết nối.")
                        self.broadcast(f"[SERVER] {username} đã rời khỏi phòng chat.")
            conn.close()

    def start(self):
        ban_manager.ensure_ban_file_exists()
        self.server_socket.bind((HOST, PORT))
        self.server_socket.listen(10)
        print(f"[*] Server đang chạy tại {HOST}:{PORT}")
        while True:
            conn, addr = self.server_socket.accept()
            threading.Thread(target=self.handle_client, args=(conn, addr)).start()