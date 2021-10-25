set -e
cp /log/logfile.log /log/report.log
cat /dev/null > /log/logfile.log
exec "$@"
