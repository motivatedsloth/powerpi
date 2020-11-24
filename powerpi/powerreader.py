#!/usr/bin/python3
# power reader daemon


import serial
import modbus_tk.defines as cst
from modbus_tk import modbus_rtu

import paho.mqtt.client as mqtt

import os
import time
import json
import math

# port configuration adjust as needed
ports = {
        'main1': '/dev/ttyUSB2',
        'main2': '/dev/ttyUSB1',
        'solar1': '/dev/ttyUSB0',
        'solar2': '/dev/ttyUSB3'
        }

# mqtt config
broker = os.environ.get('MQTT_BROKER')
user = os.environ.get('MQTT_USER')
pw = os.environ.get('MQTT_PASS')
topic = os.environ.get('MQTT_TOPIC')

# general config
report_threshold = 5 # only report if wattage change is greater than 
phantom_load = 45 # typical phantom load 


class PZEMReadError(Exception):
    pass


class pzem():
    """Class to represent PZEM-004t sensor"""
    current = None
    previous = None

    def __init__(self, tty):
        self.master = modbus_rtu.RtuMaster(serial.Serial(
            port=tty,
            baudrate=9600,
            bytesize=8,
            parity='N',
            stopbits=1,
            xonxoff=0
            ))
        self.master.set_timeout(2.0)
        self.master.set_verbose(True)

    def read(self):
        try:
            data = self.master.execute(1, cst.READ_INPUT_REGISTERS, 0, 10)
        except Exception as exp:
            raise PZEMReadError from exp

        voltage = data[0] / 10.0  # [V]
        current = (data[1] + (data[2] << 16)) / 1000.0  # [A]
        power = (data[3] + (data[4] << 16)) / 10.0  # [W]
        energy = data[5] + (data[6] << 16)  # [Wh]
        frequency = data[7] / 10.0  # [Hz]
        powerFactor = data[8] / 100.0
        alarm = data[9]  # 0 = no alarm

        res = {
                'voltage': voltage,
                'current': current,
                'power': power,
                'energy': energy,
                'frequency': frequency,
                'powerFactor': powerFactor,
                'alarm': alarm
                }
        self.previous = self.current
        self.current = res
        return res


class publisher():
    """Send payload to mqtt broker"""
    def __init__(self, broker, user="", password=""):
        self.client = mqtt.Client()
        self.client.username_pw_set(user, password)
        self.client.connect(broker)

    def publish(self, topic, payload):
        messageInfo = self.client.publish(topic, payload)
        if messageInfo.rc == mqtt.MQTT_ERR_NO_CONN:
            self.client.reconnect()


# initialize connections
sensors = dict()

for sensor, port in ports.items():
    sensors[sensor] = pzem(port)

pub = publisher(broker, user, pw)

class branch():
    def __init__(self, limit):
        self.myGen = wattage(limit)
        self.myNet = wattage(limit)
        self.myLoad = load(limit) 

    def evaluate(self, main, generation):
        '''check load and wattages, return true if any changes'''
        load = self.myLoad.evaluate(main, generation)
        gen = self.myGen.add(generation)
        if load or gen:
            self.myNet.add(self.myLoad.getValue() - self.myGen.getValue()) # net is positive when pulling from grid, negative if pushing
            return True
        return False

    def report(self):
        return {
                "net": self.myNet.getValue(),
                "load": self.myLoad.getValue(),
                "generation": self.myGen.getValue()
                }

class wattage():
    '''class to track wattages read'''

    def __init__(self, limit=10):
        '''limit is wattage difference that triggers a change'''
        self.limit = limit
        self.val = None # last reported value

    def add(self, watts):
        '''return true if value changed'''
        if self.val == None or abs(watts - self.val) >= self.limit:
            self.setValue(watts)
            return True
        return False

    def setValue(self, value):
        self.val = value

    def getValue(self):
        return self.val


class load_evaluator():
    '''class for evaluating load by deviation'''

    def __init__(self, quantity=3):
        self.history = list()
        self.quantity = quantity

    def add(self, watts):
        self.history.append(watts)
        if len(self.history) > self.quantity:
            self.history.pop(0)
        self.mean = sum(self.history)/len(self.history)
        self.variance = sum((c - self.mean) **2 for c in self.history)/len(self.history)
        self.dev = math.sqrt(self.variance)
        return watts > 0

    def getDeviation(self):
        return self.dev

    def getValue(self):
        return self.history[-1]


class load(wattage):
    def __init__(self, limit):
        wattage.__init__(self, limit)
        self.over = load_evaluator() # load is greater than generation
        self.under = load_evaluator() # load is less than generation

    def evaluate(self, net, generation):
        isOver = self.over.add(generation + net) # sum when load is greater than generation
        isUnder = self.under.add(generation - net) # difference when load is under than generation
        if not isUnder: # low generation, can only be over
            return self.add(self.over.getValue())
        
        if self.val == None: # no definite choice, just use default
            return self.add(phantom_load)
        
        if self.over.getDeviation() > self.under.getDeviation():
            return self.add(self.under.getValue())
        else: 
            return self.add(self.over.getValue())


class normalizer():
    '''normalize readings to net, load, generation'''
    def __init__(self):
        self.branch1 = branch(report_threshold) 
        self.branch2 = branch(report_threshold) 

    def normalize(self, readings):
        b1 = self.branch1.evaluate(
                    readings['main1']['power'], 
                    readings['solar1']['power']
                )
        b2 = self.branch2.evaluate(
                    readings['main2']['power'],
                    readings['solar2']['power']
                )
        return b1 or b2 

    def report(self):
        return {'branch1': self.branch1.report(), 'branch2': self.branch2.report()}

norm = normalizer()
def reader():
    while 1:
        res = {}
        try:
            for sensor in sensors:
                res[sensor] = sensors[sensor].read()
            if norm.normalize(res):
                pub.publish(topic, json.dumps(norm.report()))
        except Exception as exc:
            print(exc)

        time.sleep(5)

reader()
