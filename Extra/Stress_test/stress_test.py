#!/usr/bin/env python3
"""
Stress Test Suite — Chat Console via TCP

"""

import socket
import threading
import time
import csv
import random
import string
import sys
import os

# ==================== CẤU HÌNH ====================
HOST = "127.0.0.1"
PORT = 5555
RECV_TIMEOUT = 5.0
STEP_DELAY = 0.3
LOG_FILE = "result.csv"
ADMIN_PASSWORD = "adminpass"

WARNING_AVG_RT_MS = 3000
STOP_AVG_RT_MS = 5000
STOP_ERROR_RATE = 0.30
PASS_AVG_RT_MS = 3000
PASS_ERROR_RATE = 0.10


# ==================== METRICS COLLECTOR ====================
class MetricsCollector:
    """Thu thập số liệu, phát hiện ngưỡng dừng, in báo cáo và ghi CSV."""

    def __init__(self):
        self.lock = threading.Lock()
        self.results = []
        self.stop_flag = False
        self.stop_reason = ""

    def record(self, scenario_name, client_id, status, error_type, response_time_ms):
        """Ghi nhận kết quả của một client."""
        with self.lock:
            self.results.append({
                "scenario": scenario_name,
                "client_id": client_id,
                "status": status,
                "error_type": error_type or "",
                "response_time_ms": round(response_time_ms, 2)
            })
            if not self.stop_flag and len(self.results) >= 5:
                total = len(self.results)
                failures = sum(1 for r in self.results if r["status"] == "FAIL")
                if failures / total > STOP_ERROR_RATE:
                    self.stop_flag = True
                    self.stop_reason = f"Error rate {failures}/{total} ({failures/total*100:.1f}%) > {STOP_ERROR_RATE*100:.0f}%"
                    return
                response_times = [r["response_time_ms"] for r in self.results if r["response_time_ms"] > 0]
                if response_times and sum(response_times) / len(response_times) > STOP_AVG_RT_MS:
                    self.stop_flag = True
                    self.stop_reason = f"Avg RT {sum(response_times)/len(response_times):.0f}ms > {STOP_AVG_RT_MS}ms"

    def report(self, scenario_name):
        """In báo cáo và ghi CSV cho một kịch bản."""
        with self.lock:
            data = list(self.results)
        total = len(data)
        success = sum(1 for r in data if r["status"] == "SUCCESS")
        failure = total - success
        error_percent = failure / total * 100 if total else 0
        response_times = [r["response_time_ms"] for r in data if r["response_time_ms"] > 0]
        average_rt = sum(response_times) / len(response_times) if response_times else 0
        percentile_95 = self._percentile(response_times, 95) if response_times else 0
        max_rt = max(response_times) if response_times else 0

        error_type_counts = {}
        for r in data:
            if r["status"] == "FAIL" and r["error_type"]:
                error_type_counts[r["error_type"]] = error_type_counts.get(r["error_type"], 0) + 1

        if error_percent <= PASS_ERROR_RATE * 100 and average_rt <= PASS_AVG_RT_MS:
            verdict = "✅ PASS"
        elif average_rt > WARNING_AVG_RT_MS or error_percent > PASS_ERROR_RATE * 100:
            verdict = "⚠️  WARN"
        else:
            verdict = "✅ PASS"

        if self.stop_flag:
            verdict = "🛑 STOPPED"

        print(f"\n{'═'*60}")
        print(f"  KẾT QUẢ: {scenario_name}  [{verdict}]")
        print(f"{'═'*60}")
        print(f"  Tổng client       : {total}")
        print(f"  Thành công        : {success}")
        print(f"  Thất bại          : {failure}")
        print(f"  Tỉ lệ lỗi        : {error_percent:.1f}%")
        print(f"  Response time AVG : {average_rt:.1f} ms")
        print(f"  Response time P95 : {percentile_95:.1f} ms")
        print(f"  Response time MAX : {max_rt:.1f} ms")
        if error_type_counts:
            print("  Phân loại lỗi:")
            for error_type, count in sorted(error_type_counts.items(), key=lambda x: -x[1]):
                print(f"    {error_type:25s} : {count}")
        if self.stop_flag:
            print(f"  🛑 DỪNG KỊCH BẢN: {self.stop_reason}")
        print(f"{'═'*60}\n")
        self._write_csv(data)

    @staticmethod
    def _percentile(data, percentile):
        """Tính percentile thủ công."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * percentile / 100.0
        f = int(k)
        c = min(f + 1, len(sorted_data) - 1)
        return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])

    def _write_csv(self, data):
        """Ghi kết quả vào file CSV."""
        try:
            is_new_file = not os.path.exists(LOG_FILE) or os.path.getsize(LOG_FILE) == 0
            with open(LOG_FILE, "a", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=["scenario", "client_id", "status", "error_type", "response_time_ms"])
                if is_new_file:
                    writer.writeheader()
                writer.writerows(data)
        except Exception as error:
            print(f"  ✗ Lỗi ghi CSV: {error}")


# ==================== CÁC HÀM TIỆN ÍCH ====================
def generate_random_string(length=8):
    """Tạo chuỗi ngẫu nhiên gồm chữ thường và số."""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def generate_strong_password():
    """Tạo mật khẩu mạnh đáp ứng yêu cầu: chữ hoa, chữ thường, số, ký tự đặc biệt."""
    uppercase = random.choice(string.ascii_uppercase)
    lowercase = random.choice(string.ascii_lowercase)
    digit = random.choice(string.digits)
    special = random.choice("!@#$%^&*()-_=+[]{}|;:,.<>?/")
    remaining = ''.join(random.choices(string.ascii_letters + string.digits + "!@#$%^&*", k=8))
    password_list = list(uppercase + lowercase + digit + special + remaining)
    random.shuffle(password_list)
    return ''.join(password_list)

def connect_to_server(timeout=RECV_TIMEOUT):
    """Tạo socket, kết nối đến server. Trả về (socket, thời gian kết nối_ms, lỗi hoặc None)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    start_time = time.time()
    try:
        sock.connect((HOST, PORT))
        elapsed_ms = (time.time() - start_time) * 1000
        return sock, elapsed_ms, None
    except socket.timeout:
        elapsed_ms = (time.time() - start_time) * 1000
        return None, elapsed_ms, "timeout"
    except ConnectionRefusedError:
        elapsed_ms = (time.time() - start_time) * 1000
        return None, elapsed_ms, "connection_refused"
    except Exception:
        elapsed_ms = (time.time() - start_time) * 1000
        return None, elapsed_ms, "connection_refused"

def send_message(sock, message):
    """Gửi message qua socket. Trả về True nếu thành công."""
    try:
        sock.sendall(message.encode("utf-8"))
        return True
    except Exception:
        return False

def receive_message(sock, buffer_size=4096):
    """Nhận message từ socket. Trả về chuỗi, None nếu đóng, '__TIMEOUT__' nếu timeout."""
    try:
        data = sock.recv(buffer_size)
        if not data:
            return None
        return data.decode("utf-8")
    except socket.timeout:
        return "__TIMEOUT__"
    except Exception:
        return None

def classify_error(response):
    """Phân loại lỗi từ response nhận được."""
    if response is None:
        return "unexpected_close"
    if response == "__TIMEOUT__":
        return "timeout"
    if isinstance(response, str) and response.startswith("ERROR"):
        return "auth_error"
    return "unexpected_close"

def perform_login_flow(sock, username, password):
    """Thực hiện đăng nhập theo đúng giao thức server."""
    start_time = time.time()
    if not send_message(sock, "LOGIN"):
        return False, (time.time() - start_time) * 1000, "unexpected_close"
    time.sleep(STEP_DELAY)
    if not send_message(sock, username):
        return False, (time.time() - start_time) * 1000, "unexpected_close"
    response = receive_message(sock)
    if response in (None, "__TIMEOUT__"):
        return False, (time.time() - start_time) * 1000, classify_error(response)
    if response != "REQ_PASS":
        return False, (time.time() - start_time) * 1000, "auth_error"
    time.sleep(STEP_DELAY)
    if not send_message(sock, password):
        return False, (time.time() - start_time) * 1000, "unexpected_close"
    response = receive_message(sock)
    if response == "SUCCESS":
        return True, (time.time() - start_time) * 1000, None
    return False, (time.time() - start_time) * 1000, "auth_error"

def perform_register_flow(sock, username, password):
    """Thực hiện đăng ký theo đúng giao thức server."""
    start_time = time.time()
    if not send_message(sock, "REGISTER"):
        return False, (time.time() - start_time) * 1000, "unexpected_close"
    time.sleep(STEP_DELAY)
    if not send_message(sock, username):
        return False, (time.time() - start_time) * 1000, "unexpected_close"
    response = receive_message(sock)
    if response in (None, "__TIMEOUT__"):
        return False, (time.time() - start_time) * 1000, classify_error(response)
    if response != "USERNAME_OK":
        return False, (time.time() - start_time) * 1000, "auth_error"
    time.sleep(STEP_DELAY)
    if not send_message(sock, password):
        return False, (time.time() - start_time) * 1000, "unexpected_close"
    response = receive_message(sock)
    if response == "SUCCESS":
        return True, (time.time() - start_time) * 1000, None
    return False, (time.time() - start_time) * 1000, "auth_error"

def register_and_login(username, password, scenario_name, client_id, metrics):
    """Đăng ký (bằng kết nối riêng) và đăng nhập (kết nối mới). Trả về (socket, total_time_ms)."""
    register_sock, connect_time, error = connect_to_server()
    if error:
        metrics.record(scenario_name, client_id, "FAIL", error, connect_time)
        return None, 0
    ok, register_time, register_error = perform_register_flow(register_sock, username, password)
    register_sock.close()
    if not ok:
        metrics.record(scenario_name, client_id, "FAIL", register_error or "auth_error", register_time)
        return None, 0
    time.sleep(STEP_DELAY)
    login_sock, connect_time2, error = connect_to_server()
    if error:
        metrics.record(scenario_name, client_id, "FAIL", error, connect_time2)
        return None, 0
    ok, login_time, login_error = perform_login_flow(login_sock, username, password)
    if not ok:
        metrics.record(scenario_name, client_id, "FAIL", login_error or "auth_error", login_time)
        login_sock.close()
        return None, 0
    total_time = connect_time + register_time + connect_time2 + login_time
    return login_sock, total_time

def safe_close_socket(sock):
    """Đóng socket an toàn."""
    if sock:
        try:
            sock.close()
        except Exception:
            pass


# ==================== CÁC KỊCH BẢN ====================
def scenario_s1_baseline(number_of_clients, metrics=None):
    """[S1] Baseline load: đăng ký, đăng nhập, gửi /all, /quit."""
    if metrics is None:
        metrics = MetricsCollector()
    scenario_name = f"S1_baseline_{number_of_clients}c"
    threads = []

    def worker(client_id):
        if metrics.stop_flag:
            return
        username = f"s1_u{client_id}_{generate_random_string(4)}"
        password = generate_strong_password()
        register_sock, _, error = connect_to_server()
        if error:
            metrics.record(scenario_name, client_id, "FAIL", error, 0)
            return
        ok, register_time, register_error = perform_register_flow(register_sock, username, password)
        register_sock.close()
        if not ok:
            metrics.record(scenario_name, client_id, "FAIL", register_error or "auth_error", register_time)
            return
        time.sleep(STEP_DELAY)
        login_sock, _, error = connect_to_server()
        if error:
            metrics.record(scenario_name, client_id, "FAIL", error, 0)
            return
        ok, login_time, login_error = perform_login_flow(login_sock, username, password)
        if ok:
            send_message(login_sock, "/all hello from stress test")
            time.sleep(STEP_DELAY)
            send_message(login_sock, "/quit")
            metrics.record(scenario_name, client_id, "SUCCESS", None, login_time)
        else:
            metrics.record(scenario_name, client_id, "FAIL", login_error or "auth_error", login_time)
        login_sock.close()

    for i in range(number_of_clients):
        if metrics.stop_flag:
            break
        thread = threading.Thread(target=worker, args=(i,), daemon=True)
        threads.append(thread)
        thread.start()
        time.sleep(0.1)

    for thread in threads:
        thread.join(timeout=RECV_TIMEOUT * 4 + 10)

    metrics.report(scenario_name)
    return metrics

def scenario_s2_register_flood(number_of_clients=30, metrics=None):
    """[S2] Register flood: nhiều client đăng ký đồng thời."""
    if metrics is None:
        metrics = MetricsCollector()
    scenario_name = "S2_register_flood"
    threads = []
    start_event = threading.Event()

    def worker(client_id):
        start_event.wait()
        if metrics.stop_flag:
            return
        username = f"s2_rf_{client_id}_{generate_random_string(6)}"
        password = generate_strong_password()
        sock, connect_time, error = connect_to_server()
        if error:
            metrics.record(scenario_name, client_id, "FAIL", error, connect_time)
            return
        ok, register_time, register_error = perform_register_flow(sock, username, password)
        total_time = connect_time + register_time
        if ok:
            metrics.record(scenario_name, client_id, "SUCCESS", None, total_time)
        else:
            metrics.record(scenario_name, client_id, "FAIL", register_error or "auth_error", total_time)
        sock.close()

    for i in range(number_of_clients):
        thread = threading.Thread(target=worker, args=(i,), daemon=True)
        threads.append(thread)
        thread.start()

    print(f"  [S2] {number_of_clients} threads sẵn sàng — flood register...")
    start_event.set()

    for thread in threads:
        thread.join(timeout=RECV_TIMEOUT * 4 + 30)

    metrics.report(scenario_name)
    return metrics

def scenario_s3_private_message_storm(number_of_pairs=10, storm_duration_seconds=10, metrics=None):
    """[S3] Private message storm: các cặp gửi /msg liên tục."""
    if metrics is None:
        metrics = MetricsCollector()
    scenario_name = "S3_msg_storm"
    threads = []
    ready_event = threading.Event()
    total_messages = 0
    total_messages_lock = threading.Lock()

    def pair_worker(pair_id):
        nonlocal total_messages  # <--- SỬA LỖI: khai báo nonlocal
        username_a = f"s3a_{pair_id}_{generate_random_string(4)}"
        username_b = f"s3b_{pair_id}_{generate_random_string(4)}"
        password_a = generate_strong_password()
        password_b = generate_strong_password()

        sock_a, _ = register_and_login(username_a, password_a, scenario_name, pair_id * 2, metrics)
        if not sock_a:
            return
        sock_b, _ = register_and_login(username_b, password_b, scenario_name, pair_id * 2 + 1, metrics)
        if not sock_b:
            safe_close_socket(sock_a)
            return

        ready_event.wait()
        end_time = time.time() + storm_duration_seconds
        message_count = 0

        while time.time() < end_time and not metrics.stop_flag:
            start_send = time.time()
            sent = send_message(sock_a, f"/msg {username_b} StormMsg#{message_count}")
            elapsed = (time.time() - start_send) * 1000
            if sent:
                metrics.record(scenario_name, pair_id, "SUCCESS", None, elapsed)
                message_count += 1
            else:
                metrics.record(scenario_name, pair_id, "FAIL", "unexpected_close", elapsed)
                break
            time.sleep(0.05)

        with total_messages_lock:
            total_messages += message_count

        send_message(sock_a, "/quit")
        send_message(sock_b, "/quit")
        safe_close_socket(sock_a)
        safe_close_socket(sock_b)

    for i in range(number_of_pairs):
        thread = threading.Thread(target=pair_worker, args=(i,), daemon=True)
        threads.append(thread)
        thread.start()

    time.sleep(3)
    print(f"  [S3] {number_of_pairs} cặp sẵn sàng — message storm {storm_duration_seconds}s...")
    ready_event.set()

    for thread in threads:
        thread.join(timeout=storm_duration_seconds + RECV_TIMEOUT * 4 + 15)

    messages_per_second = total_messages / storm_duration_seconds if storm_duration_seconds > 0 else 0
    print(f"  [S3] Tổng tin nhắn gửi: {total_messages} ({messages_per_second:.1f} msg/s)")
    metrics.report(scenario_name)
    return metrics

def scenario_s4_spike(number_of_clients=80, spike_window_seconds=3, metrics=None):
    """[S4] Spike test: nhiều client kết nối trong cửa sổ ngắn."""
    if metrics is None:
        metrics = MetricsCollector()
    scenario_name = "S4_spike"
    threads = []
    start_event = threading.Event()

    def worker(client_id):
        start_event.wait()
        time.sleep(random.random() * spike_window_seconds)
        if metrics.stop_flag:
            return
        username = f"s4_sp_{client_id}_{generate_random_string(4)}"
        password = generate_strong_password()
        register_sock, connect_time, error = connect_to_server(timeout=10)
        if error:
            metrics.record(scenario_name, client_id, "FAIL", error, connect_time)
            return
        ok, register_time, register_error = perform_register_flow(register_sock, username, password)
        register_sock.close()
        if not ok:
            metrics.record(scenario_name, client_id, "FAIL", register_error or "auth_error", connect_time + register_time)
            return
        time.sleep(STEP_DELAY)
        login_sock, connect_time2, error = connect_to_server(timeout=10)
        if error:
            metrics.record(scenario_name, client_id, "FAIL", error, connect_time + register_time + connect_time2)
            return
        ok, login_time, login_error = perform_login_flow(login_sock, username, password)
        total_time = connect_time + register_time + connect_time2 + login_time
        if ok:
            send_message(login_sock, "/quit")
            metrics.record(scenario_name, client_id, "SUCCESS", None, total_time)
        else:
            metrics.record(scenario_name, client_id, "FAIL", login_error or "auth_error", total_time)
        login_sock.close()

    for i in range(number_of_clients):
        thread = threading.Thread(target=worker, args=(i,), daemon=True)
        threads.append(thread)
        thread.start()

    print(f"  [S4] {number_of_clients} threads sẵn sàng — SPIKE trong {spike_window_seconds}s!")
    start_event.set()

    for thread in threads:
        thread.join(timeout=spike_window_seconds + RECV_TIMEOUT * 4 + 30)

    metrics.report(scenario_name)
    return metrics

def scenario_s5_admin_chaos(number_of_normal_clients=15, hold_duration_seconds=20, metrics=None):
    """[S5] Admin chaos: normal clients chat, admin /kick và /list."""
    if metrics is None:
        metrics = MetricsCollector()
    scenario_name = "S5_admin_chaos"
    threads = []
    normal_usernames = []
    normal_lock = threading.Lock()
    start_event = threading.Event()

    def normal_worker(client_id):
        username = f"s5_u{client_id}_{generate_random_string(4)}"
        password = generate_strong_password()
        sock, _ = register_and_login(username, password, scenario_name, client_id, metrics)
        if not sock:
            return
        with normal_lock:
            normal_usernames.append(username)
        start_event.wait()
        end_time = time.time() + hold_duration_seconds
        message_index = 0
        while time.time() < end_time and not metrics.stop_flag:
            start_send = time.time()
            sent = send_message(sock, f"/all Chat #{message_index} from {username}")
            elapsed = (time.time() - start_send) * 1000
            if not sent:
                metrics.record(scenario_name, client_id, "SUCCESS", None, elapsed)
                break
            receive_message(sock)  # consume broadcast
            metrics.record(scenario_name, client_id, "SUCCESS", None, elapsed)
            message_index += 1
            time.sleep(0.3 + random.random() * 0.3)
        safe_close_socket(sock)

    def admin_worker():
        sock, _, error = connect_to_server()
        if error:
            metrics.record(scenario_name, "admin", "FAIL", error, 0)
            return
        ok, login_time, login_error = perform_login_flow(sock, "admin", ADMIN_PASSWORD)
        if not ok:
            metrics.record(scenario_name, "admin", "FAIL", login_error or "auth_error", login_time)
            safe_close_socket(sock)
            return
        start_event.wait()
        time.sleep(1)
        end_time = time.time() + hold_duration_seconds
        action_index = 0
        while time.time() < end_time and not metrics.stop_flag:
            start_action = time.time()
            if action_index % 2 == 0:
                send_message(sock, "/list")
                response = receive_message(sock)
                elapsed = (time.time() - start_action) * 1000
                if response and response != "__TIMEOUT__":
                    metrics.record(scenario_name, "admin", "SUCCESS", None, elapsed)
                else:
                    metrics.record(scenario_name, "admin", "FAIL", classify_error(response), elapsed)
            else:
                with normal_lock:
                    target = random.choice(normal_usernames) if normal_usernames else None
                if target:
                    send_message(sock, f"/kick {target}")
                    response = receive_message(sock)
                    elapsed = (time.time() - start_action) * 1000
                    if response and response != "__TIMEOUT__" and "kick" in response.lower():
                        with normal_lock:
                            if target in normal_usernames:
                                normal_usernames.remove(target)
                        metrics.record(scenario_name, "admin", "SUCCESS", None, elapsed)
                    else:
                        metrics.record(scenario_name, "admin", "FAIL", classify_error(response), elapsed)
            action_index += 1
            time.sleep(2.0)
        send_message(sock, "/quit")
        safe_close_socket(sock)

    for i in range(number_of_normal_clients):
        thread = threading.Thread(target=normal_worker, args=(i,), daemon=True)
        threads.append(thread)
        thread.start()
        time.sleep(0.2)

    time.sleep(2)
    admin_thread = threading.Thread(target=admin_worker, daemon=True)
    threads.append(admin_thread)
    admin_thread.start()

    time.sleep(1)
    print(f"  [S5] {number_of_normal_clients} normal + 1 admin — chaos test {hold_duration_seconds}s...")
    start_event.set()

    for thread in threads:
        thread.join(timeout=hold_duration_seconds + RECV_TIMEOUT * 4 + 15)

    metrics.report(scenario_name)
    return metrics

def scenario_s6_zombie_connection(number_of_zombies=30, metrics=None):
    """[S6] Zombie connection: đăng nhập rồi đóng socket thô (không /quit)."""
    if metrics is None:
        metrics = MetricsCollector()
    scenario_name = "S6_zombie"

    for zombie_id in range(number_of_zombies):
        if metrics.stop_flag:
            break
        username = f"s6_zb_{zombie_id}_{generate_random_string(4)}"
        password = generate_strong_password()
        register_sock, _, error = connect_to_server()
        if error:
            metrics.record(scenario_name, zombie_id, "FAIL", error, 0)
            time.sleep(0.2)
            continue
        ok, register_time, register_error = perform_register_flow(register_sock, username, password)
        register_sock.close()
        if not ok:
            metrics.record(scenario_name, zombie_id, "FAIL", register_error or "auth_error", register_time)
            time.sleep(0.2)
            continue
        time.sleep(STEP_DELAY)
        login_sock, _, error = connect_to_server()
        if error:
            metrics.record(scenario_name, zombie_id, "FAIL", error, 0)
            time.sleep(0.2)
            continue
        ok, login_time, login_error = perform_login_flow(login_sock, username, password)
        total_time = register_time + login_time
        if ok:
            try:
                login_sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            login_sock.close()
            metrics.record(scenario_name, zombie_id, "SUCCESS", None, total_time)
        else:
            metrics.record(scenario_name, zombie_id, "FAIL", login_error or "auth_error", total_time)
            login_sock.close()
        time.sleep(0.2)

    metrics.report(scenario_name)
    return metrics


# ==================== MAIN ====================
def run_all_scenarios():
    """Chạy tuần tự tất cả 6 kịch bản."""
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)

    print("╔════════════════════════════════════════════════════════════╗")
    print("║       STRESS TEST SUITE — Chat Console via TCP           ║")
    print(f"║       Server: {HOST}:{PORT:<5}                             ║")
    print(f"║       Timeout: {RECV_TIMEOUT}s  |  Step delay: {STEP_DELAY}s              ║")
    print("╚════════════════════════════════════════════════════════════╝\n")

    summary = []

    def run_and_record(scenario_name, scenario_function):
        print(f"\n▶▶▶ {scenario_name}")
        print("─" * 60)
        metrics = scenario_function()
        summary.append((scenario_name, metrics.stop_flag, metrics))
        if metrics.stop_flag:
            print(f"  ⚠ DỪNG: {metrics.stop_reason}")
        time.sleep(5)

    run_and_record("[S1] BASELINE 5", lambda: scenario_s1_baseline(5))
    run_and_record("[S1] BASELINE 20", lambda: scenario_s1_baseline(20))
    run_and_record("[S1] BASELINE 50", lambda: scenario_s1_baseline(50))
    run_and_record("[S2] REGISTER FLOOD 30", lambda: scenario_s2_register_flood(30))
    run_and_record("[S3] MSG STORM 10 pairs 10s", lambda: scenario_s3_private_message_storm(10, 10))
    run_and_record("[S4] SPIKE 80 in 3s", lambda: scenario_s4_spike(80, 3))
    run_and_record("[S5] ADMIN CHAOS 15 normal 20s", lambda: scenario_s5_admin_chaos(15, 20))
    run_and_record("[S6] ZOMBIE 30", lambda: scenario_s6_zombie_connection(30))

    print(f"\n{'█'*60}")
    print("  TỔNG KẾT TOÀN BỘ TEST SUITE")
    print(f"{'█'*60}")

    stopped_count = sum(1 for _, stopped, _ in summary if stopped)
    completed_count = len(summary) - stopped_count

    for scenario_name, stopped, metrics in summary:
        total_clients = len(metrics.results)
        failures = sum(1 for r in metrics.results if r["status"] == "FAIL")
        error_percent = failures / total_clients * 100 if total_clients else 0
        response_times = [r["response_time_ms"] for r in metrics.results if r["response_time_ms"] > 0]
        average_rt = sum(response_times) / len(response_times) if response_times else 0
        icon = "🛑" if stopped else "✅"
        print(f"  {icon} {scenario_name}")
        print(f"      Clients: {total_clients}  |  Lỗi: {failures} ({error_percent:.1f}%)  |  Avg RT: {average_rt:.0f}ms")

    print(f"\n  Kịch bản hoàn thành (không dừng): {completed_count}/{len(summary)}")
    print(f"  Kịch bản bị dừng sớm          : {stopped_count}/{len(summary)}")
    print(f"{'█'*60}\n")

def run_single_scenario(scenario_name):
    """Chạy một kịch bản duy nhất (S1..S6)."""
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)

    mapping = {
        "S1": lambda: [scenario_s1_baseline(5), scenario_s1_baseline(20), scenario_s1_baseline(50)],
        "S2": lambda: scenario_s2_register_flood(30),
        "S3": lambda: scenario_s3_private_message_storm(10, 10),
        "S4": lambda: scenario_s4_spike(80, 3),
        "S5": lambda: scenario_s5_admin_chaos(15, 20),
        "S6": lambda: scenario_s6_zombie_connection(30),
    }
    key = scenario_name.upper()
    if key not in mapping:
        print(f"Kịch bản không hợp lệ: {scenario_name}. Hợp lệ: S1, S2, S3, S4, S5, S6")
        return
    print(f"\n▶ Chạy kịch bản {key}")
    print("─" * 60)
    mapping[key]()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_single_scenario(sys.argv[1])
    else:
        run_all_scenarios()