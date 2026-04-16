import socket, threading, os
from config import HOST, PORT
from client.ui_helpers import print_help_menu, print_incoming_message, print_menu

class ChatClient:
    def __init__(self):
        self.client_socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.is_running = True
        self.username = None

    def reconnect(self):
        try:
            self.client_socket.close()
        except:
            pass
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.connect((HOST, PORT))
            return True
        except:
            print("[!] Không thể kết nối lại đến server")
            return False

    def handle_login(self):
        while self.is_running:
            try:
                username = input("Tên đăng nhập: ")
                if not username: 
                    continue

                self.client_socket.send("LOGIN".encode('utf-8'))
                self.client_socket.send(username.encode('utf-8'))
                response = self.client_socket.recv(1024).decode('utf-8')

                if response == "REQ_PASS":
                    password = input("Mật khẩu: ")
                    self.client_socket.send(password.encode('utf-8'))
                    response = self.client_socket.recv(1024).decode('utf-8')

                if response == "SUCCESS":
                   self.username = username
                   print("\nĐăng nhập thành công!")
                   return True
                else:
                    print(f"[SERVER] {response}\n")
                    return False
            except Exception as e:
                print(f"[!] Mất kết nối với máy chủ, đang kết nối lại...")
                self.reconnect()
                return False
    
    def handle_register(self):
        while self.is_running:
            username = input("Tên đăng nhập: ")
            if not username:
                continue

            try:
                self.client_socket.send("REGISTER".encode('utf-8'))
                self.client_socket.send(username.encode('utf-8'))
                response = self.client_socket.recv(1024).decode('utf-8')

                if response == "USERNAME_OK":
                    password = input("Mật khẩu: ")
                    self.client_socket.send(password.encode('utf-8'))
                    response = self.client_socket.recv(1024).decode('utf-8')

                    if response == "SUCCESS":
                        print("\nĐăng ký thành công! Bạn có thể đăng nhập ngay bây giờ.")
                        return True
                    else:
                        print(f"[SERVER] {response}\n")
                        return False
                else:
                    print(f"[SERVER] {response}\n")
                    return False
            except Exception as e:
                print(f"[!] Mất kết nối với máy chủ, đang kết nối lại...")
                self.reconnect()
                return False

    def login(self):
        while self.is_running:
            print_menu()
            choice = input("Chọn tùy chọn (1-3): ").strip()
            if choice == "LOGIN" or choice == "1":
                if self.handle_login():
                    return True
            elif choice == "REGISTER" or choice == "2":
                if self.handle_register():
                    continue
            elif choice == "QUIT" or choice == "3":
                return False
            else:
                print("[!] Tùy chọn không hợp lệ, vui lòng thử lại.")

    def receive_messages(self):
        while self.is_running:
            try:
                msg = self.client_socket.recv(1024).decode('utf-8')
                if not msg: break
                print_incoming_message(msg)
            except: break

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
                    cmd = input("\r>> ")
                    if cmd == "/quit": break
                    self.client_socket.send(cmd.encode('utf-8'))
                except (KeyboardInterrupt, EOFError):
                    break
        self.is_running = False
        print("\nNgắt kết nối với server.")
        os._exit(0)
