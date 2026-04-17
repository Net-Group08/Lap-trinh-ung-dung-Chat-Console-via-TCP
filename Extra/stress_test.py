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
ADMIN_PASS = "adminpass"

WARN_AVG_RT_MS = 3000
STOP_AVG_RT_MS = 5000
STOP_ERROR_RATE = 0.30
PASS_AVG_RT_MS = 3000
PASS_ERROR_RATE = 0.10


# ==================== METRICS COLLECTOR ====================
class Metrics:
    def __init__(self):
        self.lock = threading.Lock()
        self.results = []
        self.stop_flag = False
        self.stop_reason = ""

    def record(self, scenario, cid, status, err_type, rt_ms):
        with self.lock:
            self.results.append({
                "scenario": scenario,
                "client_id": cid,
                "status": status,
                "error_type": err_type or "",
                "response_time_ms": round(rt_ms, 2)
            })
            if not self.stop_flag and len(self.results) >= 5:
                total = len(self.results)
                fails = sum(1 for r in self.results if r["status"] == "FAIL")
                if fails / total > STOP_ERROR_RATE:
                    self.stop_flag = True
                    self.stop_reason = f"Error rate {fails}/{total} ({fails/total*100:.1f}%) > {STOP_ERROR_RATE*100:.0f}%"
                    return
                rts = [r["response_time_ms"] for r in self.results if r["response_time_ms"] > 0]
                if rts and sum(rts) / len(rts) > STOP_AVG_RT_MS:
                    self.stop_flag = True
                    self.stop_reason = f"Avg RT {sum(rts)/len(rts):.0f}ms > {STOP_AVG_RT_MS}ms"

    def report(self, name):
        with self.lock:
            data = list(self.results)
        total = len(data)
        success = sum(1 for r in data if r["status"] == "SUCCESS")
        fail = total - success
        err_pct = fail / total * 100 if total else 0
        rts = [r["response_time_ms"] for r in data if r["response_time_ms"] > 0]
        avg = sum(rts) / len(rts) if rts else 0
        p95 = self._percentile(rts, 95) if rts else 0
        max_rt = max(rts) if rts else 0
        err_types = {}
        for r in data:
            if r["status"] == "FAIL" and r["error_type"]:
                err_types[r["error_type"]] = err_types.get(r["error_type"], 0) + 1
        verdict = "✅ PASS" if err_pct <= PASS_ERROR_RATE*100 and avg <= PASS_AVG_RT_MS else "⚠️  WARN"
        if self.stop_flag:
            verdict = "🛑 STOPPED"
        print(f"\n{'═'*60}\n  KẾT QUẢ: {name}  [{verdict}]\n{'═'*60}")
        print(f"  Tổng client: {total}  |  Thành công: {success}  |  Thất bại: {fail} ({err_pct:.1f}%)")
        print(f"  RT AVG: {avg:.1f}ms  |  P95: {p95:.1f}ms  |  MAX: {max_rt:.1f}ms")
        if err_types:
            print("  Phân loại lỗi:")
            for e, c in sorted(err_types.items(), key=lambda x: -x[1]):
                print(f"    {e:25s}: {c}")
        if self.stop_flag:
            print(f"  🛑 DỪNG: {self.stop_reason}")
        print(f"{'═'*60}\n")
        self._write_csv(data)

    @staticmethod
    def _percentile(data, p):
        if not data:
            return 0.0
        s = sorted(data)
        k = (len(s) - 1) * p / 100.0
        f = int(k)
        return s[f] + (k - f) * (s[min(f+1, len(s)-1)] - s[f])

    def _write_csv(self, data):
        try:
            new = not os.path.exists(LOG_FILE) or os.path.getsize(LOG_FILE) == 0
            with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["scenario", "client_id", "status", "error_type", "response_time_ms"])
                if new:
                    w.writeheader()
                w.writerows(data)
        except Exception as e:
            print(f"  ✗ CSV error: {e}")


# ==================== HELPER FUNCTIONS ====================
def rand_str(n=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=n))

def rand_pwd():
    upper = random.choice(string.ascii_uppercase)
    lower = random.choice(string.ascii_lowercase)
    digit = random.choice(string.digits)
    special = random.choice("!@#$%^&*()-_=+[]{}|;:,.<>?/")
    rest = ''.join(random.choices(string.ascii_letters + string.digits + "!@#$%^&*", k=8))
    pwd = list(upper + lower + digit + special + rest)
    random.shuffle(pwd)
    return ''.join(pwd)

def connect(timeout=RECV_TIMEOUT):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    t0 = time.time()
    try:
        s.connect((HOST, PORT))
        return s, (time.time() - t0) * 1000, None
    except socket.timeout:
        return None, (time.time() - t0) * 1000, "timeout"
    except ConnectionRefusedError:
        return None, (time.time() - t0) * 1000, "connection_refused"
    except Exception:
        return None, (time.time() - t0) * 1000, "connection_refused"

def send(sock, msg):
    try:
        sock.sendall(msg.encode())
        return True
    except:
        return False

def recv(sock, sz=4096):
    try:
        d = sock.recv(sz)
        return d.decode() if d else None
    except socket.timeout:
        return "__TIMEOUT__"
    except:
        return None

def classify(resp):
    if resp is None:
        return "unexpected_close"
    if resp == "__TIMEOUT__":
        return "timeout"
    if isinstance(resp, str) and resp.startswith("ERROR"):
        return "auth_error"
    return "unexpected_close"

def do_flow(sock, mode, user, pwd):
    """mode: 'LOGIN' hoặc 'REGISTER'"""
    t0 = time.time()
    if not send(sock, mode):
        return False, (time.time() - t0) * 1000, "unexpected_close"
    time.sleep(STEP_DELAY)
    if not send(sock, user):
        return False, (time.time() - t0) * 1000, "unexpected_close"
    resp = recv(sock)
    if resp in (None, "__TIMEOUT__"):
        return False, (time.time() - t0) * 1000, classify(resp)
    if mode == "LOGIN" and resp != "REQ_PASS":
        return False, (time.time() - t0) * 1000, "auth_error"
    if mode == "REGISTER" and resp != "USERNAME_OK":
        return False, (time.time() - t0) * 1000, "auth_error"
    time.sleep(STEP_DELAY)
    if not send(sock, pwd):
        return False, (time.time() - t0) * 1000, "unexpected_close"
    resp = recv(sock)
    if resp == "SUCCESS":
        return True, (time.time() - t0) * 1000, None
    return False, (time.time() - t0) * 1000, "auth_error"

def full_login(user, pwd, scenario, cid, metrics):
    # Register
    s_r, rt_c, err = connect()
    if err:
        metrics.record(scenario, cid, "FAIL", err, rt_c)
        return None, 0
    ok, rt_r, e = do_flow(s_r, "REGISTER", user, pwd)
    s_r.close()
    if not ok:
        metrics.record(scenario, cid, "FAIL", e or "auth_error", rt_r)
        return None, 0
    time.sleep(STEP_DELAY)
    # Login
    s, rt_c2, err = connect()
    if err:
        metrics.record(scenario, cid, "FAIL", err, rt_c2)
        return None, 0
    ok, rt_l, e = do_flow(s, "LOGIN", user, pwd)
    if not ok:
        metrics.record(scenario, cid, "FAIL", e or "auth_error", rt_l)
        s.close()
        return None, 0
    return s, rt_c + rt_r + rt_c2 + rt_l

def safe_close(s):
    if s:
        try:
            s.close()
        except:
            pass


# ==================== KỊCH BẢN ====================
def s1_baseline(n, metrics=None):
    metrics = metrics or Metrics()
    name = f"S1_baseline_{n}c"
    threads = []
    def worker(cid):
        if metrics.stop_flag:
            return
        u = f"s1_u{cid}_{rand_str(4)}"
        p = rand_pwd()
        # Register
        s_r, _, err = connect()
        if err:
            metrics.record(name, cid, "FAIL", err, 0)
            return
        ok, rt_r, e = do_flow(s_r, "REGISTER", u, p)
        s_r.close()
        if not ok:
            metrics.record(name, cid, "FAIL", e or "auth_error", rt_r)
            return
        time.sleep(STEP_DELAY)
        # Login
        s, _, err = connect()
        if err:
            metrics.record(name, cid, "FAIL", err, 0)
            return
        ok, rt_l, e = do_flow(s, "LOGIN", u, p)
        if ok:
            send(s, "/all hello")
            time.sleep(STEP_DELAY)
            send(s, "/quit")
            metrics.record(name, cid, "SUCCESS", None, rt_l)
        else:
            metrics.record(name, cid, "FAIL", e or "auth_error", rt_l)
        s.close()
    for i in range(n):
        if metrics.stop_flag:
            break
        t = threading.Thread(target=worker, args=(i,), daemon=True)
        threads.append(t)
        t.start()
        time.sleep(0.1)
    for t in threads:
        t.join(timeout=RECV_TIMEOUT*4+10)
    metrics.report(name)
    return metrics

def s2_register_flood(n=30, metrics=None):
    metrics = metrics or Metrics()
    name = "S2_register_flood"
    threads = []
    start = threading.Event()
    def worker(cid):
        start.wait()
        if metrics.stop_flag:
            return
        u = f"s2_rf_{cid}_{rand_str(6)}"
        p = rand_pwd()
        s, rt_c, err = connect()
        if err:
            metrics.record(name, cid, "FAIL", err, rt_c)
            return
        ok, rt_r, e = do_flow(s, "REGISTER", u, p)
        s.close()
        metrics.record(name, cid, "SUCCESS" if ok else "FAIL", None if ok else (e or "auth_error"), rt_c+rt_r)
    for i in range(n):
        t = threading.Thread(target=worker, args=(i,), daemon=True)
        threads.append(t)
        t.start()
    print(f"  [S2] {n} threads ready — flood register...")
    start.set()
    for t in threads:
        t.join(timeout=RECV_TIMEOUT*4+30)
    metrics.report(name)
    return metrics

def s3_msg_storm(pairs=10, duration=10, metrics=None):
    metrics = metrics or Metrics()
    name = "S3_msg_storm"
    threads = []
    ready = threading.Event()
    total_msgs = 0
    lock = threading.Lock()
    def worker(pid):
        ua = f"s3a_{pid}_{rand_str(4)}"
        ub = f"s3b_{pid}_{rand_str(4)}"
        pa = rand_pwd()
        pb = rand_pwd()
        sa, _ = full_login(ua, pa, name, pid*2, metrics)
        if not sa:
            return
        sb, _ = full_login(ub, pb, name, pid*2+1, metrics)
        if not sb:
            safe_close(sa)
            return
        ready.wait()
        end = time.time() + duration
        cnt = 0
        while time.time() < end and not metrics.stop_flag:
            t0 = time.time()
            ok = send(sa, f"/msg {ub} Storm#{cnt}")
            rt = (time.time() - t0) * 1000
            if ok:
                metrics.record(name, pid, "SUCCESS", None, rt)
                cnt += 1
            else:
                metrics.record(name, pid, "FAIL", "unexpected_close", rt)
                break
            time.sleep(0.05)
        with lock:
            nonlocal total_msgs
            total_msgs += cnt
        send(sa, "/quit")
        send(sb, "/quit")
        safe_close(sa)
        safe_close(sb)
    for i in range(pairs):
        t = threading.Thread(target=worker, args=(i,), daemon=True)
        threads.append(t)
        t.start()
    time.sleep(3)
    print(f"  [S3] {pairs} pairs ready — storm {duration}s...")
    ready.set()
    for t in threads:
        t.join(timeout=duration+RECV_TIMEOUT*4+15)
    print(f"  [S3] Total msgs: {total_msgs} ({total_msgs/duration:.1f} msg/s)")
    metrics.report(name)
    return metrics

def s4_spike(n=50, window=2, metrics=None):
    metrics = metrics or Metrics()
    name = "S4_spike"
    threads = []
    start = threading.Event()
    def worker(cid):
        start.wait()
        time.sleep(random.random() * window)
        if metrics.stop_flag:
            return
        u = f"s4_sp_{cid}_{rand_str(4)}"
        p = rand_pwd()
        s_r, rt_c, err = connect(timeout=10)
        if err:
            metrics.record(name, cid, "FAIL", err, rt_c)
            return
        ok, rt_r, e = do_flow(s_r, "REGISTER", u, p)
        s_r.close()
        if not ok:
            metrics.record(name, cid, "FAIL", e or "auth_error", rt_c+rt_r)
            return
        time.sleep(STEP_DELAY)
        s, rt_c2, err = connect(timeout=10)
        if err:
            metrics.record(name, cid, "FAIL", err, rt_c+rt_r+rt_c2)
            return
        ok, rt_l, e = do_flow(s, "LOGIN", u, p)
        total = rt_c + rt_r + rt_c2 + rt_l
        if ok:
            send(s, "/quit")
            metrics.record(name, cid, "SUCCESS", None, total)
        else:
            metrics.record(name, cid, "FAIL", e or "auth_error", total)
        s.close()
    for i in range(n):
        t = threading.Thread(target=worker, args=(i,), daemon=True)
        threads.append(t)
        t.start()
    print(f"  [S4] {n} threads — spike in {window}s")
    start.set()
    for t in threads:
        t.join(timeout=window+RECV_TIMEOUT*4+30)
    metrics.report(name)
    return metrics

def s5_admin_chaos(normal=15, hold=20, metrics=None):
    metrics = metrics or Metrics()
    name = "S5_admin_chaos"
    threads = []
    normal_users = []
    norm_lock = threading.Lock()
    start = threading.Event()
    def normal_worker(cid):
        u = f"s5_u{cid}_{rand_str(4)}"
        p = rand_pwd()
        s, _ = full_login(u, p, name, cid, metrics)
        if not s:
            return
        with norm_lock:
            normal_users.append(u)
        start.wait()
        end = time.time() + hold
        idx = 0
        while time.time() < end and not metrics.stop_flag:
            t0 = time.time()
            ok = send(s, f"/all Chat#{idx} from {u}")
            rt = (time.time() - t0) * 1000
            if not ok:
                metrics.record(name, cid, "SUCCESS", None, rt)
                break
            recv(s)  # consume broadcast (bỏ qua)
            metrics.record(name, cid, "SUCCESS", None, rt)
            idx += 1
            time.sleep(0.3 + random.random() * 0.3)
        safe_close(s)
    def admin_worker():
        s, _, err = connect()
        if err:
            metrics.record(name, "admin", "FAIL", err, 0)
            return
        ok, rt_l, e = do_flow(s, "LOGIN", "admin", ADMIN_PASS)
        if not ok:
            metrics.record(name, "admin", "FAIL", e or "auth_error", rt_l)
            safe_close(s)
            return
        start.wait()
        time.sleep(1)
        end = time.time() + hold
        act = 0
        while time.time() < end and not metrics.stop_flag:
            t0 = time.time()
            if act % 2 == 0:
                send(s, "/list")
                resp = recv(s)
                rt = (time.time() - t0) * 1000
                metrics.record(name, "admin", "SUCCESS" if resp and resp != "__TIMEOUT__" else "FAIL",
                               classify(resp), rt)
            else:
                with norm_lock:
                    target = random.choice(normal_users) if normal_users else None
                if target:
                    send(s, f"/kick {target}")
                    resp = recv(s)
                    rt = (time.time() - t0) * 1000
                    if resp and resp != "__TIMEOUT__" and "kick" in resp.lower():
                        with norm_lock:
                            if target in normal_users:
                                normal_users.remove(target)
                    metrics.record(name, "admin", "SUCCESS" if resp and resp != "__TIMEOUT__" else "FAIL",
                                   classify(resp), rt)
            act += 1
            time.sleep(2.0)
        send(s, "/quit")
        safe_close(s)
    for i in range(normal):
        t = threading.Thread(target=normal_worker, args=(i,), daemon=True)
        threads.append(t)
        t.start()
        time.sleep(0.2)
    time.sleep(2)
    t_admin = threading.Thread(target=admin_worker, daemon=True)
    threads.append(t_admin)
    t_admin.start()
    time.sleep(1)
    print(f"  [S5] {normal} normal + 1 admin — chaos {hold}s")
    start.set()
    for t in threads:
        t.join(timeout=hold+RECV_TIMEOUT*4+15)
    metrics.report(name)
    return metrics

def s6_zombie(n=30, metrics=None):
    metrics = metrics or Metrics()
    name = "S6_zombie"
    for cid in range(n):
        if metrics.stop_flag:
            break
        u = f"s6_zb_{cid}_{rand_str(4)}"
        p = rand_pwd()
        s_r, _, err = connect()
        if err:
            metrics.record(name, cid, "FAIL", err, 0)
            time.sleep(0.2)
            continue
        ok, rt_r, e = do_flow(s_r, "REGISTER", u, p)
        s_r.close()
        if not ok:
            metrics.record(name, cid, "FAIL", e or "auth_error", rt_r)
            time.sleep(0.2)
            continue
        time.sleep(STEP_DELAY)
        s, _, err = connect()
        if err:
            metrics.record(name, cid, "FAIL", err, 0)
            time.sleep(0.2)
            continue
        ok, rt_l, e = do_flow(s, "LOGIN", u, p)
        total = rt_r + rt_l
        if ok:
            # Đóng thô (zombie)
            try:
                s.shutdown(socket.SHUT_RDWR)
            except:
                pass
            s.close()
            metrics.record(name, cid, "SUCCESS", None, total)
        else:
            metrics.record(name, cid, "FAIL", e or "auth_error", total)
            s.close()
        time.sleep(0.2)
    metrics.report(name)
    return metrics


# ==================== MAIN ====================
def run_all():
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
    print(" ╔════════════════════════════════════════════════════════════╗")
    print(" ║       STRESS TEST SUITE — Chat Console via TCP             ║")
    print(f"║       Server: {HOST}:{PORT:<5}                             ║")
    print(f"║      Timeout: {RECV_TIMEOUT}s  |  Step delay: {STEP_DELAY}s║")
    print(" ╚════════════════════════════════════════════════════════════╝\n")

    summary = []  # (name, stop_flag, metrics)
    def _run(name, fn):
        print(f"\n▶▶▶ {name}")
        print("─" * 60)
        m = fn()
        summary.append((name, m.stop_flag, m))
        if m.stop_flag:
            print(f"  ⚠ DỪNG: {m.stop_reason}")
        time.sleep(5)

    _run("[S1] BASELINE 5", lambda: s1_baseline(5))
    _run("[S1] BASELINE 20", lambda: s1_baseline(20))
    _run("[S1] BASELINE 50", lambda: s1_baseline(50))
    _run("[S2] REGISTER FLOOD 30", lambda: s2_register_flood(30))
    _run("[S3] MSG STORM 10 pairs 10s", lambda: s3_msg_storm(10, 10))
    _run("[S4] SPIKE 80 in 3s", lambda: s4_spike(80, 3))
    _run("[S5] ADMIN CHAOS 15 normal 20s", lambda: s5_admin_chaos(15, 20))
    _run("[S6] ZOMBIE 30", lambda: s6_zombie(30))

    # Tổng kết
    print(f"\n{'█'*60}\n  TỔNG KẾT TOÀN BỘ TEST SUITE\n{'█'*60}")
    stopped_cnt = sum(1 for _, stopped, _ in summary if stopped)
    completed_cnt = len(summary) - stopped_cnt
    for name, stopped, m in summary:
        total = len(m.results)
        fails = sum(1 for r in m.results if r["status"] == "FAIL")
        err_pct = fails / total * 100 if total else 0
        rts = [r["response_time_ms"] for r in m.results if r["response_time_ms"] > 0]
        avg = sum(rts) / len(rts) if rts else 0
        icon = "🛑" if stopped else "✅"
        print(f"  {icon} {name}")
        print(f"      Clients: {total}  |  Lỗi: {fails} ({err_pct:.1f}%)  |  Avg RT: {avg:.0f}ms")
    print(f"\n  Kịch bản hoàn thành : {completed_cnt}/{len(summary)}")
    print(f"  Kịch bản bị dừng sớm          : {stopped_cnt}/{len(summary)}")
    print(f"{'█'*60}\n")

def run_single(sc):
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
    mapping = {
        "S1": lambda: [s1_baseline(5), s1_baseline(20), s1_baseline(50)],
        "S2": lambda: s2_register_flood(30),
        "S3": lambda: s3_msg_storm(10, 10),
        "S4": lambda: s4_spike(80, 3),
        "S5": lambda: s5_admin_chaos(15, 20),
        "S6": lambda: s6_zombie(30),
    }
    key = sc.upper()
    if key not in mapping:
        print(f"Kịch bản không hợp lệ: {sc}. Hợp lệ: S1..S6")
        return
    print(f"\n▶ Chạy {key}\n" + "─"*60)
    mapping[key]()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_single(sys.argv[1])
    else:
        run_all()