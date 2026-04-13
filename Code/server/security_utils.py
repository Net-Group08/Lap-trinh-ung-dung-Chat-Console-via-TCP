import bcrypt
import re
from cryptography.fernet import Fernet
from config import SECRET_KEY


def checkpassword_strength(password):
    if len(password) < 8 or len(password) > 29:
        return False , "Password must be between 8 and 29 characters long."
    if not any(char.isalpha() for char in password):
        return False, "Password must contain at least one letter."
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter."
    if not any(char.isdigit() for char in password):
        return False, "Password must contain at least one digit."
    if not any(char in "!@#$%^&*()-_=+[]{}|;:,.<>?/" for char in password):
        return False, "Password must contain at least one special character."

    return True, None

def hash_password(plain_password):
    return bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt(rounds=12))

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def encrypt_data(data):
    fernet = Fernet(SECRET_KEY)
    return fernet.encrypt(data.encode('utf-8'))

def decrypt_data(encrypted_data):
    fernet = Fernet(SECRET_KEY)
    return fernet.decrypt(encrypted_data).decode('utf-8')