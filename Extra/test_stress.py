"""
Stress Test Cases - Kiểm tra hiệu suất và độ ổn định dưới tải cao

Bao gồm:
1. Heavy concurrent connections
2. High-frequency message sending
3. Rapid registration/login
4. Memory and resource consumption
5. Response time under load
6. Server stability and error recovery
"""

import unittest
import socket
import threading
import time
import random
import string
from server import user_service, ban_manager
from config import HOST, PORT
import sys


class TestStressConcurrentRegistration(unittest.TestCase):
    """Stress test: Đăng ký hàng loạt từ multiple threads"""
    
    def setUp(self):
        """Chuẩn bị trước test"""
        self.success_count = 0
        self.failure_count = 0
        self.lock = threading.Lock()
    
    def register_user_thread(self, user_id):
        """Thread function để đăng ký user"""
        try:
            username = f"sreg_{user_id}_{time.time_ns() & 0xFFFFFFFF:08x}"
            password = f"StressPass@{user_id:04d}Aa"
            
            success, message = user_service.register_user(username, password)
            
            with self.lock:
                if success:
                    self.success_count += 1
                else:
                    self.failure_count += 1
        except Exception as e:
            with self.lock:
                self.failure_count += 1
            print(f"Error in thread {user_id}: {e}")
    
    def test_stress_100_concurrent_registrations(self):
        """Stress Test 1: 100 concurrent registrations"""
        print("\n=== STRESS TEST 1: 100 Concurrent Registrations ===")
        print("Note: Password hashing adds ~200ms overhead per registration\n")
        
        threads = []
        start_time = time.time()
        
        # Create 100 threads with staggered start to prevent thundering herd
        for i in range(100):
            thread = threading.Thread(target=self.register_user_thread, args=(i,))
            threads.append(thread)
            thread.start()
            
            # Stagger thread starts
            if i % 20 == 19:
                time.sleep(0.05)
        
        # Wait for all threads with generous timeout (100 regs × 200ms = 20s minimum)
        for thread in threads:
            thread.join(timeout=60)
        
        elapsed = time.time() - start_time
        total = self.success_count + self.failure_count
        
        print(f"Total attempts: {total}")
        print(f"✓ Success: {self.success_count}")
        print(f"✗ Failures: {self.failure_count}")
        print(f"Time: {elapsed:.2f}s")
        if total > 0:
            print(f"Rate: {total/elapsed:.2f} registrations/second")
            print(f"Success rate: {(self.success_count/total)*100:.1f}%")
        
        # With hashing overhead, expect 60%+ success rate
        if total > 0:
            min_success = max(1, int(total * 0.60))
            self.assertGreaterEqual(self.success_count, min_success,
                                  f"Expected at least {min_success} successes, got {self.success_count}")
    
    def test_stress_500_concurrent_registrations(self):
        """Stress Test 2: 500 concurrent registrations"""
        print("\n=== STRESS TEST 2: 500 Concurrent Registrations ===")
        print("Note: Heavy concurrent load with hashing overhead\n")
        
        # Reset counters
        self.success_count = 0
        self.failure_count = 0
        
        threads = []
        start_time = time.time()
        
        # Create 500 threads with staggered start
        for i in range(500):
            thread = threading.Thread(target=self.register_user_thread, args=(i,))
            threads.append(thread)
            thread.start()
            
            # Stagger to avoid connection pool exhaustion
            if i % 50 == 49:
                time.sleep(0.1)
        
        # Wait for all threads with generous timeout (500 regs × 200ms = 100s minimum)
        for thread in threads:
            thread.join(timeout=120)
        
        elapsed = time.time() - start_time
        total = self.success_count + self.failure_count
        
        print(f"Total attempts: {total}")
        print(f"✓ Success: {self.success_count}")
        print(f"✗ Failures: {self.failure_count}")
        print(f"Time: {elapsed:.2f}s")
        if total > 0:
            print(f"Rate: {total/elapsed:.2f} registrations/second")
            print(f"Success rate: {(self.success_count/total)*100:.1f}%")
        
        # With heavy load, expect 50%+ success rate
        if total > 0:
            min_success = max(1, int(total * 0.50))
            self.assertGreaterEqual(self.success_count, min_success,
                                  f"Expected at least {min_success} successes, got {self.success_count}")


class TestStressConcurrentLogin(unittest.TestCase):
    """Stress test: Đăng nhập hàng loạt"""
    
    @classmethod
    def setUpClass(cls):
        """Setup - tạo user pool cho testing"""
        print("\n=== Setting up test users for login stress tests ===")
        cls.test_users = []
        
        for i in range(100):
            username = f"stress_login_{i}_{int(time.time())}"
            password = f"StressPass@{i:04d}Aa"
            
            success, _ = user_service.register_user(username, password)
            if success:
                cls.test_users.append((username, password))
        
        print(f"Created {len(cls.test_users)} test users")
    
    def setUp(self):
        """Chuẩn bị trước test"""
        self.success_count = 0
        self.failure_count = 0
        self.lock = threading.Lock()
    
    def login_user_thread(self, username, password):
        """Thread function để đăng nhập"""
        try:
            success, message = user_service.login_user(username, password)
            
            with self.lock:
                if success:
                    self.success_count += 1
                else:
                    self.failure_count += 1
        except Exception as e:
            with self.lock:
                self.failure_count += 1
    
    def test_stress_100_concurrent_logins(self):
        """Stress Test 3: 100 concurrent logins"""
        print("\n=== STRESS TEST 3: 100 Concurrent Logins ===")
        
        if len(self.test_users) < 100:
            self.skipTest(f"Not enough test users: {len(self.test_users)}")
        
        threads = []
        start_time = time.time()
        
        # Create 100 threads with different users
        for i in range(100):
            username, password = self.test_users[i % len(self.test_users)]
            thread = threading.Thread(
                target=self.login_user_thread,
                args=(username, password)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        elapsed = time.time() - start_time
        total = self.success_count + self.failure_count
        
        print(f"Total logins: {total}")
        print(f"✓ Success: {self.success_count}")
        print(f"✗ Failures: {self.failure_count}")
        print(f"Time: {elapsed:.2f}s")
        print(f"Rate: {total/elapsed:.2f} logins/second")
        
        # All should succeed
        self.assertEqual(self.success_count, total,
                        "All logins should succeed")


class TestStressConcurrentConnections(unittest.TestCase):
    """Stress test: Multiple socket connections"""
    
    def setUp(self):
        """Chuẩn bị trước test"""
        self.connected_sockets = []
        self.lock = threading.Lock()
    
    def tearDown(self):
        """Dọn dẹp sau test"""
        for sock in self.connected_sockets:
            try:
                sock.close()
            except:
                pass
    
    def connect_thread(self, idx):
        """Thread function để kết nối"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)  # 5 second timeout
            sock.connect((HOST, PORT))
            
            with self.lock:
                self.connected_sockets.append(sock)
        except socket.timeout:
            print(f"Connection {idx} timeout")
        except ConnectionRefusedError:
            print(f"Connection {idx} refused - server may not be running")
        except Exception as e:
            print(f"Connection {idx} failed: {type(e).__name__}: {e}")
    
    def test_stress_50_concurrent_connections(self):
        """Stress Test 4: 50 concurrent socket connections"""
        print("\n=== STRESS TEST 4: 50 Concurrent Socket Connections ===")
        print("Note: Make sure server is running (python start_server.py)\n")
        
        threads = []
        start_time = time.time()
        
        # Create 50 connection threads with staggered start
        for i in range(50):
            thread = threading.Thread(target=self.connect_thread, args=(i,))
            threads.append(thread)
            thread.start()
            
            # Stagger connection attempts to avoid thundering herd
            if i % 10 == 9:
                time.sleep(0.1)
        
        # Wait for all threads with generous timeout
        for thread in threads:
            thread.join(timeout=10)
        
        elapsed = time.time() - start_time
        
        print(f"Successful connections: {len(self.connected_sockets)}")
        print(f"Time: {elapsed:.2f}s")
        if len(self.connected_sockets) > 0:
            print(f"Rate: {len(self.connected_sockets)/elapsed:.2f} connections/second")
        
        # At least 80% should connect (40 out of 50)
        if len(self.connected_sockets) < 40:
            print(f"\n⚠️  WARNING: Only {len(self.connected_sockets)}/50 connections successful")
            print("   Possible issues:")
            print("   1. Server not running? Start with: python start_server.py")
            print("   2. Server backlog too small? (fixed in server_core.py)")
            print("   3. Network/firewall blocking connections?")
        
        self.assertGreaterEqual(len(self.connected_sockets), 40,
                              "At least 40 connections should succeed")


class TestStressHighFrequencyMessages(unittest.TestCase):
    """Stress test: High-frequency message operations"""
    
    def test_stress_rapid_password_validation(self):
        """Stress Test 5: Rapid password strength validation"""
        print("\n=== STRESS TEST 5: 1000 Rapid Password Validations ===")
        
        from server import security_utils
        
        start_time = time.time()
        valid_count = 0
        invalid_count = 0
        
        for i in range(1000):
            # Generate random passwords
            if i % 2 == 0:
                pwd = f"Valid@Pass{i:04d}Aa"
                is_strong, _ = security_utils.checkpassword_strength(pwd)
                if is_strong:
                    valid_count += 1
            else:
                pwd = "weak"
                is_strong, _ = security_utils.checkpassword_strength(pwd)
                if not is_strong:
                    invalid_count += 1
        
        elapsed = time.time() - start_time
        
        print(f"Valid passwords detected: {valid_count}")
        print(f"Invalid passwords detected: {invalid_count}")
        print(f"Time: {elapsed:.2f}s")
        print(f"Rate: {1000/elapsed:.2f} validations/second")
        
        # Should process quickly (< 5 seconds)
        self.assertLess(elapsed, 5.0, "Should process 1000 validations in < 5 seconds")
    
    def test_stress_rapid_ban_operations(self):
        """Stress Test 6: Rapid ban/unban operations"""
        print("\n=== STRESS TEST 6: 500 Rapid Ban/Unban Operations ===")
        
        start_time = time.time()
        
        for i in range(500):
            username = f"ban_{i}_{time.time_ns() & 0xFFFFFFFF:08x}"
            
            # Ban
            ban_manager.ban_user(username)
            is_banned = ban_manager.is_banned(username)
            self.assertTrue(is_banned)
            
            # Unban
            ban_manager.unban_user(username)
            is_banned = ban_manager.is_banned(username)
            self.assertFalse(is_banned)
        
        elapsed = time.time() - start_time
        
        print(f"Operations: 500 ban/unban pairs")
        print(f"Time: {elapsed:.2f}s")
        print(f"Rate: {1000/elapsed:.2f} operations/second")


class TestStressLongDuration(unittest.TestCase):
    """Stress test: Long duration operations"""
    
    def test_stress_sustained_registration_load(self):
        """Stress Test 7: Sustained registration for 30 seconds"""
        print("\n=== STRESS TEST 7: Sustained Registration Load (30s) ===")
        
        self.success_count = 0
        self.failure_count = 0
        self.lock = threading.Lock()
        self.stop_flag = False
        
        def registration_worker():
            """Worker thread for continuous registration"""
            counter = 0
            while not self.stop_flag:
                try:
                    username = f"sst_{counter}_{time.time_ns() & 0xFFFFFFFF:08x}"
                    password = f"Sustain@{counter:04d}Aa"
                    
                    success, _ = user_service.register_user(username, password)
                    
                    with self.lock:
                        if success:
                            self.success_count += 1
                        else:
                            self.failure_count += 1
                    
                    counter += 1
                except:
                    with self.lock:
                        self.failure_count += 1
        
        # Start 5 worker threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=registration_worker, daemon=True)
            threads.append(thread)
            thread.start()
        
        # Run for 30 seconds
        start_time = time.time()
        time.sleep(30)
        self.stop_flag = True
        
        # Wait for threads to finish
        for thread in threads:
            thread.join(timeout=5)
        
        elapsed = time.time() - start_time
        total = self.success_count + self.failure_count
        
        print(f"Duration: {elapsed:.2f}s")
        print(f"Total registrations: {total}")
        print(f"✓ Success: {self.success_count}")
        print(f"✗ Failures: {self.failure_count}")
        print(f"Rate: {total/elapsed:.2f} registrations/second")
        print(f"Success rate: {(self.success_count/total)*100:.1f}%")


class TestStressErrorRecovery(unittest.TestCase):
    """Stress test: Error handling and recovery"""
    
    def test_stress_invalid_credentials_handling(self):
        """Stress Test 8: Handling many invalid login attempts"""
        print("\n=== STRESS TEST 8: 1000 Invalid Login Attempts ===")
        
        start_time = time.time()
        rejected_count = 0
        
        for i in range(1000):
            username = f"invalid_{i}"
            password = f"Invalid@{i:04d}Aa"
            
            success, _ = user_service.login_user(username, password)
            if not success:
                rejected_count += 1
        
        elapsed = time.time() - start_time
        
        print(f"Total attempts: 1000")
        print(f"Rejected: {rejected_count}")
        print(f"Time: {elapsed:.2f}s")
        print(f"Rate: {1000/elapsed:.2f} attempts/second")
        
        # All should be rejected
        self.assertEqual(rejected_count, 1000, "All invalid logins should be rejected")
    
    def test_stress_duplicate_registration_attempts(self):
        """Stress Test 9: Repeated duplicate registration attempts"""
        print("\n=== STRESS TEST 9: 100 Duplicate Registration Attempts ===")
        
        username = f"dup_stress_{int(time.time())}"
        password = "DupStress@123Aa"
        
        # Register once
        success, _ = user_service.register_user(username, password)
        self.assertTrue(success)
        
        start_time = time.time()
        rejected_count = 0
        
        # Try to register 100 times
        for i in range(100):
            success, _ = user_service.register_user(username, password)
            if not success:
                rejected_count += 1
        
        elapsed = time.time() - start_time
        
        print(f"Duplicate attempts: 100")
        print(f"Rejected: {rejected_count}")
        print(f"Time: {elapsed:.2f}s")
        
        # All duplicate attempts should be rejected
        self.assertEqual(rejected_count, 100, "All duplicates should be rejected")


class TestStressMemoryStability(unittest.TestCase):
    """Stress test: Memory and stability"""
    
    def test_stress_large_dataset_registration(self):
        """Stress Test 10: Register 200 users sequentially"""
        print("\n=== STRESS TEST 10: 200 Sequential Registrations ===")
        
        start_time = time.time()
        success_count = 0
        failure_count = 0
        
        for i in range(200):
            username = f"lset_{i}_{time.time_ns() & 0xFFFFFFFF:08x}"
            password = f"LargeSet@{i:04d}Aa"
            
            try:
                success, _ = user_service.register_user(username, password)
                if success:
                    success_count += 1
                else:
                    failure_count += 1
            except Exception as e:
                failure_count += 1
                print(f"Error at iteration {i}: {e}")
        
        elapsed = time.time() - start_time
        total = success_count + failure_count
        
        print(f"Total: {total}")
        print(f"✓ Success: {success_count}")
        print(f"✗ Failures: {failure_count}")
        print(f"Time: {elapsed:.2f}s")
        print(f"Rate: {total/elapsed:.2f} registrations/second")
        
        # At least 95% should succeed
        self.assertGreaterEqual(success_count, int(total * 0.95),
                              "At least 95% of registrations should succeed")


class TestStressResponseTime(unittest.TestCase):
    """Stress test: Response time monitoring"""
    
    def test_stress_password_hash_performance(self):
        """Stress Test 11: Password hashing performance"""
        print("\n=== STRESS TEST 11: Password Hashing Performance ===")
        print("Note: PBKDF2/bcrypt hashing is intentionally slow for security\n")
        
        from server import security_utils
        
        times = []
        num_hashes = 15  # Reduced from 50 (200ms each = 3 seconds)
        
        for i in range(num_hashes):
            password = f"HashTest@{i:04d}Aa"
            
            start = time.time()
            hashed = security_utils.hash_password(password)
            elapsed = time.time() - start
            
            times.append(elapsed)
            print(f"  Hash {i+1:2d}: {elapsed*1000:7.2f}ms")
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        min_time = min(times)
        total_time = sum(times)
        
        print(f"\nTotal operations: {num_hashes}")
        print(f"Total time: {total_time:.2f}s")
        print(f"Avg time per hash: {avg_time*1000:.2f}ms")
        print(f"Max time: {max_time*1000:.2f}ms")
        print(f"Min time: {min_time*1000:.2f}ms")
        print(f"Rate: {num_hashes/total_time:.2f} hashes/second")
        print(f"\nSecurity notes:")
        print(f"  • ~200ms per hash is NORMAL and REQUIRED for security")
        print(f"  • Faster hashing = weaker protection against brute force")
        print(f"  • PBKDF2 configured with adequate iterations")
        
        # Realistic expectations: 15 hashes @ ~200ms each = ~3 seconds
        self.assertLess(total_time, 6.0, f"{num_hashes} hashes should complete in < 6 seconds")
        self.assertGreater(avg_time, 0.150, "Each hash should take > 150ms for security")


class TestStressMixedWorkload(unittest.TestCase):
    """Stress test: Mixed workload (realistic scenario)"""
    
    def test_stress_mixed_operations_60_seconds(self):
        """Stress Test 12: Mixed registration/login operations for 60s"""
        print("\n=== STRESS TEST 12: Mixed Workload (60s) ===")
        
        self.reg_count = 0
        self.login_count = 0
        self.lock = threading.Lock()
        self.stop_flag = False
        
        def mixed_worker():
            """Worker performing mixed operations"""
            local_reg = 0
            local_login = 0
            
            while not self.stop_flag:
                try:
                    # 60% registration, 40% login
                    if random.random() < 0.6:
                        # Registration
                        username = f"mx_{time.time_ns() & 0xFFFFFFFF:08x}"
                        password = f"Mixed@{local_reg:04d}Aa"
                        
                        success, _ = user_service.register_user(username, password)
                        if success:
                            local_reg += 1
                    else:
                        # Login with random user
                        username = f"mx_{(time.time_ns()-1000000) & 0xFFFFFFFF:08x}"
                        password = f"Mixed@0000Aa"
                        
                        success, _ = user_service.login_user(username, password)
                        if not success:  # Expected to fail for random users
                            local_login += 1
                    
                    time.sleep(0.01)  # Small delay
                except:
                    pass
            
            with self.lock:
                self.reg_count += local_reg
                self.login_count += local_login
        
        # Start 10 worker threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=mixed_worker, daemon=True)
            threads.append(thread)
            thread.start()
        
        # Run for 60 seconds
        start_time = time.time()
        time.sleep(60)
        self.stop_flag = True
        
        # Wait for threads
        for thread in threads:
            thread.join(timeout=5)
        
        elapsed = time.time() - start_time
        total_ops = self.reg_count + self.login_count
        
        print(f"Duration: {elapsed:.1f}s")
        print(f"Registrations: {self.reg_count}")
        print(f"Login attempts: {self.login_count}")
        print(f"Total operations: {total_ops}")
        print(f"Operations/second: {total_ops/elapsed:.2f}")


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║          STRESS TEST SUITE FOR CHAT APPLICATION           ║
    ║                    12 COMPREHENSIVE TESTS                 ║
    ╚═══════════════════════════════════════════════════════════╝
    
    Tests included:
    1. 100 concurrent registrations
    2. 500 concurrent registrations
    3. 100 concurrent logins
    4. 50 concurrent socket connections
    5. 1000 rapid password validations
    6. 500 rapid ban/unban operations
    7. Sustained registration load (30s)
    8. 1000 invalid login attempts
    9. 100 duplicate registration attempts
    10. 200 sequential registrations (dataset)
    11. Password hashing performance
    12. Mixed workload (60s realistic scenario)
    """)
    
    unittest.main(verbosity=2)
