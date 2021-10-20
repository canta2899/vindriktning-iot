# https://github.com/thelebster/example-mosquitto-simple-auth-docker/blob/master/docker-entrypoint.sh

set -e

# Fix write permissions for mosquitto directories
chown --no-dereference --recursive mosquitto /mosquitto/log
chown --no-dereference --recursive mosquitto /mosquitto/data

mkdir -p /var/run/mosquitto \
  && chown --no-dereference --recursive mosquitto /var/run/mosquitto

if ( [ -z "${MOSQUITTO_USERNAME}" ] || [ -z "${MOSQUITTO_PASSWORD}" ] ); then
  echo "MOSQUITTO_USERNAME or MOSQUITTO_PASSWORD not defined"
  exit 1
fi

# create mosquitto passwordfile
touch passwordfile
mosquitto_passwd -b passwordfile $MOSQUITTO_USERNAME $MOSQUITTO_PASSWORD

exec "$@"





# Test
# Subscribe to topic.
# mosquitto_sub -h localhost -t test -u "mosquitto" -P "mosquitto"

# Publish a message.
# mosquitto_pub -h localhost -t test -m "hello." -u "mosquitto" -P "mosquitto"
