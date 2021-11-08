[![License](http://img.shields.io/:license-mit-blue.svg?style=flat-square)](http://badges.mit-license.org)

# Ikea VINDRIKTNING sensor app

![Vindriktning](report/img/vindriktning.jpeg)

The project is under development and proposes an IoT integration over a cheap air quality sensor named [VINDRIKTNING](https://www.ikea.com/it/it/p/vindriktning-sensore-della-qualita-dellaria-80515910/), sold by Ikea. The idea is inspired by the [following](https://github.com/Hypfer/esp8266-vindriktning-particle-sensor) project, developed by Hypfer.

## How it works

### Customize and configure your vindriktning units

You'll have to flash the custom firmware on each unit, then power it up and connect to each sensor (exposed as Soft Access Point) in order to configure WiFi and MQTT parameters.

### Define variables

First, edit the `proxy/domain.ext` file by adding the **alt_names** you want to include in your certificate.

Then, cd to the root directory of the repository and run 

```bash
./configure
```

in order to

1. Create `env` file containing all the needed environment variables
2. Create the certificates needed

### Build and run

In the root directory of the repository, run

```bash
docker-compose build
```

Then, you just have to run

```bash
docker-compose up
```

If your sensors are configured properly they should connect to the MQTT broker in a few seconds, then data logging will start.

You will be able to access the monitortool by navigating to the previously configured domain. If you used the `gen-certs` script you may have to mark the certificate as valid too. 

You can access the monitortool with the username and password you provided in the `.env` file.
