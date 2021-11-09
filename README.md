[![License](http://img.shields.io/:license-mit-blue.svg?style=flat-square)](http://badges.mit-license.org)

# Ikea VINDRIKTNING sensor app

![Vindriktning](report/img/vindriktning.jpeg)

The project proposes an IoT integration over a cheap air quality sensor named [VINDRIKTNING](https://www.ikea.com/it/it/p/vindriktning-sensore-della-qualita-dellaria-80515910/), sold by Ikea. The idea is inspired by the [following](https://github.com/Hypfer/esp8266-vindriktning-particle-sensor) project, developed by Hypfer.

## Repository Structure

The repository contains a folder for each one of the services implemented.

- `firmware` contains the **PlatformIO Project** of the custom ESP8266 firmware for the sensor units
- `broker` contains the Dockerfile and other configuration files in order to setup the MQTT broker container
- `influxdb` contains the Dockerfile and the initialization InfluxQL script for the InfluxDB container
- `airpi` contains the Dockerfile and the app folder for the Flask API implemented
- `proxy` contains the Dockerfile and the configuration files in order to setup the **nginx** container for the HTTPs reverse proxy
- `report` contains the full report and assets
- `configuration` provides a shell script in order to configure the project before building
- `docker-compose.yml` the docker-compose file used to organize the multi-container stack

## Requirements

### Hardware

- VINDRIKTNING by Ikea
- D1 Mini by Wemos
- USB-C to USB Cable (one for each sensor unit)
- Dupont Cables
- Soldering Iron
- PH0 Screwdriver

### Software

Since the proposed solution is completely based on Docker containers except for the sensor's firmware, you'll only need:

- Docker Engine running on a supported architecture
- PlatformIO in order to build the custom VINDRIKTNING firmware (check out the [VSCode Extension](https://platformio.org/install/ide?install=vscode))

## Usage Guide

### Customize and configure your VINDRIKTNING units

You'll have to flash the custom firmware on each unit before powering it up. You'll then be able to connect to each sensor (exposed as Soft Access Point) in order to configure WiFi and MQTT parameters.

### Configure domain (if needed)

First, edit the `domain.ext` file inside the `proxy` directory by adding the **alt_names** you want to include in your certificate. The standard configuration is made for **localhost only**, but you can edit the file and make it like the following:

```
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = my-domain.com
DNS.2 = localhost
```

#### ⚠️  Note ⚠️

In case you want to use **multiple** domains, entering all the variants inside the `domain.ext` file won't be enough. You'll also have to customize the `default.conf` file in the `proxy` directory in order to configure redirection for each `server_name` on the reverse proxy. Here's an example that matches the previous `ext` file:

```

server {
	listen 443 ssl;


	ssl_certificate /certificates/domain.crt;
	ssl_certificate_key /certificates/domain.key;

	# listens for both domains on https
	server_name localhost my-domain.com;


	location / {

	   proxy_pass http://airpi:5000/;
	   proxy_set_header Host $host;
	   proxy_set_header X-Real-IP $remote_addr;
	   proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
	   proxy_set_header X-Forwarded-Host $host;
	   proxy_set_header X-Forwarded-Port $server_port;

	   # Define the maximum file size on file uploads
	   client_max_body_size 5M;
	}


}

server {
	listen 80;

	# redirection for localhost
	server_name localhost;

	return 302 https://$server_name$request_uri;
}

server {
	listen 80;

	# redirection for my domain
	server_name mydomain.com;

	return 302 https://$server_name$request_uri;
}

``` 

### Build and run

Locate inside the root directory of the repository and run 

```bash
./configure
```

in order to (according to your choice):

1. Create the `env` file containing all the needed environment variables
2. Create the certificates needed
3. Both the previous options

In order to build the container images, run:

```bash
docker-compose build
```

You can, then, start the containers by running:

```bash
docker-compose up
```

If your sensors are configured properly they should connect to the MQTT broker in a few seconds, then data logging will start. You can of course add other sensors later on.

You will be able to access the monitortool with the username and password you provided during the configuration by navigating to the previously configured domain. If you generated the certificates with the script provided you may have to mark them as valid. 

