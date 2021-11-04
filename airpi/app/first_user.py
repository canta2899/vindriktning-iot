import sqlite3
from passlib.hash import pbkdf2_sha256
import os
import sys

USERNAME = os.environ['AUTH_USERNAME']
PASSWORD = os.environ['AUTH_USERPASS']
DB = '/app/appdb.db'

conn = sqlite3.connect(DB)
c = conn.cursor()

try:
    c.execute('INSERT INTO user(name, password, is_admin) VALUES (?,?,1)', (USERNAME, pbkdf2_sha256.hash(PASSWORD)))
    conn.commit()
except Exception as e:
    conn.rollback()
finally:
    conn.close()

sys.exit(0)
