/*

ABOUT OTA UPDATE
================

  - Examples: https://github.com/espressif/arduino-esp32/tree/master/libraries/ArduinoOTA
  - Docs: https://docs.platformio.org/en/latest/platforms/espressif32.html#over-the-air-ota-update
  - Command: pio run --target upload --upload-port MCUaddress
  - The password must be saved in the platformio.ini at the voice upload_flags and the subvoice --auth

CREDITS
=======

This code was heavily inspired by Hypfer: https://github.com/Hypfer/esp8266-vindriktning-particle-sensor
*/

#include <Arduino.h>
#include <DNSServer.h>
#include <ESP8266WebServer.h>
#include <ESP8266WiFi.h>
#include <WiFiManager.h>
#include <PubSubClient.h>
#include <LittleFS.h>
#include <ArduinoJson.h>
#include <ArduinoOTA.h>

#include "Utils.h"

/*
  Example of sensorID: VINDRKING-EX976
  When sensor goes online publishes on: airquality/VINDRKING-EX9763/online     
  When sensors updates its state publishes on: airquality/VINDRKING-EX9763/state          
*/

#define ONLINE "online"
#define OFFLINE "offline"
#define MQTT_PORT 1883                      /* Port used by the MQTT publisher */
#define MQTT_KEEPALIVE 10                   /* Keep alive redefinition for MQTT messages*/
#define MQTT_BUFSIZE 2048                   /* Buffersize for the MQTT message */
#define MQTT_PUBLISH_INTERVAL_MS 5000       /* Interval between messages in milliseconds */
#define MQTT_CONNECTION_INTERVAL_MS 60000   /* Reconnection interval */
#define OTA_PASS "ikea"                     /* Password for OTA updates */

char sensorID[32];                          /* Buffer that contains the sensore UID */
char MQTT_TOPIC_ONLINE[128];                /* Avaiability message for MQTT */
char MQTT_TOPIC_OFFLINE[128];               /* Avaiability message for MQTT */
char MQTT_TOPIC_STATE[128];                 /* State message for MQTT */
char MQTT_TOPIC_CONFIG[128];                /* Config message for MQTT */

bool shouldSaveConfig = false;              /* Flag to enable config update on flash memory */
uint32_t previousPublish = millis();        /* Timestamp of previous MQTT publish, on start is millis() */
uint32_t lastMqttConnectionAttempt = 0;     /* Timestamp of the latest MQTT connection attemp in order to handle reconnection */

particleSensorState_t state;                /* Data structure containing the sensor data read from the serial line */

WiFiManager wifiManager;                    /* Handles the wifi connection */
WiFiClient wifiClient;                      /* Handles a client connection to the ESP8266*/
PubSubClient mqttClient;                    /* Handles the mqtt connection to broker and publish*/


/* Custom parameters to be displayed on the wifi manager menu, together with WiFi SSID and PASS */
WiFiManagerParameter mqtt_server("server", "MQTT Server", Config::mqtt_server, sizeof(Config::mqtt_server));
WiFiManagerParameter mqtt_user("user", "MQTT Username", Config::username, sizeof(Config::username));
WiFiManagerParameter mqtt_pass("password", "MQTT Password", Config::password, sizeof(Config::password));
WiFiManagerParameter sensor_name("name", "Sensor Name", Config::name, sizeof(Config::name));

/* Switched the global variable value to true. Needed as function in order to be called as a callback */
void shouldSaveConfigSwitch() 
{
    shouldSaveConfig = true;
}

/* Sets up WiFi and sets mqtt client to the current wifi client */
void setupWifi() 
{
  wifiManager.setDebugOutput(false);
  
  // When called, sets shouldSaveConfig=true so config file will be saved
  // This is used for custom parameters used by the wifi manager defined below
  wifiManager.setSaveConfigCallback(shouldSaveConfigSwitch);

  wifiManager.addParameter(&mqtt_server); 
  wifiManager.addParameter(&mqtt_user);
  wifiManager.addParameter(&mqtt_pass);
  wifiManager.addParameter(&sensor_name);

  // The sensor will be scanned on the network when in AP mode with it's sensor name
  WiFi.hostname(sensorID);  
  wifiManager.autoConnect(sensorID);
    
  // Binds mqtt client to the wifi client
  mqttClient.setClient(wifiClient);

  // Reads config param from config file and prints them to the WifiManager params buffer
  strcpy(Config::mqtt_server, mqtt_server.getValue());
  strcpy(Config::username, mqtt_user.getValue());
  strcpy(Config::password, mqtt_pass.getValue());
  strcpy(Config::name, sensor_name.getValue());

  // Saves config if needed, otherwise reloads the configuration
  if (shouldSaveConfig) {
      Config::saveConfiguration();
  } 
  else {
      Config::loadConfiguration();
  }
}

// Unused mqtt callback
void mqttCallback(char* topic, uint8_t* payload, unsigned int length) {}

/* Publishes the state of the sensor as a MQTT message */
void publishState()
{
  DynamicJsonDocument stateJson(604);   /* Json containing state info */
  char payload[256];                    /* Global payload */
  // State info
  stateJson["pm25"] = state.avgPM25;
  stateJson["ip"] = WiFi.localIP().toString();
  stateJson["quality"] = state.status;
  stateJson["name"] = Config::name;

  // Everything is serialized to the payload
  serializeJson(stateJson, payload);

  // The message is published on airsensor/{sensorid}/state
  // The publish method published only if mqtt is connected
  // So if this method is called without being connected to the mqtt
  // broker, it will only return false without breaking anything 
  mqttClient.publish(&MQTT_TOPIC_STATE[0], &payload[0], true);
}

// void publishConfiguration() {}

void mqttReconnect()
{
//   // Tries to connect three times

  for (uint8_t attempt = 0; attempt < 3; ++attempt) {
    // Changing qos to 0
    if (mqttClient.connect(sensorID, Config::username, Config::password, MQTT_TOPIC_OFFLINE, 0, true, Config::name)) {
        // If connection is successful, declares itself available to the broker which will handle the message
        // differently is the sensor is a known one or a new one
        mqttClient.publish(&MQTT_TOPIC_ONLINE[0], Config::name, true);

        // publishConfiguration();
        // Make sure to subscribe after polling the status so that we never execute commands with the default data
        // mqttClient.subscribe(MQTT_TOPIC_COMMAND);
        break;
    }
    delay(5000);  // waiting for 5 seconds otherwise
  }
}

/* Handles the OTA update */
void OTAConfig()
{
  ArduinoOTA.onStart([]() { Serial.println("Start"); });
  ArduinoOTA.onEnd([]() { Serial.println("\nEnd"); });
  ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
      Serial.printf("Progress: %u%%\r", (progress / (total / 100)));
  });
  ArduinoOTA.onError([](ota_error_t error) {
      Serial.printf("Error[%u]: ", error);
      if (error == OTA_AUTH_ERROR) {
          Serial.println("Auth Failed");
      } else if (error == OTA_BEGIN_ERROR) {
          Serial.println("Begin Failed");
      } else if (error == OTA_CONNECT_ERROR) {
          Serial.println("Connect Failed");
      } else if (error == OTA_RECEIVE_ERROR) {
          Serial.println("Receive Failed");
      } else if (error == OTA_END_ERROR) {
          Serial.println("End Failed");
      }
  });

  ArduinoOTA.setHostname(sensorID);

  // Should be converted to an md5 hash of the password
  ArduinoOTA.setPassword(OTA_PASS);
  ArduinoOTA.begin();
}

void setup() 
{
  // Serial.begin(115200);

  // fills the mqtt topics and the sensorID according to the ESP's chipId
  snprintf(sensorID, sizeof(sensorID), "VINDRIKTNING-%X", ESP.getChipId());;
  snprintf(MQTT_TOPIC_ONLINE, sizeof(MQTT_TOPIC_ONLINE), "airsensor/%s/online", sensorID);
  snprintf(MQTT_TOPIC_OFFLINE, sizeof(MQTT_TOPIC_OFFLINE), "airsensor/%s/offline", sensorID);
  snprintf(MQTT_TOPIC_STATE, sizeof(MQTT_TOPIC_STATE), "airsensor/%s/state", sensorID);

  // Sets up the serial communication with the sensor
  SerialCom::setup();
  // Waits three seconds to avoid errors
  delay(3000);
  // Loads the default configuration from flash
  Config::loadConfiguration();
  
  setupWifi();  // Sets up the wifi 
  OTAConfig();  // Sets up the OTA

  // Configures and connects the mqttClient to the broker
  mqttClient.setServer(Config::mqtt_server, MQTT_PORT);
  mqttClient.setKeepAlive(MQTT_KEEPALIVE);
  mqttClient.setBufferSize(MQTT_BUFSIZE);
  mqttClient.setCallback(mqttCallback);
  mqttReconnect();
}


void loop()
{
  ArduinoOTA.handle();  // Handles OTA firmware update requests
  SerialCom::handleUart(state); // Handles new messages on the serial port
  mqttClient.loop();  // Handles mqtt connection 

  // New time
  const uint32_t currentMillis = millis();

  // If the interval has passed, and the state is valid, published the data
  if (currentMillis - previousPublish >= MQTT_PUBLISH_INTERVAL_MS){
    previousPublish = currentMillis;
    if (state.valid) {
      publishState();
    }
  }

  // If mqtt is not connected, tries to reconnect
  if (!mqttClient.connected() && currentMillis - lastMqttConnectionAttempt >= MQTT_CONNECTION_INTERVAL_MS) {
    lastMqttConnectionAttempt = currentMillis;
    mqttReconnect();
  }
}
