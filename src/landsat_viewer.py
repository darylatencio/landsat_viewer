import json
import os
import sys
import tkinter as tk
from data_manager import data_manager
from data_view import data_view
from datetime import datetime
from ee import landsat
from login_dialog import *
from PyQt6 import QtCore, QtGui, QtWidgets
from pathlib import Path
from tkinter import simpledialog

#--------------------------------------------------------------------------------------------------
#+
#-
class landsat_viewer(QtWidgets.QWidget):

    _pr = None
    app = QtWidgets.QApplication(sys.argv)
    file_login = None

    #----------------------------------------------------------------------------------------------
    #+
    #-
    def __init__(self, cloud_cover=None, debug=False, lonlat=None, login_file=None,
                 parent=None, save_login=False, token=None, uname=None, working_folder=None):
        super().__init__(parent)
        if (uname == None or token == None):
            uname, token, save_login = self.get_login(file_login=login_file)
        self.api = landsat(uname, token,
                           cloud_cover=cloud_cover, debug=debug, lonlat=lonlat,
                           working_folder=working_folder)
        if (save_login and (self.api.api_key != None)):
            self.save_login(uname, token)
        self.dm = data_manager(working_folder=self.api.dir_work)
        self.dm.add_listener(self)
        self.gui()

    #----------------------------------------------------------------------------------------------
    #+
    #-
    def dialog_get_login(self):
        # root = tk.Tk()
        # root.withdraw()
        uname, pwd, save = get_ee_login()
        return uname, pwd, save

    #----------------------------------------------------------------------------------------------
    #+
    #-
    def event_download(self, event):
        ll = [float(self.qLL[0].text()),float(self.qLL[1].text())]
        self.api.query(lonlat=ll, month=int(self.text_date[0].text()), year=int(self.text_date[1].text()))
        self.api.download_all()
        self.dm.parse()

    #----------------------------------------------------------------------------------------------
    #+
    #-
    def event_open(self):
        self.load_from_dm()

    #----------------------------------------------------------------------------------------------
    #+
    #-
    def get_login(self, file_login=None):
        self.file_login = os.path.join(Path.home(), "methane_finder", "ee_login.json") if \
            (file_login == None) else file_login
        uname, token, save = "", "", False
        if os.path.exists(self.file_login):
            with open(self.file_login, "r") as file:
                j = json.load(file)
                uname = j["username"] if ("username" in j) else ""
                token = j["token"] if ("token" in j) else ""
        else:
            uname, token, save = self.dialog_get_login()
        return uname, token, save

    #----------------------------------------------------------------------------------------------
    #+
    #-
    def gui(self):
        self.setWindowTitle('Landsat Viewer')
        self.resize(800,600)
        tlb = QtWidgets.QVBoxLayout(self)
        self.tab = QtWidgets.QTabWidget()
        tlb.addWidget(self.tab)
        self.gui_display()
        self.gui_download()
        self.setLayout(tlb)
        self.show()
        sys.exit(self.app.exec())

    #----------------------------------------------------------------------------------------------
    #+
    #-
    def gui_display(self):
        tlb = QtWidgets.QWidget()
        tlb.resize(300,300)
        self.tab.addTab(tlb, 'Display')
        layoutH = QtWidgets.QHBoxLayout(tlb)
    # data manager
        layoutDM = QtWidgets.QVBoxLayout()
        layoutH.addLayout(layoutDM)
        baseDM = QtWidgets.QWidget(tlb)
        baseDM.setFixedWidth(200)
        layoutDM.addWidget(baseDM)
        self.dm.gui(baseDM, width=200)
        self.buttonAuto = QtWidgets.QRadioButton(self)
        self.buttonAuto.setText('Auto Open')
        self.buttonOpen = QtWidgets.QPushButton(self)
        self.buttonOpen.setText('Open')
        self.buttonOpen.clicked.connect(self.event_open)
        layoutBottom = QtWidgets.QHBoxLayout()
        layoutDM.addLayout(layoutBottom)
        layoutBottom.addWidget(self.buttonAuto)
        layoutBottom.addWidget(self.buttonOpen)
    # display
        layoutDV = QtWidgets.QVBoxLayout()
        layoutH.addLayout(layoutDV)
        baseDV = QtWidgets.QWidget(tlb)
        layoutDV.addWidget(baseDV)
        self.viewer = data_view(baseDV)
        self.viewer.signal_coords_changed.connect(self.update_coords)
        self.viewer.signal_coords_selected.connect(self.select_coords)
        self.labelCoords = QtWidgets.QLabel(tlb)
        self.labelCoords.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignCenter |
            QtCore.Qt.AlignmentFlag.AlignCenter)
        layoutDV = QtWidgets.QVBoxLayout(baseDV)
        layoutDV.addWidget(self.viewer)
        layoutDV.addWidget(self.labelCoords)

    def gui_download(self):
        tlb = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        tlb.setLayout(layout)
        self.tab.addTab(tlb, 'Search')
    # text output
        self.text_output = QtWidgets.QTextEdit(str(datetime.now()), self)
        self.text_output.ensureCursorVisible = True
        self.text_output.setReadOnly = True
        self.text_output.resize(500,500)
        self.api.text_output = self.text_output
        layout.addWidget(self.text_output)
    # bottom base
        layout_bottom = QtWidgets.QHBoxLayout()
    # month/year
        layout_bottom.addWidget(QtWidgets.QLabel('Month/Year:'), alignment=QtCore.Qt.AlignmentFlag.AlignRight)
        layout_date = QtWidgets.QHBoxLayout()
        layout_date.setSpacing(0)
        self.text_date = [QtWidgets.QLineEdit(str(self.api.month), self)]
        self.text_date[0].setValidator(QtGui.QIntValidator(1,12))
        self.text_date.append(QtWidgets.QLineEdit(str(self.api.year), self))
        self.text_date[1].setValidator(QtGui.QIntValidator(2005,2025))   
        for text_date in self.text_date:
            text_date.setFixedWidth(40)
            layout_date.addWidget(text_date)
        layout_bottom.addLayout(layout_date)
    # lon/lat
        layout_bottom.addWidget(QtWidgets.QLabel('Lon/Lat:'), alignment=QtCore.Qt.AlignmentFlag.AlignRight)
        layout_ll = QtWidgets.QHBoxLayout()
        layout_ll.setSpacing(0)
        self.qLL = [QtWidgets.QLineEdit(str(self.api.ll[0]), self)]
        self.qLL[0].setValidator(QtGui.QDoubleValidator(-180,180,3))
        self.qLL.append(QtWidgets.QLineEdit(str(self.api.ll[1]), self))
        self.qLL[1].setValidator(QtGui.QDoubleValidator(-90,90,3))
        for qLL in self.qLL:
            qLL.setFixedWidth(50)
            layout_ll.addWidget(qLL)
        layout_bottom.addLayout(layout_ll)
        button = QtWidgets.QPushButton("Download", self)
        button.setFixedWidth(70)
        button.mousePressEvent = self.event_download
        layout_bottom.addWidget(button)
        layout_bottom.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        layout.addLayout(layout_bottom)

    #----------------------------------------------------------------------------------------------
    #+
    #-
    def load_from_dm(self):
        pixmap = self.dm.get_data()
        pr = self.dm.get_pr()
        self.viewer.set_data(pixmap, reset=(pr != self._pr))
        self._pr = pr

    #----------------------------------------------------------------------------------------------
    #+
    #-
    def save_login(self, uname, tok):
        print("saving login information")
        dir = os.path.dirname(self.file_login)
        if not os.path.exists(dir):
            os.mkdir(dir)
        with open(self.file_login, "w") as file:
            json.dump({"username":uname, "token":tok}, file)

    #----------------------------------------------------------------------------------------------
    #+
    #-
    def select_coords(self, point):
        if not point.isNull():
            ll, xyMap = self.dm.get_data_coords((point.x(), point.y()))

    #----------------------------------------------------------------------------------------------
    #+
    #-
    def signal_datamanager(self, event):
        if not (self.isVisible() and self.buttonAuto.isChecked()):
            return None
        self.load_from_dm()

    #----------------------------------------------------------------------------------------------
    #+
    #-
    def update_coords(self, point):
        if not point.isNull():
            ll, xyMap = self.dm.get_data_coords((point.x(),point.y()))
            self.labelCoords.setText(
                f"geo: [{ll[0]:.3f},{ll[1]:.3f}] map: [{xyMap[0]},{xyMap[1]}]  pixel: [{point.x()}, {point.y()}]")
        else:
            self.labelCoords.clear()

if __name__ == '__main__':
    import sys
    print('testing Landsat viewer')
    cc = 50.0
    ll = [54.199,38.499]
    dir = 'C:\\data\\landsat'
    viewer = landsat_viewer(cloud_cover=cc, debug=True, lonlat=ll, working_folder=dir)
