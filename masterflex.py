from twisted.internet import defer
from twisted.internet.protocol import Factory

# System Imports
from time import time as now

# Package Imports
from ..machine import Machine, Property, Stream, ui
from ..protocol.basic import QueuedLineReceiver

__all__ = ["MasterFlex", "Pump"]

class MasterflexLineReceiver(QueuedLineReceiver):
    delimiter= b''

    def dataReceived (self, data):
        r = QueuedLineReceiver.dataReceived(self, data)

        if self._current.delimiter == '\x02':
            while r: 
                delimiter += r
                self.lineReceived(delimiter)
            else:
                delimiter += r
                return delimiter

class Masterflex (Machine):

    protocolFactory = Factory.forProtocol(MasterflexLineReceiver)
    name = "Masterflex Pump"
    def _standardCommand(self, cmd_char, *params):
        ''' Builds and returns a formatted string 
            representation of a standard command '''
        cmd = "P%02d" % self.pump_addr + cmd_char
        for param in params:
            cmd += "%s" % param
        return '\x02' + cmd + '\x0D' 
    def setup (self):
        def set_power (power):
			cmd = "ON" if power == "on" else "OFF"
			return self.protocol.write(cmd)

        self.status = Property(title = "Status", type = str)
        self.power = Property(title = "Power", type = str, options = ("on", "off"), setter = set_power)
        self.direction = Property(title = "Direction", type = str, options = ("cw", "ccw"))
        self.ui = ui(
            trace = [{
                "title": "Power",
                "traces": [self.power],
                "colours": ["#0c4"]
            }],
            properties = [self.direction]
        )
    def go(self):
        ''' (G) Go Turn pump on and auxiliary output if preset,
            run for number of revolutions set by V command '''
        cmd = "G"
        return self.protocol.write(cmd)
        if abs(int(float(self.requestMotorSpeed()[2:-1]))) <= 0.1:
            return self.halt()
        else:        
            return self.protocol.write(cmd)
    def requestMotorSpeed(self):
        cmd = 'S'
        return self.protocol.write(cmd)
    def requestStatus(self):
        ''' (I) Request status data '''
        cmd = 'I'
        return self.protocol.write(cmd)
    def goContinuous(self):
        ''' (G) Go Turn pump on and auxiliary output if preset, 
            run continuously until Halt '''
        cmd = 'G' + 0
        if int(float(self.requestMotorSpeed()[2:-1])) == 0:
            return self.halt()
        else:
            return self.protocol.write(cmd)
    
    def halt(self):
        ''' (H) Halt (turn pump off) '''
        cmd = "H"
        return self.protocol.write(cmd)