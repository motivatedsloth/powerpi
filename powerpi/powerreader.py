#!/usr/bin/python3
# power reader daemon

import time
import json

import serial
import modbus_tk.defines as cst
from modbus_tk import modbus_rtu

import paho.mqtt.client as mqtt

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


class PZEMReadError(Exception):
    pass


class reading():
    '''Class to represent energy reading'''
    def __init__(
            self,
            voltage=None,
            current=None,
            power=None,
            energy=None,
            frequency=None,
            powerFactor=None,
            alarm=None
            ):
        self.voltage = voltage
        self.current = current
        self.power = power
        self.energy = energy
        self.frequency = frequency
        self.powerFactor = powerFactor
        self.alarm = alarm


class pzem():
    """Class to represent PZEM-004t sensor"""
    current = None

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

        voltage = data[0] / 10.0,  # [V]
        current = (data[1] + (data[2] << 16)) / 1000.0,  # [A]
        power = (data[3] + (data[4] << 16)) / 10.0,  # [W]
        energy = data[5] + (data[6] << 16),  # [Wh]
        frequency = data[7] / 10.0,  # [Hz]
        powerFactor = data[8] / 100.0,
        alarm = data[9]  # 0 = no alarm

        res = reading(
                voltage=voltage,
                current=current,
                power=power,
                energy=energy,
                frequency=frequency,
                powerFactor=powerFactor,
                alarm=alarm
                )
        self.current = res
        return res


class publisher():
    """Send readings to mqtt broker"""
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


def reader():
    while 1:
        res = {'hello': 'al', 'hi': 'laura'}
        pub.publish(topic, json.dumps(res))
        time.sleep(5)
