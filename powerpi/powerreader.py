#!/usr/bin/python3
# power reader daemon

import time
import json

from powerpi.sensor import pzem
from powerpi.notifier import publisher
# from powerpi.branch import branch

# port configuration adjust as needed
ports = {
        'main1': '/dev/ttyUSB0',
        'main2': '/dev/ttyUSB1',
        'solar1': '/dev/ttyUSB2',
        'solar2': '/dev/ttyUSB3'
        }

# mqtt config
broker = '192.168.0.92'
user = 'energy'
pw = 'Tigger23'
topic = 'energy/testing'

# initialize connections
sensors = dict()

for sensor, port in ports.items():
    sensors[sensor] = pzem(port)

mqtt = publisher(broker, user, pw)


def reader():
    while 1:
        res = {'hello': 'al', 'hi': 'laura'}
        mqtt.publish(topic, json.dumps(res))
        time.sleep(5)
