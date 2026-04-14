import os
import threading
import mysql.connector
from config import DB_CONFIG

db_ban = threading.Lock()

# def ensure_ban_file_exists():
#     if not os.path.exists(BANS_FILE): open(BANS_FILE, 'w').close()

def is_banned(username):
    # with open(BANS_FILE, 'r') as f:
    #     return username in [line.strip() for line in f.readlines()]
    with db_ban:
        conn = None
        cursor = None
        try:
            conn = mysql.connector.connect(**DB_CONFIG,connect_timeout=2)
            cursor = conn.cursor()
            query = "SELECT banned FROM account_user WHERE username = %s"
            cursor.execute(query, (username,))
            result = cursor.fetchone()
            return result[0] if result else False
        except mysql.connector.Error as err:
            print(f"[-] DB error while checking ban status for user '{username}': {err}")
            return False
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

def ban_user(username):
    # with open(BANS_FILE, 'a') as f: f.write(f"{username}\n")
    with db_ban:
        conn = None
        cursor = None
        try:
            conn = mysql.connector.connect(**DB_CONFIG,connect_timeout=2)
            cursor = conn.cursor()
            query = "UPDATE account_user SET banned = TRUE WHERE username = %s"
            cursor.execute(query, (username,))
            conn.commit()
            print(f"User {username} banned successfully in DB.")
        except mysql.connector.Error as err:
            print(f"[-] DB error while banning user '{username}': {err}")
        except Exception as e:
            print(f"[-] Unexpected error while banning user '{username}': {e}")
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
        

def unban_user(username):
    # with open(BANS_FILE, 'r') as f:
    #     lines = f.readlines()
    # with open(BANS_FILE, 'w') as f:
    #     for line in lines:
    #         if line.strip() != username:
    #             f.write(line)
    with db_ban:
        conn = None
        cursor = None
        try:
            conn = mysql.connector.connect(**DB_CONFIG,connect_timeout=2)
            cursor = conn.cursor()
            query = "UPDATE account_user SET banned = FALSE WHERE username = %s"
            cursor.execute(query, (username,))
            conn.commit()
            print(f"User {username} unbanned successfully in DB.")
        except mysql.connector.Error as err:
            print(f"[-] DB error while unbanning user '{username}': {err}")
        except Exception as e:
            print(f"[-] Unexpected error while unbanning user '{username}': {e}")
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()