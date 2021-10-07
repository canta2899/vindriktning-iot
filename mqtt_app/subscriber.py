import paho.mqtt.client as mqtt #import the client
import signal
import sys

# callback function
def process_message(client, userdata, message):  
    msg = json.loads(message.payload.decode("utf-8"))
    print("Message on topic " + message.topic + " with retain flag: " + message.retain)
    print(json.dumps(msg, indent=4, sort_keys=True))

def signal_handler(sig, frame):
		global client, is_connected
		print('Closing...')
		if is_connected:
			client.disconnect()
			client.loop_stop()
		sys.exit(0)

is_connected=False
qos=2

signal.signal(signal.SIGINT, signal_handler)

broker_address="broker"

# Create client
client = mqtt.Client(client_id=sub_id) 

# Assign callback function
client.on_message = process_message

# Connect to broker
client.connect("broker",1883,60)

is_connected=True

# Subscriber to topic
client.subscribe('airsensor',qos)
client.subscribe('airsensor/+',qos)

# Run loop
client.loop_forever()
