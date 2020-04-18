from twisted.internet import defer
from twisted.internet.protocol import Factory

# Package Imports
from ..util import now
from ..machine import Machine, Component, Stream, Property
from ..protocol.basic import QueuedLineReceiver as _qlr
__all__ = ["MasterFlex", "Pump"]

class MasterflexLineReceiver(_qlr):
    delimiter= "\x02"
    our_delimiter = "\x0D"

    def sendline(self, line):
        return self.transport.write(line + self.out_delimiter)

class Masterflex (Machine):

    protocolFactory = Factory.forProtocol(MasterflexLineReceiver)
    name = "Masterflex Pump"

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
    def start (self):
        ''' (G) Go Turn pump on and auxiliary output if preset,
            run for number of revolutions set by V command '''
        cmd = "G"
        return self.protocol.write(cmd)
        if abs(int(float(self.requestMotorSpeed()[2:-1]))) <= 0.1:
            return self.halt()
        else:        
            return self.protocol.write(cmd)
    def _assignNumber(self):
        ''' On startup, set the pump number '''
        if not self.initialized:
            cmd = " "
            return self._sendReceive(cmd)
    
    def requestMotorSpeed(self):
        cmd = "S"
        return self.protocol.write(cmd)
    def requestStatus(self):
        ''' (I) Request status data '''
        cmd = "I"
        return self.protocol.write(cmd)
    def goContinuous(self):
        ''' (G) Go Turn pump on and auxiliary output if preset, 
            run continuously until Halt '''
        cmd = 'G' + 0
        if int(float(self.requestMotorSpeed()[2:-1])) == 0:
            return self.stop()
        else:
            return self.protocol.write(cmd)
    
    def stop(self):
        ''' (H) Halt (turn pump off) '''
        cmd = "H"
        return self.protocol.write(cmd)
    	def reset (self):
		return defer.gatherResults([
			self.power.set("off"),
			self.target.set(0)
		])

	def pause (self):
		self._pauseState = self.power.value
		return self.power.set("off")

	def resume (self):
		return self.power.set(self._pauseState)
