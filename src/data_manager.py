import numpy as np
import os
import re
import tempfile

from osgeo import gdal, osr
from PyQt6 import QtCore, QtGui, QtWidgets

class data_manager():

    _pr = None
    d = {}
    listPR = None
    listDT = None
    listener = []
    raster = None

    def __init__(self, working_folder=None):
        self.dir = os.path.join(tempfile.gettempdir(),'data') if (working_folder == None) else working_folder
        if not os.path.exists(self.dir):
            os.mkdir(self.dir)
        self.srs_wgs84 = osr.SpatialReference()
        self.srs_wgs84.SetWellKnownGeogCS("WGS84")
        self.parse()
        return None

    def __str__(self):
        return 'data manager'

    def add_listener(self, listener):
        self.listener.append(listener)

    def format_date(self, s):
        sOut = s[0:4]+'/'+s[4:6]+'/'+s[6:]
        return sOut

    def get_available_data(self):
        return None

    def get_current_selection(self):
        itemPR = self.listPR.currentItem()
        if not itemPR:
            return False, None, None
        pr = itemPR.text()
        itemDT = self.listDT.currentItem()
        if not itemDT:
            return False, pr, None
        return True, pr, itemDT.text()

    def get_data(self, band=None):
        void, pr, dt = self.get_current_selection()
        if not void:
            print('either path/row or date not selected selected')
            return None
        dDT = (self.d[pr])[dt]
        match self.combo_box.currentText().lower():
            case 'methane':
                if ("methane" in dDT):
                    methane = dDT["methane"]
                else:
                    methane = self.methane_image(dDT)
                    dDT["methane"] = methane
                img = QtGui.QImage(methane.data, methane.shape[1], methane.shape[0], QtGui.QImage.Format.Format_Grayscale16)
            case 'rgb':
                band = ['B4','B3','B2']
                if ("rgb" in dDT):
                    rgb = dDT["rgb"]
                else:
                    npByte = []
                    for key in band:
                        npUint = self.open_file(dDT[key])
                        npByte.append((npUint/256).astype(np.uint8))
                        npUint = None
                    rgb = np.zeros((npByte[0].shape[0], npByte[0].shape[1], len(band)), dtype=np.uint8)
                    for i in range(len(band)):
                        rgb[:,:,i] = npByte[i].data
                    dDT["rgb"] = rgb
                    for i in range(len(band)):
                        npByte[i] = None
                img = QtGui.QImage(rgb.data, rgb.shape[1], rgb.shape[0], len(band)*rgb.shape[1],
                                   QtGui.QImage.Format.Format_RGB888)
            case _:
                file = dDT[self.combo_box.currentText()]
                npImg = self.open_file(file)
                img = QtGui.QImage(npImg.data, npImg.shape[1], npImg.shape[0], QtGui.QImage.Format.Format_Grayscale16)
                npImg = None
        
        pixmap = QtGui.QPixmap.fromImage(img)
# todo: investigate sub-pixel interpolation
#        pixmap = pixmap.scaled(8000, 8000, QtCore.Qt.AspectRatioMode.KeepAspectRatio, transformMode=QtCore.Qt.TransformationMode.SmoothTransformation)
        self._pr = pr
        return pixmap                

    def get_pr(self):
        return self._pr

    def get_data_coords(self, xy):
        xoff, a, b, yoff, d, e=self.raster.GetGeoTransform()
        x_map = a*xy[0] + b*xy[1] + xoff
        y_map = d*xy[0] + e*xy[1] + yoff
        tf = osr.CoordinateTransformation(self.srs, self.srs_wgs84)
        lon, lat, _ = tf.TransformPoint(x_map, y_map)
        return (lon,lat), (x_map,y_map)

    def get_folder(self):
        return self.dir

    def gui(self, parent, width=None):
        tlb = QtWidgets.QWidget(parent)
        layout = QtWidgets.QVBoxLayout(tlb)
        tlb.setLayout(layout)
        layout.addWidget(QtWidgets.QLabel('Path/Row'), alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        self.listPR = QtWidgets.QListWidget(tlb)
        self.listPR.itemClicked.connect(self.signal_clicked_pr)
        layout.addWidget(self.listPR)
        layout.addWidget(QtWidgets.QLabel('Date'), alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        self.listPR.setFixedHeight(64)
        self.listDT = QtWidgets.QListWidget(tlb)
        self.listDT.itemClicked.connect(self.signal_clicked_dt)
        layout.addWidget(self.listDT)
        self.listDT.setFixedHeight(128)
        if (width != None):
            self.listPR.setFixedWidth(width)
            self.listDT.setFixedWidth(width)
        layout_bottom = QtWidgets.QHBoxLayout()
        self.combo_box = QtWidgets.QComboBox(tlb)
        self.combo_box.currentIndexChanged.connect(self.signal_band_changed)
        layout_bottom.addWidget(self.combo_box)
        layout.addLayout(layout_bottom)
        self.combo_box.addItems(['B1','B2','B3','B4','B5','B6','B7','B10','RGB','Methane'])
        self.combo_box.setCurrentIndex(8)
        self.update_list()

    def methane_image(self, dDT=None):
        if (dDT == None):
            void, pr, dt = self.get_current_selection()
            if not void:
                print('either path/row or date not selected')
                return None
            dDT = self.d[pr]
        b6 = self.open_file(dDT['B6']).astype(np.float32)
        b7 = self.open_file(dDT['B7']).astype(np.float32)
        c = np.polyfit(b6.flatten(), b7.flatten(), 1)
        methane = ((c[0]*b6 + c[1]) - b7)
        dim = methane.shape
        methane = methane.flatten() - methane.min()
        pct = np.cumsum(np.bincount(methane.astype(np.int64)))/methane.size
        r = [np.argmin(pct < 0.02), np.argmax(pct > 0.98)]
        methane[methane < r[0]] = r[0]
        methane[methane > r[1]] = r[1]
        methane = (methane-methane.min())/(methane.max()-methane.min())
        methane = methane.reshape(dim[0],dim[1])
        methane = (methane*65535).astype(np.uint16)
        b6, b7 = None, None
        return methane

    def open_file(self, file):
        self.raster = gdal.Open(file)
        self.srs = osr.SpatialReference()
        self.srs.ImportFromWkt(self.raster.GetProjection())
        npImg = np.array(self.raster.ReadAsArray())
        for iDelete in range(2):
            if (npImg.shape[iDelete] == 7991):
                npImg = np.delete(npImg, (0), axis=(1-iDelete))
        return npImg

    def parse(self, folder=None):
        print(f'parsing folder: {self.dir}')
        self.d.clear()
        rexB = re.compile('_B.')
        rexTIF = re.compile('.tif')
        for basePR in os.listdir(self.dir):
            print(f" path/row: {basePR}")
            dPR = {}
            dirPR = os.path.join(self.dir, basePR)
            if not os.path.isdir(dirPR):
                continue
            for baseDT in os.listdir(dirPR):
                print(f"  date: {baseDT}")
                dirDT = os.path.join(dirPR, baseDT)
                if not os.path.isdir(dirDT):
                    continue
                dDT = {}
                for base in os.listdir(dirDT):
                    if ((rexB.search(base) == None) or (rexTIF.search(base.lower()) == None)):
                        continue
                    band = str(f'B{int(base[base.find("_B")+2:base.lower().find(".tif")])}')
                    dDT[band] = os.path.join(dirDT, base)                    
                if (len(dDT) >= 6):
                    dDT['date'] = self.format_date(baseDT)
                    dPR[baseDT] = dDT
            self.d[basePR] = dPR
        self.update_list()

    def set_working_folder(self, dir=None):
        if (dir != None):
            self.dir = dir
            if not os.path.exists(self.dir):
                os.mkdir(self.dir)
            self.parse()

    def signal_clicked_dt(self, event):
        self.update_list()
    # notify the listeners
        if (self.listener != None):
            for listener in self.listener:
                listener.signal_datamanager(event)

    def signal_clicked_pr(self, event):
    # udpate the date list
        self.update_list()
    # notify the listeners
        if (self.listener != None):
            for listener in self.listener:
                listener.signal_datamanager(event)

    def signal_band_changed(self, event):
    # notify the listeners
        if (self.listener != None):
            for listener in self.listener:
                listener.signal_datamanager(event)

    def update_list(self):
        if (self.listPR == None) or (len(self.d) == 0):
            return None
        itemPR = self.listPR.currentItem()
        kPR = list(self.d.keys())
        pr = itemPR.text() if itemPR else kPR[0]
        kDT = list(self.d[pr].keys())
        itemDT = self.listDT.currentItem()
        if (len(kDT) == 0):
            return None
        dt = itemDT.text() if itemDT else kDT[0]
        self.listPR.clear()
        self.listPR.addItems(self.d.keys())
        self.listDT.clear()
        self.listDT.addItems(list(self.d[pr].keys()))
        self.listDT.setCurrentItem(self.listDT.item(0))
        for i in range(len(self.listPR)):
            item = self.listPR.item(i)
            if (item.text() == pr):
                self.listPR.setCurrentItem(item)
                break
        for i in range(len(self.listDT)):
            item = self.listDT.item(i)
            if (item.text() == dt):
                self.listDT.setCurrentItem(item)
                break

def test_data_manager():
    dir = 'C:\\data\\landsat'
    dm = data_manager(working_folder=dir)

if (__name__ == '__main__'):
    test_data_manager()