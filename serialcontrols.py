from PySide2 import QtCore, QtGui, QtWidgets
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import QApplication, QMessageBox, QMainWindow, QMenu, QAction, QToolBar
from PySide2.QtUiTools import QUiLoader
import sys
from Ui_mainwindow import Ui_MainWindow
import serial
import serial.tools.list_ports
from mettler_toledo_device import MettlerToledoDevice
import threading
import asyncio.tasks
import asyncio
import queue
#from MasterflexPump import MasterflexPump

import RPi.GPIO as gp

class WorkerSignals(QObject):
    '''
    Defines the signals available from a running worker thread.
    Supported signals are:
    finished
        No data
    
    error
        `tuple` (exctype, value, traceback.format_exc() )
    
    result
        `object` data returned from processing, anything
    progress
        `int` indicating % progress 
    '''
    finished = Signal()
    error = Signal(tuple)
    result = Signal(object)
    connected = Signal(str)
    progress = Signal(int)
    pumpStart = Signal()
    pumpStop = Signal()



class Worker(QRunnable):
    '''
    Worker thread
    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.
    :param callback: The function callback to run on this worker thread. Supplied args and 
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function
    '''

    def __init__(self, name,pumpname,max, isSerial, **kwargs):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.name = name
        self.max = max
        self.isPaused = False
        self.pumpname = pumpname
                
        self.resultsvector = []
        self.changevector = []
        self.isSerial = isSerial
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.running = True
        if(self.isSerial == True):
            try:
                self.pumpPort = serial.Serial(port=self.pumpname, baudrate=4800, bytesize=serial.SEVENBITS, parity=serial.PARITY_ODD, timeout= 1 )
            except:
                self.pumpPort.close()
                self.pumpPort = serial.Serial(port=self.pumpname, baudrate=4800, bytesize=serial.SEVENBITS, parity=serial.PARITY_ODD, timeout= 1 )
        

        
        self.scalePort = MettlerToledoDevice(port=self.name)
            
        # Add the callback to our kwargs
    def stop(self):
        self.event
    def pause(self):
        self.isPaused = True
    def resume(self):
        self.isPaused = False
    def cancel(self):
        if(self.isSerial == True):
            try:
                self.scalePort.close()
                self.running = False
                self.resultsvector = []
                self.changevector =[]
                self.pumpPort.close()
            except: 
                self.scalePort = None
                self.pumpPort = None
        else:
            
            #self.signals.pumpStop.emit()
            self.scalePort.close()
            self.running = False
    def factor_conversion(self):
        if 0 < self.max < 5001:
            factor = 0.9
        elif 5001 <= self.max < 20001:
            factor = 0.99
        elif 20001 <= self.max:
            factor = 0.999
        return factor 

    def convertToVoltage(self, rpm):
        volt = self.rpm*0.016 
    @Slot()
    def run(self):
        if(self.isSerial == True):
            if(self.pumpPort):
                self.pumpPort.close()

        while(self.running):
            while self.isPaused:
                time.sleep(0)
            
            try:
                
                s = self.scalePort.get_weight()
                if s:
                    num = s[0]
                    inum = int(num)
                    result = str(num)
                    changes = []
                    self.resultsvector.append(int(inum))
                    self.signals.result.emit(result)
                    self.signals.progress.emit(100 * inum/int(0.97*self.max))
                    
                    if(len(self.resultsvector) > 5):
                        if(self.resultsvector[-1] != self.resultsvector[-2]):

                            change = float(self.resultsvector[-1]) - float(self.resultsvector[-2])
                            self.changevector.append(float(change))

                        if(len(self.changevector) > 5):
                            avg = sum(self.changevector)/len(self.changevector)
                            if((self.changevector[-1])/avg < 0.1):
                                self.signals.result.emit("Air in the line or still clamped")
                                self.signals.error.emit((str(self.changevector[-1]), "Rate of change has fallen to low, check line"))
                                self.cancel()
                                break 
                                           
              

                    if (inum > int(0.999*self.max)):
                        self.cancel()
                        break
                   
                    
                if self.scalePort is None:
                    self.cancel()
                    break
            except:
               
                self.cancel()
                break
                 
           # Return the result of the processin
              # Done
        if (self.running == False):
            self.signals.finished.emit()


class PumpThread():
    def __init__(self, **kwargs):
        super(PumpThread, self).__init__()
        self.signals = WorkerSignals()
        self.isPumping = False
        self.pump = MasterflexPump(0)
        self.signals.pumpStart.connect(self.run)
        self.signals.pumpStop.connect(self.stop)
        
    def stop(self):
        self.isPumping == False
        self.pump.close()    
    def run(self):
        while self.isPumping:
            self.pump(600)
            
            
        
         
class SerialControls(QMainWindow, Ui_MainWindow):
    text_update = Signal(str)
    start_scale = Signal(str)


    def __init__(self):
        super(SerialControls, self).__init__()
        self.setupUi(self)
        sys.stdout = self
        self.speed = 0
        self._createActions()
        self._createToolBars()
        app.aboutToQuit.connect(self.closeEvent)
        self.direction = False
        self._createMenuBar()
        self.res = ''   
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.scalePortList.addItem(port.device)
            self.pumpPortList.addItem(port.device)
        self.stopButton.clicked.connect(self.stopShit)
        self.setWindowTitle("Sup")
        self.counter = 0
        self.timer = QTimer()
        self.event_stop = threading.Event()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.recurring_timer)
        self.progressBar.setValue(1)
        self.progressBar.minimum = 0
        self.rpm = 0
        self.isSetup = True
        self.setup()

        self.progressBar.maximum = 100
        self.dial.valueChanged.connect(self.change_speed)
        if(self.serialCheck == True):
            try:
                self.pumpPort = serial.Serial(port=self.pumpPortList.currentText(), baudrate=4800, bytesize=serial.SEVENBITS, parity=serial.PARITY_ODD, timeout= 1 )
            except:
                self.pumpPort = None
        else:
            try:
                self.pump = MasterflexPump()
                self.isConnected = True
            except:
                
                self.isConnected = False
        self.threadpool = QThreadPool()
        self.expStart.clicked.connect(self.startTheExp)
        self.mutex = QMutex()
    def setup(self):
        if not self.isSetup:
            self.isSetup = True
        gp.setmode(gp.BOARD)
        gp.setup(35, gp.OUT)
        gp.setup(32, gp.OUT)
        gp.setup(36, gp.OUT)
        gp.output(36, 1)
        self.p = gp.PWM(32, 2000)
    def _createMenuBar(self):   
        menuBar = self.menuBar()
        fileMenu = QMenu("&File", self)
        menuBar.addMenu(fileMenu)
        # Creating menus using a title
        editMenu = menuBar.addMenu("&Edit")
        helpMenu = menuBar.addMenu("&Help")
    def _createToolBars(self):
        # Using a title
        fileToolBar = self.addToolBar("File")
        # Using a QToolBar object
        editToolBar = QToolBar("Edit", self)
        self.addToolBar(editToolBar)
        # Using a QToolBar object and a toolbar area
        helpToolBar = QToolBar("Help", self)
        self.addToolBar(Qt.LeftToolBarArea, helpToolBar)
    def _createActions(self):
        # Creating action using the first constructor
        self.newAction = QAction(self)
        self.newAction.setText("&New")
        # Creating actions using the second constructor
        self.openAction = QAction("&Open...", self)
        self.saveAction = QAction("&Save", self)
        self.exitAction = QAction("&Exit", self)
        self.copyAction = QAction("&Copy", self)
        self.pasteAction = QAction("&Paste", self)
        self.cutAction = QAction("C&ut", self)
        self.helpContentAction = QAction("&Help Content", self)
        self.aboutAction = QAction("&About", self)
    def closeEvent(self, event):
        self.resultBox.appendPlainText('Close button pressed')
        import sys
        import RPi.GPIO as gp
        close = QMessageBox.question(self, "&Close", "Sure?", QMessageBox.Yes | QMessageBox.No)
        if close == QMessageBox.Yes:
             event.accept()
             if self.isConnected:
                 gp.cleanup()
             sys.exit(0)
        else:
             event.ignore()
        #self.pump.close()

    def stopShit(self):
        self.event_stop.set()
        self.timer.stop()
        self.expStart.setChecked(False)
        if(self.serialCheck.isChecked()==True):
            self.pumpPort = serial.Serial(port=self.pumpPortList.currentText(), baudrate=4800, bytesize=serial.SEVENBITS, parity=serial.PARITY_ODD, timeout= 1 )
        #if self.pump:
            #self.pump.stop()
        gp.output(36,1)
        
        self.isConnected = False
        self.resultBox.appendPlainText('if not stopped, manually do and restart program. if stopped good job!')
    def change_speed(self):
        rpm = self.dial.value()
        self.p.ChangeDutyCycle(rpm/6)
        #self.pump.changeSpeed(rpm)     
   #def change_dir(self):
        #self.pump.changeDir()
     
    def setText(self, s):
        self.mutex.lock()
        self.res = s
        self.mutex.unlock()
    def startTheExp(self):
        name =self.scalePortList.currentText()
        self.timer.start()
        self.expStart.setChecked(True)
        if self.serialCheck.isChecked():
            pumpname = self.pumpPortList.currentText()
            try:
                max = float(str(self.weightBox.text()))
                self.pumpPort.close()
            except:
                max = 0.00
                self.pumpPort = None
        else:
            try:
                pumpname = "PWM"
                self.rpm = self.dial.value()
                #self.pump.start(self.rpm) 
                self.p.start(self.rpm/6)
                gp.output(36,0)
                max = float(str(self.weightBox.text()))
            except:
                max = 0.00
                #self.pump.start(0)
                gp.output(36,1)
                
                
                self.resultBox.appendPlainText('Failed on Start expStart')
                self.stopShit()
        worker = Worker(name, pumpname, max, self.serialCheck.isChecked())
        worker.signals.result.connect(self.setText)
        worker.signals.finished.connect(self.stopShit)
        worker.signals.progress.connect(self.setBar)
        #self.dial.sliderMoved.connect(worker.pause)
        #self.dial.sliderReleased.connect(worker.resume)
        self.threadpool.start(worker)

   
    def setBar(self, per):
        self.progressBar.setValue(per)

    def recurring_timer(self):
        self.resultBox.appendPlainText(self.res)
        

if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle('Fusion')
    main = SerialControls()
    main.show()
    sys.exit(app.exec_())