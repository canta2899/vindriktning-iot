FROM eclipse-mosquitto

ADD ./config/mosquitto.conf /mosquitto/config
ADD ./broker-entrypoint.sh /

ENTRYPOINT ["sh", "./broker-entrypoint.sh"]

CMD ["/usr/sbin/mosquitto", "-c", "/mosquitto/config/mosquitto.conf"]
