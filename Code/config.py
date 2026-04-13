from mysql.connector import pooling

HOST = "127.0.0.1"
PORT = 5555

ADMIN_PASS = 'adminpass'

BANS_FILE = 'bans.txt'

DB_CONFIG = {
    'host': '127.0.0.1',
    'port': '3306',
    'user': 'root',
    'password': '123456',
    'database': 'user_db'

}

# dp_pool = pooling.MySQLConnectionPool(
#     pool_name="mypool",
#     pool_size=32, 
#     pool_reset_session=True,
#     **DB_CONFIG
# )

SECRET_KEY = b'yMvbRItLZcDbXQWwvJwULE8r4PdnEo-8mkFtbmpJicg='