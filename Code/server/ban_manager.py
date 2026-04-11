import os
from config import BANS_FILE

def ensure_ban_file_exists():
    if not os.path.exists(BANS_FILE): open(BANS_FILE, 'w').close()

def is_banned(username):
    with open(BANS_FILE, 'r') as f:
        return username in [line.strip() for line in f.readlines()]

def ban_user(username):
    with open(BANS_FILE, 'a') as f: f.write(f"{username}\n")

def unban_user(username):
    with open(BANS_FILE, 'r') as f:
        lines = f.readlines()
    with open(BANS_FILE, 'w') as f:
        for line in lines:
            if line.strip() != username:
                f.write(line)