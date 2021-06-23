import RPi.GPIO as gp


class MasterflexPump():

    def __init__(self):
        self.isSetup = True
        self.speed = 0
        self.dc = 0

        self.direction = True
        self.setup()
     
    def setup(self):
        if not self.isSetup:
            self.isSetup = True
        gp.setmode(gp.BOARD)
        gp.setup(35, gp.OUT)
        gp.setup(32, gp.OUT)
        gp.setup(36, gp.OUT)
        gp.output(36, 1)
        self.p = gp.PWM(32, 2000)
    def convert(self, rpm):
        
        return rpm*0.16 
    def changeDir(self): 
       # gp.setup(35, gp.OUT)
        if(self.direction):
            gp.output(35, 1)
        else:
            gp.output(35, 0)
    def close(self):
        gp.cleanup()
        self.isSetup = False
    def start(self, speed):
        if not self.isSetup:
            self.setup()
        self.p.start(speed*0.16)
        gp.output(36, 0)
    def stop(self):
        gp.output(36, 1)
    def changeSpeed(self, rpm):
        if not self.isSetup:
            self.p.ChangeDutyCycle(rpm*0.16)


        
