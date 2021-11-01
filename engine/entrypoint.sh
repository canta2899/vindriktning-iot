set -e

mkdir -p /log
touch /log/logfile.log
cp /log/logfile.log /log/report.log
cat /dev/null > /log/logfile.log
exec "$@"
