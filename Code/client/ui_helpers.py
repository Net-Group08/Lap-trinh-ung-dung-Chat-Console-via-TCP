def print_help_menu(is_admin=False):
    """In ra menu các lệnh có thể sử dụng."""
    print("\n--- CÁC LỆNH HỖ TRỢ ---")
    print("/list          - Xem danh sách người dùng online")
    print("/msg <tên> <nd> - Gửi tin nhắn riêng cho một người")
    print("/all <nd>      - Gửi tin nhắn cho tất cả mọi người")
    print("/quit          - Thoát chương trình")
    print("-----------------------\n")


def print_incoming_message(msg):
    print(f"\r{msg}\n>> ", end="", flush=True)