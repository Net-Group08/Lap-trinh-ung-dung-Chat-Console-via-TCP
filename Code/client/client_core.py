import socket, threading, os
from config import HOST, PORT
from client.ui_helpers import print_help_menu, print_incoming_message, print_menu

class ChatClient:
    def __init__(self):
        self.client_socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.is_running = True
        self.username = None

    def show_auth_menu(self):
        while True:
            print_menu()            
            choice = input("Chọn tùy chọn (1-3): ").strip()
            if choice == "1":
                return "LOGIN"
            elif choice == "2":
                return "REGISTER"
            elif choice == "3":
                return "QUIT"
            else:
                print("[!] Tùy chọn không hợp lệ, vui lòng thử lại.")

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
                    print(f"[SERVER] {response}")
                    print("Vui lòng thử lại.\n")
                    return False
            except Exception as e:
                print(f"[!] Lỗi kết nối: {e}")
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
                        print("\nĐăng ký thành công! Vui lòng kết nối lại để đăng nhập.")
                        self.client_socket.close()
                        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.client_socket.connect((HOST, PORT))
                        return True
                    else:
                        print(f"[SERVER] {response}")
                        print("Vui lòng thử lại.\n")
                        return False
                else:
                    print(f"[SERVER] {response}")
                    print("Vui lòng thử lại.\n")
                    return False
            except Exception as e:
                print(f"[!] Lỗi: {e}")
                try:
                    self.client_socket.close()
                except:
                    pass
                self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    self.client_socket.connect((HOST, PORT))
                except:
                    print("[!] Không thể kết nối lại đến server")
                    return False
                return False

    def login(self):
        while self.is_running:
            choice = self.show_auth_menu()
            
            if choice == "LOGIN":
                if self.handle_login():
                    return True
            elif choice == "REGISTER":
                if self.handle_register():
                    continue
            elif choice == "QUIT":
                return False

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
                    cmd = input("\r>> ")
                    if cmd == "/quit": break
                    self.client_socket.send(cmd.encode('utf-8'))
                except (KeyboardInterrupt, EOFError):
                    break
        self.is_running = False
        self.client_socket.close();
        print("\nDisconnected from server.")
        os._exit(0)
