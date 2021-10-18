#pragma once

#include <SoftwareSerial.h>
#include <LittleFS.h>
#include <ArduinoJson.h>

struct particleSensorState_t {
    uint16_t avgPM25 = 0;                           /* Average of five measurement */
    uint16_t measurements[5] = {0, 0, 0, 0, 0};     /* Collection of five measurement */
    uint8_t measurementIdx = 0;                     /* Idx of the measurement */
    boolean valid = false;                          /* Indicates if the content is valid */
    uint8_t status = 0;                             /* Maps the status to good, bad, medium */
};

namespace Config {

    // Default params are all empty

    char mqtt_server[80] = "";
    char username[24] = "";
    char password[24] = "";
    char name[24] = "My Room";

    /* 
        Saves the wifiManager configuration as json file containing params  
        in flash memory. LittleFS uses NOR storage with wear levelling so
        it doesn't strongly damage the MCU
    */
    void saveConfiguration() {
        File configFile;
        DynamicJsonDocument configuration(512);

        configuration["mqtt_server"] = mqtt_server;
        configuration["username"] = username;
        configuration["password"] = password;
        configuration["name"] = name;

        if (!(configFile = LittleFS.open("/config.json", "w"))) {
            return;  // should never happen
        }

        // serializing the DynamicJsonDocument to the file, then closing 
        serializeJson(configuration, configFile);
        configFile.close();
    }

    /* 
        Loads the configuration file if present. 
        Then copies params to the respective variables
    */
    void loadConfiguration() {
        if (LittleFS.begin()) {

            if (LittleFS.exists("/config.json")) {
                File configFile = LittleFS.open("/config.json", "r");

                if (configFile) {
                    // getting size in bytes
                    const size_t size = configFile.size();

                    // using unique pointer as a safety measure in order to avoid having
                    // multiple pointers referencing the same buffer
                    std::unique_ptr<char[]> buf(new char[size]);


                    // reading file to the buffer
                    configFile.readBytes(buf.get(), size);
                    DynamicJsonDocument configuration(512);

                    // deserzializing the buffer to the Dynamic Json data structure 
                    if (DeserializationError::Ok == deserializeJson(configuration, buf.get())) {

                        // Then assigning params to variables 

                        strcpy(mqtt_server, configuration["mqtt_server"]);
                        strcpy(username, configuration["username"]);
                        strcpy(password, configuration["password"]);
                        strcpy(name, configuration["name"]);
                    }

                    configFile.close();    // closing the file
                }
            }
        }
    }
}

namespace SerialCom {

    constexpr static const uint8_t PIN_UART_RX = 4;             /* D2 PIN */
    constexpr static const uint8_t PIN_UART_TX = 13;            /* UNPLUGGED */

    // Using SoftwareSerial to read sensor data over RX pin
    SoftwareSerial sensorSerial(PIN_UART_RX, PIN_UART_TX);      

    uint8_t serialRxBuf[255];       /* Serial buffer */
    uint8_t rxBufIdx = 0;           /* Reading position in buffer */

    void setup() {
        sensorSerial.begin(9600);   /* Reading at 9600 bauds which is sufficient */
    }

    void clearRxBuf() {
        memset(serialRxBuf, 0, sizeof(serialRxBuf));     /* Clearing the buffer */
        rxBufIdx = 0;                                    /* Resetting the reading position */
    }


    /* Evaluates the air quality status basing on the IKEA's manual indications */
    uint8_t evaluateStatus(float avgPM25) {
        if (avgPM25 <= 35){
            return 0;    // Good
        }else if(avgPM25 > 25 && avgPM25 < 85){
            return 1;    // Medium
        }else{
            return 2;    // Bad
        }
    }

    /* 
        Extracts the payload from the buffer. 
        It's a 16 bit unsigned integer which is codified
        in two bytes as a uint16_t. The two bytes are 
        the fifth and the sixth 
    */
    void parseState(particleSensorState_t& state) {

        const uint16_t pm25 = (serialRxBuf[5] << 8) | serialRxBuf[6];

        state.measurements[state.measurementIdx] = pm25;

        state.measurementIdx = (state.measurementIdx + 1) % 5;

        // Computes the avg of five measurements, evaluates the status
        // and sets valid to true
        if (state.measurementIdx == 0) {
            float avgPM25 = 0.0f;

            for (uint8_t i = 0; i < 5; ++i) {
                avgPM25 += state.measurements[i] / 5.0f;
            }

            state.avgPM25 = avgPM25;
            state.status = evaluateStatus(avgPM25);
            state.valid = true;
        }

        clearRxBuf();  // Cleaning the buffer at the end
    }

    /* Checks if the serial message header is valid. Header must be 22 17 11*/
    bool isValidHeader() {
        return serialRxBuf[0] == 0x16 && serialRxBuf[1] == 0x11 && serialRxBuf[2] == 0x0B;
    }

    /* Checks if the checksum is valid. The 20 bytes sum must be 0 */
    bool isValidChecksum() {
        uint8_t checksum = 0;

        for (uint8_t i = 0; i < 20; i++) {
            checksum += serialRxBuf[i];
        }

        return checksum == 0;
    }

    /*
        Receives data over UART, parses the value, checks header and checksum.
        Then fills the state data structure
    */
    void handleUart(particleSensorState_t& state) {
        if (!sensorSerial.available()) {
            return;
        }

        // Reading serial until it's not available
        while (sensorSerial.available()) {
            serialRxBuf[rxBufIdx++] = sensorSerial.read();

            delay(15);                          // pause between readings

            if (rxBufIdx >= 64) clearRxBuf();   // too long, clearing the buffer
        }

        // If the data read is valid, parsing the state
        if (isValidHeader() && isValidChecksum()) {
            parseState(state);
        } else {
            // Otherwise clears the buffer            
            clearRxBuf();
        }
    }
} // namespace SerialCom