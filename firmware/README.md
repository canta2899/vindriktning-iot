# Sensor firmware

This directory contains a PlatformIO project with the custom firmware that needs to be uploaded to the sensors in order to allow them to connect to the network and send regular messages to the MQTT broker. The code is heavily inspired by [Hypfer's work](https://github.com/Hypfer/esp8266-vindriktning-particle-sensor).

The thirds party libreries you'll need to install are:

- WiFi Manager
- PubSubClient
- ArduinoJSON

After the firmware had been flashed for the first time, you can run

```bash
pio run --target upload --upload-port [MCUaddress]
```

In order to apply updates remotely.
