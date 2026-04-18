from server import security_utils
import mysql.connector
from config import DB_CONFIG
import threading

temporary_memory = {}
db_lock = threading.Lock()
    
def store_temp_password(username, hashed_password):
    with db_lock:
        if username in temporary_memory:
                return False, "Username already exists."
        temporary_memory[username] = hashed_password
        return True, "Temporary password stored successfully."
    
def receive_temp_password(username):
    with db_lock:
        return temporary_memory.get(username, None)
    
def check_user_exists(username):
        conn = None
        cursor = None
        try:
            conn = mysql.connector.connect(**DB_CONFIG,connect_timeout=2)
            cursor = conn.cursor()
            query = "SELECT COUNT(*) FROM account_user WHERE username = %s"
            cursor.execute(query, (username,))
            result = cursor.fetchone()
            return result[0] > 0
        except mysql.connector.Error as err:
            print(f"[-] DB error while checking existence of user '{username}': {err}")
            return False
        except Exception as e:
            print(f"[-] Unexpected error while checking existence of user '{username}': {e}")
            return False
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
        
def register_user( username, plain_password):
    print(f"[~] Attempting to register user: {username}")

    is_strong, msg = security_utils.checkpassword_strength(plain_password)
    if not is_strong:
        print("[-] Password does not meet strength requirements.")
        return False, msg
    
    hashed_password = security_utils.hash_password(plain_password).decode('utf-8')

    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG,connect_timeout=2)
        cursor = conn.cursor()
        query = "INSERT INTO account_user (username, password) VALUES (%s, %s)"
        cursor.execute(query, (username, hashed_password))
        conn.commit()
        print(f"[~] User {username} registered successfully.")
        return True, "User registered successfully."
    except mysql.connector.IntegrityError as err:
        print(f"[-] Username '{username}' already taken in DB: {err}")
        return False, "Username already taken."
    except mysql.connector.Error as err:
        success, msg = store_temp_password(username, hashed_password)
        if success:
            print(f"[~] User registered in memory. DB error: {err}")
        else:
            print("[-] Registration rejected (in-memory fallback).")
        return success, msg
    except Exception as e:
        return False, f"Database connection error: {e}"
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
    
def login_user( username, plain_password):
    print(f"[~] Attempting to log in user: {username}")

    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG,connect_timeout=2)
        cursor = conn.cursor()
        query = "SELECT password FROM account_user WHERE username = %s"
        cursor.execute(query, (username,))
        result = cursor.fetchone()
        if result and security_utils.verify_password(plain_password, result[0]):
            return True, "Login successful."
        else:
            return False, "Invalid username or password."
    except mysql.connector.Error as err:
        if conn is None:
            stored_hash = receive_temp_password(username)
            if stored_hash and security_utils.verify_password(plain_password, stored_hash):
                return True, "Login successful (from temporary memory)."
            else:
                return False, "Invalid username or password (and DB is down)."
        return False, f"Database error: {err}"
    except Exception as e:
        return False, f"Database connection error: {e}"
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def history_log(username, action):
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG,connect_timeout=2)
        cursor = conn.cursor()
        query = "INSERT INTO history_log (username, action) VALUES (%s, %s)"
        cursor.execute(query, (username, action))
        conn.commit()
    except mysql.connector.Error as err:
        print(f"[-] DB error while logging history for user '{username}': {err}")
    except Exception as e:
        print(f"[-] Unexpected error while logging history for user '{username}': {e}")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()