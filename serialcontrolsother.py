
from PySide2 import QtCore, QtGui, QtWidgets
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import QApplication, QMainWindow
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
import numpy as npy
import time
from MasterflexPump import MasterflexPump


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

class PumpWorker(QRunnable):
    def __init__(self, name):
        super(PumpWorker, self).__init__()
        self.name = name
        self.running = True
        self.pumpPort = serial.Serial(port=name, baudrate=4800, bytesize=serial.SEVENBITS, parity=serial.PARITY_ODD, timeout= 1 )
    def run(self):
        while(self.running):
            if self.pumpPort.is_open:
                self.pumpPort.close()

        

class Worker(QObject):
    '''
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and 
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''

    def __init__(self, name, max, **kwargs):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.name = name
        self.max = max
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.running = True
        self.isPaused = False
        
        self.scalePort = MettlerToledoDevice(port=self.name)

        # Add the callback to our kwargs
    def stop(self):
        self.event
    @Slot()
    def pause(self):
        self.isPaused =True
    @Slot()
    def resume(self):
        self.isPaused = False
    def cancel(self):
        self.scalePort.close()
        self.running = False
        
    def factor_conversion(self):
        if 0 < self.maxed < 5001:
            factor = 0.9
        elif 5001 <= self.max < 20001:
            factor = 0.99
        elif 20001 <= self.max:
            factor = 0.999
        return factor 

    @Slot()
    def run(self):
        resultcounter = 0
        resultarray = npy.array([])                  
        deltaarray = npy.array([])
        changecounter = 0
        while(self.running):
            while self.isPaused() ==True:
                time.wait(0)
            try:
                
                s = self.scalePort.get_weight()
                if s:
                    resultcounter += 1

                    num = s[0]
                    inum = int(num)
                    result = str(num)
                    if resultcounter >= 5:
                        resultarray.append(result)
                        resultcounter = 0
                        changecounter += 1
                        p
                        if changecounter >=5:
                           deltaarray.append(resultarray[len(resultarray)-1]-resultarray[-1])
                           changecounter = 0
                           if deltaarray[len(deltaarray)-1]-deltaarray[-1] <= 50:
                               self.cancel()


                    if len(resultarray) > 10:
                        if len(resultarray) < 25:
                            if sum(resultarray)/len(resultarray) <= 100:
                                self.cancel()
                        


                    self.signals.result.emit(result)
                    self.signals.progress.emit(100 * inum/int(0.9*self.factor_conversion()))
                    if (inum > int(self.factor_conversion())):
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

            
         
class SerialControls(QMainWindow, Ui_MainWindow):
    text_update = Signal(str)
    start_scale = Signal(str)


    def __init__(self):
        super(SerialControls, self).__init__()
        self.setupUi(self)
        sys.stdout = self
      
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
        self.progressBar.maximum = 100
        self.dial.valueChanged.connect(self.change_speed)
        try:
            self.pump = MasterflexPump(speed=self.dial.value())
        except:
            self.resultBox.appendPlainText('Shits fucked self.pump aint shit')

        self.threadpool = QThreadPool()
        self.expStart.clicked.connect(self.startTheExp)
        self.mutex = QMutex()
    @Slot()
    def stopShit(self):
        self.event_stop.set()
        self.timer.stop()
        self.expStart.setChecked(False)
        self.pump.close()
        self.resultBox.appendPlainText('Shit has stopped, hopefully')
    def change_speed(self):
        speed = self.dial.value()
        
        self.pump.changeSpeed(speed)
        self.resultBox.appendPlainText('Set speed to: ' + sr)

        
    @Slot(str)   
    def setText(self, s):
        self.mutex.lock()
        self.res = s
        self.mutex.unlock()
    def startTheExp(self):
        name =self.scalePortList.currentText()
        self.timer.start()
        self.expStart.setChecked(True)
        self.rpm = self.dial.value()
        try:
            max = float(str(self.weightBox.text()))
            self.pump.start(self.rpm)
        except:
            max = 0.00
            self.pump.start(0)
            self.resultbox.appendPlainText("Issues with starting at speed")
           
        _threads = []
        for idx in range(5):
            thread = QThread()
            worker = Worker(name,max )
            thread.setObjectName("Worker_" + str(idx))
            _threads.append((thread, worker))
            worker.signals.result.connect(self.setText)
            worker.signals.finished.connect(self.stopShit)
            worker.signals.progress.connect(self.setBar)
            self.dial.sliderMoved.connect(worker.pause)
            self.dial.sliderReleased.connect(worker.resume)
            thread.started.connect(worker.run)
            thread.start()
    @Slot(int)   
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