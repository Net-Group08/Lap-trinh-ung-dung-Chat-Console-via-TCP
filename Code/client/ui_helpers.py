import sys
import msvcrt

def masked_input(prompt="Mật khẩu: "):
    """Nhập mật khẩu, mỗi ký tự hiển thị dấu *. Hỗ trợ Backspace."""
    sys.stdout.write(prompt)
    sys.stdout.flush()
    password = []
    while True:
        ch = msvcrt.getwch()
        if ch in ('\r', '\n'):  # Enter
            sys.stdout.write('\n')
            sys.stdout.flush()
            return ''.join(password)
        elif ch == '\x08':  # Backspace
            if password:
                password.pop()
                sys.stdout.write('\b \b')
                sys.stdout.flush()
        elif ch == '\x03':  # Ctrl+C
            raise KeyboardInterrupt
        else:
            password.append(ch)
            sys.stdout.write('*')
            sys.stdout.flush()

def print_help_menu(is_admin=False):
    """In ra menu các lệnh có thể sử dụng."""
    print("\n--- CÁC LỆNH HỖ TRỢ ---")
    print("/list          - Xem danh sách người dùng online")
    print("/msg <tên> <nd> - Gửi tin nhắn riêng cho một người")
    print("/all <nd>      - Gửi tin nhắn cho tất cả mọi người")
    print("/quit          - Thoát chương trình")
    print("-----------------------\n")
    if is_admin:
        print("--- LỆNH ADMIN ---")
        print("/kick <tên>    - Kick một người dùng")
        print("/ban <tên>     - Cấm một người dùng vĩnh viễn")
        print("/unban <tên>   - Bỏ cấm một người dùng")
        print("------------------\n")

def print_menu():
    print("\n--- MENU ---")
    print("1. Đăng nhập")
    print("2. Đăng ký")
    print("3. Thoát")
    print("-------------\n")

def print_incoming_message(msg):
    print(f"\r{msg}\n>> ", end="", flush=True)