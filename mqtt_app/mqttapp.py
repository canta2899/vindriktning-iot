import paho.mqtt.client as paho
import time
import sys
import datetime
import time
broker="broker"  #host name
topic="airsensor/test" #topic name
        
def on_message(client, userdata, message):
    with open("log.txt", "a") as f:
        f.write("received: " + str(message.payload.decode("utf-8")))
        f.write("\n\n\n")
    
client= paho.Client() #create client object 
client.username_pw_set("mosquitto", "homepass")
client.on_message=on_message
   
print("connecting to broker host",broker)
client.connect(broker)#connection establishment with broker
print("subscribing begins here")    
client.subscribe(topic)#subscribe topic test

while 1:
    try:
        client.loop_forever() #contineously checking for message 
    except KeyboardInterrupt:
        print("Closing...")
        break
