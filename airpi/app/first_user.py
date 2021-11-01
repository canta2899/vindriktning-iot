import sqlite3
from passlib.hash import pbkdf2_sha256
import os
import sys

username = os.environ['AUTH_USERNAME']
password = os.environ['AUTH_USERPASS']

conn = sqlite3.connect('/app/appdb.db')
c = conn.cursor()

c.execute('INSERT INTO user(name, password, is_admin) VALUES (?,?,1)', (username, pbkdf2_sha256.hash(password)))
conn.commit()
conn.close()

sys.exit(0)
