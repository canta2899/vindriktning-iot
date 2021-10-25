import paho.mqtt.client as paho
import requests as r
from requests import ConnectionError
import logging
import signal 
import time
import json
import sys
import os


#Log file path
LOG_FILE = '/log/logfile.log'

# Name of the measurement from the sensor 
MEASUREMENT = 'airquality'

# Broker params
BROKER = 'broker'
STATE_NAME = 'state'
TOPIC = 'airsensor/#' 


AUTH_APPNAME=os.environ['AUTH_APPNAME']
AUTH_PASS=os.environ['AUTH_APPPASS']

BROKER_USER = os.environ['MOSQUITTO_USERNAME'] 
BROKER_PASSWORD = os.environ['MOSQUITTO_PASSWORD']
SENSOR_STATUS_ENDPOINT = os.environ['SENSOR_STATUS_ENDPOINT']
DATA_ENDPOINT = os.environ['DATA_ENDPOINT']
NOTIFICATION_ENDPOINT = os.environ['NOTIFICATION_ENDPOINT']

# Helper class in order to make token requests easier
class ApiComm:

    AUTH_ENDPOINT = os.environ['AUTH_ENDPOINT']

    def __init__(self, name, key):
        self.AUTH_APPNAME = name
        self.AUTH_PASS = key
        self.session = r.Session()
        self.__getAccessToken()

    def __getAccessToken(self):

        """
            Requests a new access token
        """
        
        try:
            request = r.post(self.AUTH_ENDPOINT, headers={
                'appName': self.AUTH_APPNAME,
                'secret': self.AUTH_PASS
            })
        except ConnectionError as e:
            logging.error("Connection error happened while requesting access token. Sleeping 10 seconds")
            time.sleep(10)
        except Exception as e:
            logging.error(f"Couldn't get access token: {e}")
            return False 

        if request.status_code == 401:
            raise Exception("Unable to authenticate")
        resp = request.json()
        token = resp['access_token']
        self.session.headers.update({'Authorization': f'Bearer {token}'})
        return True 

    def makerequest(self, endpoint, msg):

        """ 
            Performs a request and eventually requests a new access token
            if 401 is thrown. If request doesn't return 200 the method
            returns False. Otherwise True
        """
        
        try:
            res = self.session.post(endpoint, json=msg) 
            if res.status_code == 401:
                if self.__getAccessToken():
                    res = self.session.post(self.DATA_ENDPOINT, json=msg)
                    if res.status_code == 200:
                        return True 
        except ConnectionError as e:
            logging.critical(f"Connection error happened while performing request {msg} to {endpoint}")
        except Exception as e:
            logging.critical(f"Unable to send {msg} to {endpoint}: {e}")

        return False
             

def declare_sensor_status(uid, name, status):

    """
        Registers a sensor status (online or offline). 
        If the sensor is not known, creates an entry 
        in the sensor collection
    """
    msg = {
        'uid': uid,
        'status': status, 
        'name': name
    }

    if not comm.makerequest(SENSOR_STATUS_ENDPOINT, msg):
        logging.critical("Couldn't perform status request. Skipping...")



def update_values(uid, pm25, quality, name, ip):

    """
        Updates last known sensor update
        
        [uid]     :  sensor id (ie VINDRIKTNING-54F9AE)
        [pm25]    :  air quaity measured
        [quality] :  quality class (0,1,2)
        [name]    :  sensor name 
        [ip]      :  the ip of the sensor in the local network
    """

    global sensor_list


    # If the sensor is not known, it's registered as an online sensor
    if uid not in sensor_list.keys():

        # entry with invalid params 
        sensor_list[uid] = {
                'pm25': -1,
                'quality': -1,
                'name' : ''
        }

    # The params are updated 
    actual_quality = sensor_list[uid]['quality']
    sensor_list[uid]['pm25'] = pm25
    sensor_list[uid]['quality'] = quality
    sensor_list[uid]['name'] = name


    # If quality differs from the previous one and a telegram bot is used
    # then a notification is pushed

    if actual_quality != quality:
        logging.debug("Pushing notification")
        if quality == 0: 
            msg = f"🟢 The air quality in {name} is getting good"
        elif quality == 1:
            msg = f"🟠 The air quality in {name} is getting unpleasant"
        else:
            msg = f"🔴 The air quality in {name} is getting unacceptable"

        logging.info(f"Sensor {name} ({ip}) is triggering a notification")

        # Triggers a notification on the api 
        if not comm.makerequest(NOTIFICATION_ENDPOINT, {'msg': msg}):
            logging.critical("Couldn't perform notification request. Skipping...")
        
            

def sigint_handler(signal, frame):

    """
        Handles the sigint ISR
    """

    mqtt_client.loop_stop()
    logging.warning("Closing after receiving SIGINT")


def sigterm_handler(signal, frame):

    """
        Handles the sigterm ISR
    """

    mqtt_client.loop_stop()
    logging.warning("Closing after receiving SIGTERM")


def on_message(client, userdata, message):

    """
        MQTT Callback which defines the main routine 
        when a message on the subscribed topic is 
        received. In this case, topic is airsensor/# 
        so every subtopic's message will be received too
    """

    try:
        # Splits the topic
        topic = message.topic.split("/")

        # Decodes the message
        msg = message.payload.decode("utf-8") 

        # Extracts sensor UID and subtopic name
        sensor_name = topic[1]
        sensor_subtopic = topic[-1]
    except Exception as e:
        logging.warning(
            f"Received invalid message on {'/'.join(topic)}"
        )
        return


    # If the topic is about availability and 
    # message is offline, it means that the 
    # sensor has gone offline

    if sensor_subtopic == "online":
        logging.warning(
            f"{msg} connected to the network."
        )
        declare_sensor_status(sensor_name, msg, "online")
        return

    # If the topic is about availability and message is online, it means
    # that the sensor is online

    if sensor_subtopic == "offline":
        logging.info(
            f"{msg}  disconnected from the network"
        ) 
        declare_sensor_status(sensor_name, msg, "offline")
        return


    # If the topic is about state the message 
    # should be a json with updates about the sensor state

    if sensor_subtopic == STATE_NAME:
        try:
            # JSON is loaded from string msg
            msg = json.loads(msg)        

            output = {
                'measurement': MEASUREMENT,
                # 'time': int(time()),
                'fields': {
                    "pm25": msg['pm25']    
                },
                'tags': {
                    'quality': msg['quality'],
                    'name': msg['name'],
                    'ip': msg['ip']
                }
            }

            # Sending data
            if not comm.makerequest(DATA_ENDPOINT, output):
                logging.critical("Couldn't post to data endpoint. Skipping...")

            # Updating last known sensor values (triggers notifications)
            update_values(
                sensor_name, 
                msg['pm25'], 
                msg['quality'], 
                msg['name'], 
                msg['ip']
            )
        except Exception as e:
            import traceback    
            logging.error(
                f"Couldn't perform update query for "
                f"{sensor_name} with msg: {msg}. If "
                f"{traceback.format_exc()}"
            )


logging.basicConfig(
    filename=LOG_FILE, 
    level=logging.INFO,
    format='%(asctime)s : %(levelname)s : %(message)s'
)

try:
    comm = ApiComm(AUTH_APPNAME, AUTH_PASS)
except Exception as e:
    logging.critical("Can't authenticate to the api. Closing...")
    sys.exit(1)

sensor_list = dict()    # sensor_list is empty at start


# Configuring signal handlers for SIGINT (Ctrl + C)
# and for SIGTERM (sent by docker on container stop request)

signal.signal(signal.SIGINT, sigint_handler)
signal.signal(signal.SIGTERM, sigterm_handler)


# Configuring the mqtt client with connection to the broker
try:
    mqtt_client = paho.Client() 
    mqtt_client.username_pw_set(BROKER_USER, BROKER_PASSWORD)
    mqtt_client.on_message = on_message
    mqtt_client.connect(BROKER)
    mqtt_client.subscribe(TOPIC)
except Exception as e:
    logging.critical(e)
    logging.critical("Unble to setup MQTT client. Shutting down")
    sys.exit(1)


logging.info("Configuration done, starting main loop")


# Runs forever until stop occours
mqtt_client.loop_forever() 
