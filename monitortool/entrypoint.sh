set -e

sqlite3 /app/appdb.db << EOF
insert into user(name, password) values ('$AUTH_USERNAME', '$AUTH_USERPASS')
EOF

exec "$@"
