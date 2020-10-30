# PZEM class represents PZEM sensor
import serial
import modbus_tk.defines as cst
from modbus_tk import modbus_rtu


class PZEM():
    """Class to represent PZEM-004t sensor"""
    def __init__(self, tty, line='main'):
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
        self.line = line

    def read(self):
        data = self.master.execute(1, cst.READ_INPUT_REGISTERS, 0, 10)
        self.voltage = data[0] / 10.0,  # [V]
        self.current = (data[1] + (data[2] << 16)) / 1000.0,  # [A]
        self.power = (data[3] + (data[4] << 16)) / 10.0,  # [W]
        self.energy = data[5] + (data[6] << 16),  # [Wh]
        self.frequency = data[7] / 10.0,  # [Hz]
        self.powerFactor = data[8] / 100.0,
        self.alarm = data[9]  # 0 = no alarm
