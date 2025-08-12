from PyQt6 import QtCore, QtGui, QtWidgets

SCALE_FACTOR = 1.1

class data_view(QtWidgets.QGraphicsView):
    signal_coords_changed = QtCore.pyqtSignal(QtCore.QPoint)
    signal_coords_selected = QtCore.pyqtSignal(QtCore.QPoint)

    #----------------------------------------------------------------------------------------------
    #+
    #-
    def __init__(self, parent):
        super().__init__(parent)
        self._zoom = 0
        self._pinned = False
        self._empty = True
        self._scene = QtWidgets.QGraphicsScene(self)
        self.pixmap_item = QtWidgets.QGraphicsPixmapItem()
        self.pixmap_item.setShapeMode(
            QtWidgets.QGraphicsPixmapItem.ShapeMode.BoundingRectShape)
        self._scene.addItem(self.pixmap_item)
        self.setScene(self._scene)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(30, 30, 30)))
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)

    #----------------------------------------------------------------------------------------------
    #+
    #-
    def get_point(self, pos=None):
        if self.pixmap_item.isUnderMouse():
            if pos is None:
                pos = self.mapFromGlobal(QtGui.QCursor.pos())
            point = self.mapToScene(pos).toPoint()
        else:
            point = QtCore.QPoint()
        return point

    #----------------------------------------------------------------------------------------------
    #+
    #-
    def hasData(self):
        return not self._empty

    #----------------------------------------------------------------------------------------------
    #+
    #-
    def leaveEvent(self, event):
        self.signal_coords_changed.emit(QtCore.QPoint())
        super().leaveEvent(event)

    #----------------------------------------------------------------------------------------------
    #+
    #-
    def mouseMoveEvent(self, event):
        self.update_coordinates(event.position().toPoint())
        super().mouseMoveEvent(event)

    #----------------------------------------------------------------------------------------------
    #+
    #-
    def mousePressEvent(self, event):
        if self.pixmap_item.isUnderMouse():
            self.update_crosshairs(event.position().toPoint())
        self.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)
        return super().mousePressEvent(event)
    
    #----------------------------------------------------------------------------------------------
    #+
    #-
    def mouseReleaseEvent(self, event):
        self.setDragMode(QtWidgets.QGraphicsView.DragMode.NoDrag)
        return super().mouseReleaseEvent(event)

    #----------------------------------------------------------------------------------------------
    #+
    #-
    def reset(self, scale=1):
        print("reset")
        rect = QtCore.QRectF(self.pixmap_item.pixmap().rect())
        if not rect.isNull():
            self.setSceneRect(rect)
            if (scale := max(1, scale)) == 1:
                self._zoom = 0
            if self.hasData():
                unity = self.transform().mapRect(QtCore.QRectF(0, 0, 1, 1))
                self.scale(1 / unity.width(), 1 / unity.height())
                viewrect = self.viewport().rect()
                scenerect = self.transform().mapRect(rect)
                factor = min(viewrect.width() / scenerect.width(),
                             viewrect.height() / scenerect.height()) * scale
                self.scale(factor, factor)
                self.centerOn(self.pixmap_item)
                self.update_coordinates()

    #----------------------------------------------------------------------------------------------
    #+
    #-
    def resizeEvent(self, event):
        super().resizeEvent(event)

    #----------------------------------------------------------------------------------------------
    #+
    #-
    def set_data(self, pixmap=None, reset=False):
        if pixmap and not pixmap.isNull():
            self._empty = False
            self.pixmap_item.setPixmap(pixmap)
        else:
            self._empty = True
            self.setDragMode(QtWidgets.QGraphicsView.DragMode.NoDrag)
            self.pixmap_item.setPixmap(QtGui.QPixmap())
        if (reset):
            self._zoom = 0
            self.reset(SCALE_FACTOR ** self._zoom)

    #----------------------------------------------------------------------------------------------
    #+
    #-
    def update(self):
        super().update()

    #----------------------------------------------------------------------------------------------
    #+
    #-
    def update_coordinates(self, pos=None):
        point = self.get_point(pos=pos)
        self.signal_coords_changed.emit(point)

    #----------------------------------------------------------------------------------------------
    #+
    #-
    def update_crosshairs(self, pos=None):
        point = self.get_point(pos=pos)
        self.signal_coords_selected.emit(point)

    #----------------------------------------------------------------------------------------------
    #+
    #-
    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        self.zoom(delta and delta // abs(delta))

    #----------------------------------------------------------------------------------------------
    #+
    #-
    def zoomLevel(self):
        return self._zoom

    #----------------------------------------------------------------------------------------------
    #+
    #-
    def zoom(self, step):
        zoom = max(0, self._zoom + (step := int(step)))
        if zoom != self._zoom:
            self._zoom = zoom
            if self._zoom > 0:
                if step > 0:
                    factor = SCALE_FACTOR ** step
                else:
                    factor = 1 / SCALE_FACTOR ** abs(step)
                self.scale(factor, factor)
            else:
                self.reset()
