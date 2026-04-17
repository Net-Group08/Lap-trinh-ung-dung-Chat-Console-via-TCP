import socket
import threading
from config import HOST, PORT, ADMIN_PASS
from server import ban_manager
from server import user_service

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

    def handle_client(self, conn, addr):
        # print(f"[+] Có kết nối TCP từ {addr}")
        username = None
        req_type = None
        try:
            while not req_type:
                req_type = self.process_login(conn)
                if req_type == "DISCONNECT":
                    return
            username = req_type
            # print(f"[+] {username}")
            while True:
                data = conn.recv(1024)
                if not data: break
                msg = data.decode('utf-8').strip()
                if msg: self.process_command(msg, username, conn)
        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
            print(f"[!] Ngắt kết nối với {username if username else addr}.")
        except Exception as e:
            print(f"[!] Lỗi trong handle_client: {e}")
        finally:
            if username:
                with self.lock:
                    if username in self.clients:
                        del self.clients[username]
                        print(f"[-] {username} đã ngắt kết nối.")
                self.broadcast(f"[SERVER] {username} đã rời khỏi phòng chat.")
            conn.close()

    def handle_registration(self, conn):
        try:
            username = conn.recv(1024).decode('utf-8').strip()
            if not username:
                return "DISCONNECT"
            
            with self.lock:
                if user_service.check_user_exists(username):
                    conn.send("ERROR: Tên đăng nhập đã tồn tại!".encode('utf-8'))
                    return None

            if ban_manager.is_banned(username):
                conn.send("ERROR: Tài khoản này đã bị cấm!".encode('utf-8'))
                return None

            if username == 'admin':
                conn.send("ERROR: Không thể đăng ký với tên 'admin'!".encode('utf-8'))
                return None

            conn.send("USERNAME_OK".encode('utf-8'))
            
            password = conn.recv(1024).decode('utf-8').strip()
            if not password:
                return "DISCONNECT"

            success, message = user_service.register_user(username, password)
            
            if success:
                conn.send("SUCCESS".encode('utf-8'))
                return None
            else:
                conn.send(f"ERROR: {message}".encode('utf-8'))
                return None
        except Exception as e:
            print(f"[!] Lỗi trong quá trình đăng ký: {e}")
            try:
                conn.send("ERROR: Đã xảy ra lỗi trong quá trình đăng ký!".encode('utf-8'))
            except: pass
            return "DISCONNECT"
        
    def handle_login(self, conn):
        try:
            username = conn.recv(1024).decode('utf-8').strip()
            if not username:
                return "DISCONNECT"
            
            with self.lock:
                if self.clients.get(username):
                    conn.send("ERROR: Tên đăng nhập đã tồn tại!".encode('utf-8'))
                    return None

            if ban_manager.is_banned(username):
                conn.send("ERROR: Tài khoản của bạn đã bị cấm!".encode('utf-8'))
                return None
            
            if username == 'admin':
                conn.send("REQ_PASS".encode('utf-8'))
                password = conn.recv(1024).decode('utf-8')
                if not password:
                    return "DISCONNECT"
                if password != ADMIN_PASS:
                    conn.send("ERROR: Sai mật khẩu admin!".encode('utf-8'))
                    return None
            else:
                conn.send("REQ_PASS".encode('utf-8'))
                password = conn.recv(1024).decode('utf-8').strip()
                if not password:
                    return "DISCONNECT"

                success, message = user_service.login_user(username, password)
                if not success:
                    conn.send(f"ERROR: {message}".encode('utf-8'))
                    return None

            with self.lock:
                if username in self.clients:
                    conn.send("ERROR: Tên đăng nhập đã tồn tại!".encode('utf-8'))
                    return None
                self.clients[username] = conn

            conn.send("SUCCESS".encode('utf-8'))
            print(f"[+] {username} đã đăng nhập từ {conn.getpeername()}.")
            self.broadcast(f"[SERVER] {username} đã tham gia phòng chat.", username)
            return username
        except Exception as e:
            print(f"[!] Lỗi trong quá trình đăng nhập: {e}")
            try:
                conn.send("ERROR: Đã xảy ra lỗi trong quá trình đăng nhập!".encode('utf-8'))
            except: pass
            return "DISCONNECT"
                    
    def process_login(self, conn):
        try:
            request_type = conn.recv(1024).decode('utf-8').strip()
            if not request_type:
                return "DISCONNECT"
            
            if request_type == "REGISTER":
                return self.handle_registration(conn)
            elif request_type == "LOGIN":
                return self.handle_login(conn)
            else:
                conn.send("ERROR: Loại yêu cầu không hợp lệ!".encode('utf-8'))
                return None
        except:
            return "DISCONNECT"

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
                self.broadcast(f"\n[{sender}]: {content}", sender_name=sender)
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
        elif msg.startswith("/unban ") and sender == 'admin':
            target = msg.split(' ', 1)[1]
            ban_manager.unban_user(target)
            conn.send(f"[ADMIN] Đã bỏ cấm {target}.".encode('utf-8'))
        else:
            conn.send("[SERVER] Lệnh không hợp lệ hoặc bạn không có quyền.".encode('utf-8'))

    def start(self):
        self.server_socket.bind((HOST, PORT))
        self.server_socket.listen(100)
        print(f"[*] Chat server started on {HOST}:{PORT}")

        while True:
            try:
                conn, addr = self.server_socket.accept()
                threading.Thread(target=self.handle_client, args=(conn, addr)).start()
            except OSError:
                break
