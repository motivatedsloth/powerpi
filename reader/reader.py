# Reading PZEM-004t power sensor (new version v3.0) through Modbus-RTU protocol over TTL UART
# Run as:
# python3 readpower.py

# To install dependencies: 
# pip install modbus-tk
# pip install pyserial

import serial
import modbus_tk.defines as cst
from modbus_tk import modbus_rtu
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

def mkMaster(tty):
	master = modbus_rtu.RtuMaster(serial.Serial(
                       port=tty,
                       baudrate=9600,
                       bytesize=8,
                       parity='N',
                       stopbits=1,
                       xonxoff=0
                      )
	)
	master.set_timeout(2.0)
	master.set_verbose(True)
	return master

main1 = mkMaster('/dev/ttyUSB0')
main2 = mkMaster('/dev/ttyUSB1')
solar1 = mkMaster('/dev/ttyUSB2')
solar2 = mkMaster('/dev/ttyUSB3')

main1file = open('/home/pi/main1', 'w')
main2file = open('/home/pi/main2', 'w')
solar1file = open('/home/pi/solar1', 'w')
solar2file = open('/home/pi/solar2', 'w')

def readpower(master):
	data = master.execute(1, cst.READ_INPUT_REGISTERS, 0, 10)
	ret = {
	
		"voltage": data[0] / 10.0, # [V]
		"current": (data[1] + (data[2] << 16)) / 1000.0, # [A]
		"power": (data[3] + (data[4] << 16)) / 10.0, # [W]
		"energy": data[5] + (data[6] << 16), # [Wh]
		"frequency": data[7] / 10.0, # [Hz]
		"powerFactor": data[8] / 100.0,
		"alarm": data[9] # 0 = no alarm
	}
	return ret

def mystr(values):
	return str(values['voltage']) + ", " + str(values['power']) + ", " + str(values['powerFactor']) + "\n"

def reader():
	while 1:
		ret = {
			"main1": readpower(main1),
			"main2": readpower(main2),
			"solar1": readpower(solar1),
			"solar2": readpower(solar2)
			#"solar2": readpower(solar1)
		}
		messageInfo = client.publish(topic, json.dumps(ret))
		if messageInfo.rc == mqtt.MQTT_ERR_NO_CONN:
			client.reconnect()
		main1file.write(mystr(ret['main1']))
		main2file.write(mystr(ret['main2']))
		solar1file.write(mystr(ret['solar1']))
		solar2file.write(mystr(ret['solar2']))
		time.sleep(5)

reader()
