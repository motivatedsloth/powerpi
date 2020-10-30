# Reading PZEM-004t power sensor (new version v3.0) through
# Modbus-RTU protocol over TTL UART
# Run as:
# python3 readpower.py
# To install dependencies:
# pip install modbus-tk
# pip install pyserial

import paho.mqtt.client as mqtt
import time
import json

broker = '192.168.92'
user = 'energy'
pw = 'Tigger23'
topic = 'energy/realtime'

client = mqtt.Client()
client.username_pw_set(user, pw)
client.connect(broker)


main1 = mkMaster('/dev/ttyUSB0')
main2 = mkMaster('/dev/ttyUSB1')
solar1 = mkMaster('/dev/ttyUSB2')
solar2 = mkMaster('/dev/ttyUSB3')


def reader():
    while 1:
        ret = {
                "main1": readpower(main1),
                "main2": readpower(main2),
                "solar1": readpower(solar1),
                "solar2": readpower(solar2)
                }
        messageInfo = client.publish(topic, json.dumps(ret))
        if messageInfo.rc == mqtt.MQTT_ERR_NO_CONN:
            client.reconnect()
        time.sleep(5)


reader()
