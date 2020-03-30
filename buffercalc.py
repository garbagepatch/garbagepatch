# -*- coding: utf-8 -*-
"""
Created on Thu Mar 26 22:30:24 2020

@author: cmedders
"""
import sys
from PyQt5 import QtGui,QtWidgets, uic
import numpy as np
import decimal as dec
import os, sys
# Translate asset paths to useable format for PyInstaller
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath('.'), relative_path)
qtCreatorFile = r'C:\Users\cmedders\buffergui\assets\ui.ui'  # Enter file here.
buffercalc, QtBaseClass = uic.loadUiType(resource_path('./assets/ui.ui'))


class MyApp(QtWidgets.QMainWindow, buffercalc):

    def __init__(self):

        QtWidgets.QMainWindow.__init__(self)
        buffercalc.__init__(self)
        self.setupUi(self)
        self.calculate.clicked.connect(self.calculate_buffer)
        self.calculate2.clicked.connect(self.calculate_phosphate)

    def calculate_buffer(self):

        tot = float(self.totbox.text())
        ph = float(self.pHedit.text())
        nacl = float(self.NaClEdit.text())
        pka =  4.616361+1.365646*tot+0.018523*ph-0.208809*nacl-0.380675*tot*ph-2.130478*tot*nacl-0.055742*ph*nacl+0.569584*tot*ph*nacl
        molr = np.power(10, (ph-pka))
        molha = tot/(molr+1)
        mola = tot-molha
        ha = molha/17.4*1000
        a = mola*82.03
        NACL = nacl*58.44
        HA_string = "Glacial Acetic Acid: {:.3f}mL".format(ha)
        A_string = "Sodium Acetate Anhydrous: {:.2f}g".format(a)
        NACL_string = "Sodium Chloride: {:.2f}g".format(NACL)
        results_string = f"""{HA_string}
{A_string}
{NACL_string}

"""
        self.results_output.setText(results_string)
        self.result_text.insertPlainText(results_string)
        return(results_string)
    def calculate_phosphate(self):


        totp = float(self.tnapi.text())
        php = float(self.ph2.text())
        naclp = float(self.nacl2_2.text())
        pkap =  6.675623+ 1.874575*totp -0.007536*php -0.425927*naclp
        molrp = np.power(10,php-pkap)
        molhap = totp/(molrp+1)
        molap = totp-molhap
        hap = molhap*137.99
        ap = molap*141.96
        naclp2 = naclp*58.44
        hap_string = "Sodium Phosphate Monobasic Monohydrate: {:.3f}g".format(hap)
        ap_string = "Sodium Phosphate Dibasic Anhydrous: {:.3f}g".format(ap)
        naclp_string = "Sodium Chloride: {:.3f}g".format(naclp2)
        presults_string = f"""{hap_string}
{ap_string}
{naclp_string}

"""


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec_())