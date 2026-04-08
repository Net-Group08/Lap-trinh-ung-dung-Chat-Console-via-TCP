# Chat Console via TCP

Một ứng dụng chat sử dụng giao thức TCP, cho phép nhiều người dùng trò chuyện với nhau thông qua kết nối mạng.

## Mục Lục

- [Tính Năng](#tính-năng)
- [Yêu Cầu Hệ Thống](#yêu-cầu-hệ-thống)
- [Cài Đặt](#cài-đặt)
- [Cấu Trúc Dự Án](#cấu-trúc-dự-án)
- [Hướng Dẫn Sử Dụng](#hướng-dẫn-sử-dụng)
- [Các Lệnh Hỗ Trợ](#các-lệnh-hỗ-trợ)
- [Cấu Hình](#cấu-hình)

## Tính Năng

### Tính Năng Chung
- Kết nối TCP giữa client và server
- Authentication/Đăng nhập người dùng
- Chat công khai và chat riêng
- Xem danh sách người dùng online
- Hỗ trợ nhiều client kết nối đồng thời

### Tính Năng Admin
- Đăng nhập Admin với mật khẩu bảo vệ
- Kick người dùng khỏi phòng chat
- Ban (cấm) người dùng vĩnh viễn
- Quản lý danh sách ban qua file `bans.txt`

## Yêu Cầu Hệ Thống

- **Python**: 3.6 trở lên
- **Socket**: Module socket chuẩn của Python
- **Threading**: Module threading chuẩn của Python

## Cài Đặt

### 1. Clone hoặc tải dự án
```bash
git clone https://github.com/Net-Group08/Lap-trinh-ung-dung-Chat-Console-via-TCP.git
```

### 2. Kiểm tra Python version
```bash
python --version
```

### 3. Không cần cài đặt dependencies bổ sung
Dự án sử dụng các module chuẩn của Python.

## Cấu Trúc Dự Án

```
Chat-tcp/
├── README.md                 # Tệp này - Hướng dẫn dự án
├── config.py                 # File cấu hình chung
├── bans.txt                  # Danh sách người dùng bị cấm
├── start_server.py           # Điểm vào của server
├── start_client.py           # Điểm vào của client
│
├── server/                   # Thư mục server
│   ├── __init__.py
│   ├── server_core.py        # Logic xử lý server chính
│   └── ban_manager.py        # Quản lý hệ thống ban
│
└── client/                   # Thư mục client
    ├── __init__.py
    ├── client_core.py        # Logic xử lý client chính
    └── ui_helpers.py         # Công cụ hỗ trợ giao diện
```

## Hướng Dẫn Sử Dụng

### Khởi Động Server

Trong terminal/command prompt, chạy:
```bash
python start_server.py
```

Kết quả:
```
[*] Server đang chạy tại 127.0.0.1:5555
[+] Có kết nối TCP từ ('127.0.0.1', 12345)
[+] username đã đăng nhập từ ('127.0.0.1', 12345).
```

### Khởi Động Client

Mở một terminal khác, chạy:
```bash
python start_client.py
```

Bạn sẽ được yêu cầu nhập username:
```
Nhập username: john
[SERVER] john đã tham gia phòng chat.
Đăng nhập thành công!

--- CÁC LỆNH HỖ TRỢ ---
/list          - Xem danh sách người dùng online
/msg <tên> <nd> - Gửi tin nhắn riêng cho một người
/all <nd>      - Gửi tin nhắn cho tất cả mọi người
/quit          - Thoát chương trình
```

### Đăng Nhập Với Quyền Admin

Nhập username là `admin`:
```
Nhập username: admin
Nhập mật khẩu admin: adminpass
Đăng nhập thành công!

--- CÁC LỆNH HỖ TRỢ ---
/list          - Xem danh sách người dùng online
/msg <tên> <nd> - Gửi tin nhắn riêng cho một người
/all <nd>      - Gửi tin nhắn cho tất cả mọi người
/quit          - Thoát chương trình

--- Lệnh Admin ---
/kick <tên>    - Đuổi một người dùng khỏi phòng chat
/ban <tên>     - Cấm một người dùng vĩnh viễn
```

## Các Lệnh Hỗ Trợ

| Lệnh | Cú Pháp | Mô Tả |
|------|---------|-------|
| List | `/list` | Xem danh sách tất cả người dùng đang online |
| Private Message | `/msg <tên_người_dùng> <nội_dung>` | Gửi tin nhắn riêng cho một người cụ thể |
| Public Message | `/all <nội_dung>` | Gửi tin nhắn tới tất cả mọi người |
| Quit | `/quit` | Thoát khỏi ứng dụng chat |
| **Kick** (Admin) | `/kick <tên_người_dùng>` | Đuổi một người dùng khỏi phòng chat |
| **Ban** (Admin) | `/ban <tên_người_dùng>` | Cấm một người dùng vĩnh viễn |

### Ví Dụ Sử Dụng

```
>> /list
[SERVER] Online: john, alice, bob, admin

>> /msg alice Hello, how are you?
[SERVER] Tin nhắn đã gửi.

>> /all Everyone, let's start!
[Tin nhắn riêng từ john]: Everyone, let's start! (gửi đến: alice, bob)

>> /kick john
[ADMIN] Đã kick john.

>> /ban john
[ADMIN] Đã cấm vĩnh viễn john.
```

## Cấu Hình

Chỉnh sửa file `config.py` để thay đổi cài đặt:

```python
# Cấu hình địa chỉ mạng
HOST = '127.0.0.1'  # Địa chỉ IP của Server (localhost)
PORT = 5555         # Cổng mà Server sẽ lắng nghe

# Cấu hình Admin
ADMIN_PASS = 'adminpass'  # Mật khẩu để đăng nhập với quyền admin

# Cấu hình file
BANS_FILE = 'bans.txt'    # Tên file lưu danh sách người dùng bị cấm
```

### Thay Đổi Cổng Server

Mở `config.py` và thay đổi giá trị `PORT`:
```python
PORT = 8888  # Hoặc cổng khác
```

### Mô Tả Chi Tiết

- **config.py**: File cấu hình tập trung, chứa HOST, PORT, mật khẩu admin, tên file ban
- **server_core.py**: 
  - Lớp `ChatServer`: Quản lý server, các client kết nối, xử lý lệnh
  - Hỗ trợ broadcast, private message, kick, ban
  - Thread-safe sử dụng locks
  
- **client_core.py**:
  - Lớp `ChatClient`: Quản lý kết nối client
  - Xử lý login, nhận tin nhắn, gửi lệnh
  - Sử dụng threading để nhận tin nhắn không chặn
  
- **ban_manager.py**: Quản lý hệ thống ban
  - Kiểm tra xem user có bị cấm không
  - Thêm user vào danh sách cấm
  - Đảm bảo file `bans.txt` luôn tồn tại
  
- **ui_helpers.py**: 
  - In menu lệnh
  - In tin nhắn đến mà không xáo trộn dòng input

## Bảo Mật

- Mật khẩu admin được lưu trong `config.py` (xem xét lưu vào environment variable)
- Danh sách ban được lưu trong file `bans.txt` (dễ dàng quản lý)
- Sử dụng threading locks để bảo vệ dữ liệu khi có nhiều client truy cập đồng thời

## Xử Lý Lỗi

### Lỗi Kết Nối

```
[!] Lỗi kết nối. Server chưa được bật hoặc sai địa chỉ.
```
**Giải pháp**: Đảm bảo server đã được khởi động và cấu hình HOST/PORT đúng.

### Tên Đăng Nhập Đã Tồn Tại

```
ERROR: Tên đăng nhập đã tồn tại!
```
**Giải pháp**: Sử dụng tên đăng nhập khác.

### Tài Khoản Bị Cấm

```
ERROR: Tài khoản của bạn đã bị cấm!
```
**Giải pháp**: Yêu cầu admin gỡ bỏ ban (xóa username khỏi `bans.txt`).

### Sai Mật Khẩu Admin

```
ERROR: Sai mật khẩu admin!
```
**Giải pháp**: Kiểm tra lại mật khẩu admin în `config.py`.
