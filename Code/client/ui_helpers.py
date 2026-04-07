class ConsoleUI:

    def show_message(self, msg: str) -> None:
        print(f"\r{msg}\n>> ", end="", flush=True)

    def show_help(self, is_admin: bool = False) -> None:
        print("\n--- CÁC LỆNH HỖ TRỢ ---")
        print("  /list                  — Xem người online")
        print("  /msg <tên> <nội dung>  — Nhắn riêng")
        print("  /all <nội dung>        — Nhắn tất cả")
        print("  /help                  — Trợ giúp từ server")
        print("  /quit                  — Thoát")
        if is_admin:
            print("  [ADMIN] /kick <tên>    — Kick")
            print("  [ADMIN] /ban  <tên>    — Ban vĩnh viễn")
            print("  [ADMIN] /unban <tên>   — Gỡ ban")
        print("------------------------\n")

    def prompt(self, text: str = ">> ") -> str:
        return input(text).strip()

    def info(self, msg: str) -> None:
        print(f"[*] {msg}")

    def error(self, msg: str) -> None:
        print(f"[!] {msg}")