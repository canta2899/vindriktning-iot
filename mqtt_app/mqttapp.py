from influxdb import InfluxDBClient
from secrets import token_urlsafe
import paho.mqtt.client as paho
from datetime import datetime           
from time import sleep
import requests as r
from requests.exceptions import HTTPError, ConnectionError, Timeout
import threading
import traceback
import signal 
import queue
import json
import time
import sys
import os

# Broker addr
BROKER = 'broker'

# Name of the subtopics for each sensor's topic
AVAILABILITY_NAME = 'availability'
STATE_NAME = 'state'

# Subscribing to all the subtopics of airsensor
TOPIC = 'airsensor/#' 

# Name of the measurement from the sensor 
MEASUREMENT = 'airquality'

# Database params 
INFLUX_DB_DATABASE = 'airquality'
INFLUX_DB_USER = os.environ['INFLUXDB_MQTT_USER'] 
INFLUX_DB_PASSWORD = os.environ['INFLUXDB_MQTT_PASSWORD']
INFLUX_DB_HOST = 'database'         
INFLUX_DB_PORT = 8086

# Broker params
BROKER_USER = os.environ['MOSQUITTO_USERNAME'] 
BROKER_PASSWORD = os.environ['MOSQUITTO_PASSWORD']

# Bot params
TELEGRAM_BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN'] 
TOKEN_ENDPOINT = 'http://logapp:5000/validatetoken'
NEW_TOKEN_ENDPOINT = 'http://logapp:5000/newtoken'
WHITELIST_ENDPOINT = 'http://logapp:5000/whitelist'
LOG_ENDPOINT = 'http://logapp:5000/logging'


"""

    A quick HTTP logger implementation that logs data to the
    logapp VINDRIKTNING monitoring tool api. 

"""

class Logger:

    def __init__(self, endpoint):

        """
            Uses and indipendent session to log data
        """

        self.e = endpoint
        self.s = r.Session()


    @staticmethod
    def __format(msg, level="INFO"):
        
        """
            Log message is sent as json 
        """

        return {
            "msg": f"{datetime.now()} : {level} : {msg}"
        }


    # Log levels
    
    def debug(self, msg):
        com = self.__format(msg, "DEBUG")
        self.log(com)

    def info(self, msg):
        com = self.__format(msg, "INFO")
        self.log(com)
    
    def warning(self, msg):
        com = self.__format(msg, "WARNING")
        self.log(com)

    def error(self, msg):
        com = self.__format(msg, "ERROR")
        self.log(com)

    def critical(self, msg):
        com = self.__format(msg, "CRITICAL")
        self.log(com)


    def log(self, com):
        
        """
            Logs with a post request to the given
            endpoint
        """

        try:
            self.s.post(self.e, json=com)
        except Exception as e:
            print(f"Unable to send request {com}")
            print(e)

# End class logger


"""
                                                                  
                  TELEGRAM BOT IMPLEMENTATION                     
                  ===========================                     
                                                                  
        The following class aims to provide the essentials        
        bot functionalities needed for the purpose of this        
        project without having to rely on external libs and       
                having to conform to their logic.                 
                                                                  
    USAGE                                                         
    =====                                                         
                                                                  
       1. The bot doesnt respond by default                       
                                                                  
       2. By sending `/token` the bot creates a new token         
          for the chat_id requesting                              
                                                                  
       3. With `/token invalid_token` nothing happens             
                                                                  
       3. After sending `/token valid_token` access is enabled    
                                                                  
       4. Commands available then are:                            
            - /status (list online sensors)                       
            - /info [sensor name] (check last known status)       
                                                                  
       You will receive notifications for quality changes         
                                                                  
                                                                  
    RUNNING THE BOT                                               
    ===============                                               
                                                                  
    The bot can be instantiated with                              
                                                                  
            b = Bot(YOUR_TOKEN)                                   
                                                                  
    And will start working after                                  
                                                                  
            b.run()                                               
                                                                             
                                                                  
    CALLBACK FUNCTIONS                                            
    ==================                                            
                                                                  
    Callbacks functions can be defined with                       
                                                                  
            b.on(message, callback_function)                      
                                                                  
    The callback function must respect the following definition   
                                                                  
            def callback_function(params, chat_id, answer)        
                # your logic                                      
                answer("A message", chat_id)                      
                                                                  
      where                                                       
         - [params] is a list of message words splitted by " "    
         - [chat_id] is the chat id of the sender                 
         - [answer] is a callback function which can be           
           used to reply to the sender                            
                                                                  
                                                                  
    PUSHING GLOBAL NOTIFICATIONS                                  
    ============================                                  
                                                                  
    The method                                                    
                                                                  
            b.push_notification(message)                           
                                                                  
    allows to push a notification message which will be sent      
    to all the users as soon as possible.                         
                                                                  
                                                                  
    STOPPING THE BOT                                              
    ================                                               
                                                                  
    In order to stop the bot you can run bot.stop(). The call     
    is blocking and might take some seconds in order to stop      
    the bot properly                                              
                                                                  

"""

class Bot:

    def __init__(self, token):
        
        self.TOKEN = token
        self.offset = 0
        self.timeout = 10
        self.polling_lock = threading.Lock()
        self.polling = True
        self.callbacks = dict()
        self.running_thread = None
        self.q = queue.Queue()
        self.max_retries = 30
        self.logging = Logger(LOG_ENDPOINT)
        self.s = r.Session()

        # Requests whitelist to the api
        self.whitelist = self.__get_whitelist()

    
    def __get_whitelist(self):
        try:
            whitelist = r.get(WHITELIST_ENDPOINT).json()
            return whitelist
        except Exception as e:
            logging.error("Couldn't get whitelist for telegram bot")

        return []



    def push_notification(self, msg):

        """
            Pushes notifications to the queue
            which is consumed by the polling
            thread
        """

        self.q.put(msg)
    

    def __get_next(self):

        """
            Helper function for __send_notification
            which gets the next element in the queue
            marking it as processed. If the queue
            is empty returns None, otherwise returns
            the message to be sent
        """

        try:
            msg = self.q.get_nowait()
            self.q.task_done()
            return msg
        except queue.Empty:
            return None


    def __send_notifications(self):
        
        """
            Sends every notification in the queue
        """

        msg = ""

        while msg is not None:
            msg = self.__get_next()
            if msg is not None:
                self.sendall(msg)

        self.logging.debug("All notifications sent")


    def on(self, msg, callback):

        """
            Binds the given callback function to
            the message
        """

        self.callbacks[msg] = callback 


    def send(self, msg, chat_id):

        """
            Sends a message to the given chat_id
        """

        self.s.post(
            f"https://api.telegram.org/bot{self.TOKEN}/sendMessage",
            data={
                "chat_id": chat_id,
                "text": msg
            }
        )


    def sendall(self, msg):

        """
            Sends a message to all the chat_ids 
        """

        for chatid in self.whitelist:
            self.send(msg, int(chatid))

    
    def __request_token_validation(self, chat_id, username, s_token):

        """
            Requests to the logapp api if the
            token for the user is valid
        """

        s_token = s_token.strip()
        
        # Requesting validation to the api
        validation = r.post(
            TOKEN_ENDPOINT,
            json={
                'chat_id': chat_id,
                'username': username,
                'token': s_token
            }
        )

        if validation.status_code == 200:
            self.logging.info(
                f"Chat id {chat_id} validated access"
            )
            self.send(
                "Great! You're ready to go.",
                chat_id
            )
            self.whitelist.append(s_token)
        else:
            self.logging.warning(
                f"Chat id {chat_id} failed "
                "to validate token: {e}"
            )
            self.send(
                "Oops, seems like that token "
                "is invalid. You can request "
                "a new one with /token", 
                chat_id
            )


    def __request_new_token(self, chat_id, username):
        newtoken = self.s.get(
            NEW_TOKEN_ENDPOINT,
            json={
                'chat_id': chat_id,
                'username': username
            }
        )
        if newtoken.status_code == 200:
            self.logging.info(
                f"User {username} made a new token request"
            )
            self.send(
                "The sensor status is top secret 🤫\n"
                "I made a token for you, send it with "
                "/token [YOUR_TOKEN] and I'll give you "
                "access 💪", chat_id
            )
        else:
            self.logging.info(
                f"Unable to produce token for the user {username}"
            )
            self.send(
                "Sorry, I couldn't make a new token for "
                "you 😭. Try again later", chat_id
            )



    def __parse_msg(self, msg):

        """
            Parses an incoming message by:
                
                - retrieving chatid, msg, user
                - splitting message by ' '
                - processing token request if msg is
                  '/token'
                - searching for a binded callback otherwise
        """

        # Extracting chat_id, splitting message by whitespaces

        try:
            chat_id = msg['message']['chat']['id']
            mlist = (msg['message']['text']).split(" ")
            username = msg['message']['chat']['username']
        except Exception as e:
            self.logging.error(
                f"Unable to parse params "
                f"on Telegram bot message: {e}"
            )
            return
        
        # If the message is a token request
        if mlist[0] == '/token':

            # If a token is specified
            if len(mlist) > 1:
                self.__request_token_validation(
                    chat_id,
                    username,
                    mlist[1]
                )
            
            else:
                self.__request_new_token(
                    chat_id,
                    username
                )

        else:
            
            # Otherwise if the message is not a token request

            # If the chat id is a white listed chat id
            if str(chat_id) in self.whitelist:
                    
                # If a callback is associated to the 
                # incoming message, executes callback

                if mlist[0] in self.callbacks.keys():
                    try:
                        self.callbacks[mlist[0]](
                                chat_id, 
                                mlist, 
                                self.send
                        )
                    except Exception as e:
                        self.logging.critical(
                            f"Exception on BOT callback "
                            f"on {mlist[0]}: {e}"
                        )
     

    def __get_updates(self):
        
        """
            Requests for updates on endpoint, then checks validity. 
            A block of updates is then parsed for each message

            Long polling caused connection problems and the with 
            the bot stopping to respond after a few hours of activity. 

            After intensive debugging it was clear that the polling
            thread was stuck on the POST request below (getUpdates
            endpoint). In order to prevent this issue, an internal
            timeout is set and exceptions are handled by reopening
            a new session in order to re-initiate the connection
        """

        self.logging.debug("Getting updates from telegram")

        try:

            up =  self.s.post(
                f"https://api.telegram.org/bot{self.TOKEN}/getUpdates",
                data = {
                    "offset": self.offset,
                    "timeout": 15
                },
                timeout=20
            ).json()

        except ValueError as e:
            self.logging.debug("Incomplete updates gotten, skipping...")
            return

        except HTTPError as e:
            self.logging.critical("Reinitiating bot connection after HTTPError")
            self.s = r.Session()
            return

        except ConnectionError as e:
            self.logging.critical("Reinitiating bot connection after ConnError")
            self.s = r.Session()
            return

        except Timeout as e:
            self.logging.critical("Reinitiating bot connection after Timeout")
            self.s = r.Session()
            return

        except Exception as e:
            self.logging.critical("Reinitiating bot connection after Timeout")
            self.s = r.Session()
            return

        self.logging.debug("Updates gotten")

        if not up['ok'] or not up['result']: 
            return

        # Parsing every update
        # https://core.telegram.org/bots/api#getupdates

        _ofst = 0

        self.logging.debug("Processing incoming messages")
        for msg in up['result']:
            self.logging.debug(f"Processing message {msg}")
            self.logging.debug("Parsing updates")
            self.__parse_msg(msg)
            self.logging.debug("Done parsing updates")

            _ofst = msg['update_id'] + 1

        self.logging.debug("Done Processing incoming messages")

        self.offset = _ofst
    

    def __run(self):

        """
            Runs the telegram bot long polling for updates. 
            If the polling causes exceptions MAX_RETRIES times
            in a row then the polling stops. 

            After each polling, enqueued notifications are sent
        """

        while self.polling:
            try:
                self.__get_updates()
                self.__send_notifications()
            finally:
                sleep(0.2)  # Sleeps 200 ms before next round


    def stop(self):

        """
            Stops the bot correctly
        """
       
        # Waits for the queue to join
        self.logging.critical("Stopping the telegram bot")
        q.join()

        # Sets polling to false in order to stop
        with self.polling_lock:
            self.polling = False

        # joins the polling thread
        self.running_thread.join()


    def run(self):
        
        """
            Runs the bot in a separate thread
        """

        self.running_thread = threading.Thread(
            target=self.__run, 
            args=()
        )
        self.running_thread.start() 

# End Bot Class



#         +----------------+
#         |                |
#         |   FUNCTIONS    |
#         |                |
#         +----------------+


def status_callback(chat_id, params, answer):

    """
        Handles /status command sent from bot
    """

    tmp_list = sensor_list.copy()

    # If there's no known sensor
    if len(tmp_list) == 0:
        answer(
            "You have no sensors registered to the network", 
            chat_id
        )
        return

    # If it's just /status sends actual status for each known sensor
    if len(params) == 1:
        global_msg = ""
        for sensor in tmp_list.values():
            global_msg += (
                f"Your sensor {sensor['name']} "
                f"is {sensor['status']}\n\n"
            )
        answer(global_msg, chat_id)
        return

    # Otherwise, sends actual status for the requested sensor
    for sensor in tmp_list.values():
        if sensor['name'] == params[1]:
            msg = ( 
                f"The sensor {sensor['name']} "
                f"is {sensor['status']}"
            )
            answer(msg, chat_id)
            return

    # Otherwise the requested sensor doesn't exist
    answer("Seems like there's no sensor with that name", chat_id)
   

def info_callback(chat_id, params, answer):

    """
        Handles /info command sent from bot
    """

    # If no sensor name is specified, requests for one and returns
    if len(params) == 1:
        answer(
            "Please specify the sensor name. "
            "You can list them with /status", 
            chat_id
        )
        return

    # Extracts sensor name
    name = params[1]

    tmp_list = sensor_list.copy()

    # Searches for the sensor
    for sensor in tmp_list.values():

        # If the sensor is found, sends updates. Then returns
        if sensor['name'] == name:
            quality = ""
            if sensor['quality'] == 2:
                quality = "🔴"
            elif sensor['quality'] == 1:
                quality = "🟠"
            else:
                quality = "🟢"
            answer(
                f"Sensor Name: {name}\n\n"
                f"Quality: {quality}\n\n"
                f"Value: {sensor['pm25']}", 
                chat_id
            )
            return

    # Otherwise, no sensor is found
    answer("There's no sensor with that name", chat_id)


def declare_sensor_status(uid, status):

    """
        Registers a sensor status (online or offline). 
        If the sensor is not known, creates an entry 
        in the sensor collection
    """

    global sensor_list

    if uid not in sensor_list.keys():

        # entry with invalid params 
        sensor_list[uid] = {
                'status': status,
                'pm25': -1,
                'quality': -1,
                'name' : ''
        }

    # Matching status
    sensor_list[uid]['status'] = status 


def update_values(uid, pm25, quality, name, ip):

    """
        Updates last known sensor update
        
        [uid]     :  sensor id (ie VINDRIKTNING-54F9AE)
        [pm25]    :  air quaity measured
        [quality] :  quality class (0,1,2)
        [name]    :  sensor name 
    """

    global sensor_list

    logging.debug("Updating values")

    # If the sensor is not known, it's registered as an online sensor
    if uid not in sensor_list.keys():
        declare_sensor_status(uid, "online")

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
            b.push_notification(
                f"🟢 The air quality in {name} is getting good"
            )
        elif quality == 1:
            b.push_notification(
                f"🟠 The air quality in {name} is getting unpleasant"
            )
        else:
            b.push_notification(
                f"🔴 The air quality in {name} is getting unacceptable"
            )
        logging.info(f"Sensor {name} ({ip}) triggered a notification")


def close_all():
    
    """
        Closes mqtt subscriber, db client and bot.
        Requires more than 10s so timeout should be higher
        on docker compose stop

        docker compose stop -t timeout
    """

    mqtt_client.loop_stop()
    dbclient.close()
    b.stop()
    

def sigint_handler(signal, frame):

    """
        Handles the sigint ISR
    """

    close_all()
    logging.warning("Closing after receiving SIGINT")


def sigterm_handler(signal, frame):

    """
        Handles the sigterm ISR
    """

    # global running
    # running = False # Stopping the program
    close_all()
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

    if sensor_subtopic == AVAILABILITY_NAME and msg == "offline":
        logging.warning(
            f"Sensor {sensor_name} disconnected from the network."
        )
        declare_sensor_status(sensor_name, "offline")
        return

    # If the topic is about availability and message is online, it means
    # that the sensor is online

    if sensor_subtopic == AVAILABILITY_NAME and msg == "online":
        logging.info(
            f"Sensor {sensor_name} connected to the network"
        ) 
        declare_sensor_status(sensor_name, "online")
        return


    # If the topic is about state the message 
    # should be a json with updates about the sensor state

    if sensor_subtopic == STATE_NAME:
        try:
            # JSON is loaded from string msg
            msg = json.loads(msg)        

            # Writing data to the DB
            dbclient.write_points([{
                'measurement': MEASUREMENT,
                'time': datetime.now(),
                'fields': {
                    "pm25": msg['pm25']    
                },
                'tags': {
                    'quality': msg['quality'],
                    'name': msg['name'],
                    'ip': msg['ip']
                }
            }])

            # Updating last known sensor values (triggers notifications)
            update_values(
                sensor_name, 
                msg['pm25'], 
                msg['quality'], 
                msg['name'], 
                msg['ip']
            )
        except Exception as e:
            logging.error(
                f"Couldn't perform update query for "
                f"{sensor_name} with msg: {msg}. If "
                f"your container just started it might be ok"
            )




#             +----------------+
#             |                |
#             |    RUNNING     |
#             |                |
#             +----------------+


running = True          # program starts in running mode
sensor_list = dict()    # sensor_list is empty at start


# Configuring signal handlers for SIGINT (Ctrl + C)
# and for SIGTERM (sent by docker on container stop request)

signal.signal(signal.SIGINT, sigint_handler)
signal.signal(signal.SIGTERM, sigterm_handler)


# Offline logger just in case it's needed
# logging.basicConfig(
#     filename=LOG_FILE, 
#     level=logging.INFO,
#     format='%(asctime)s : %(levelname)s : %(message)s'
# )
# 

# Setting up the REST logger

logging = Logger(LOG_ENDPOINT)


# Configuring the telegram bot

b = Bot(TELEGRAM_BOT_TOKEN)
b.on('/status', status_callback)
b.on('/info', info_callback)
b.run()

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


# Configuring the influx db client and connection to the DB

try:
    dbclient = InfluxDBClient(
            INFLUX_DB_HOST, 
            INFLUX_DB_PORT, 
            INFLUX_DB_USER, 
            INFLUX_DB_PASSWORD, 
            INFLUX_DB_DATABASE
    )

    dbclient.switch_database(INFLUX_DB_DATABASE)
except Exception as e:
    logging.critical(
        "Unable to perform influxDB connection. Shutting down"
    )
    sys.exit(1)


# Configuration is done

logging.info("Configuration done, starting main loop")


# Runs forever until stop occours

mqtt_client.loop_forever() 
