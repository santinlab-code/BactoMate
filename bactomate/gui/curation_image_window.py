"""Detachable Filtering canvas and keyboard/table selection feedback."""
import numpy as np
from PyQt6.QtCore import Qt, QEvent, QObject
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QLabel


class _ImageWindow(QDialog):
    def closeEvent(self, event):
        self.controller.attach()
        event.ignore()


class CurationImageWindow(QObject):
    def __init__(self, preview, panel, mask):
        super().__init__(preview)
        self.preview, self.panel, self.mask = preview, panel, mask
        self.canvas = preview.canvas
        self.home = self.canvas.parentWidget()
        self.layout = self.home.layout()
        self.index = self.layout.indexOf(self.canvas)
        self.window = _ImageWindow(preview, Qt.WindowType.Window)
        self.window.controller = self
        self.window.setWindowTitle('Filtering — image (click to select; Delete to exclude)')
        self.window.resize(1000, 800)
        layout = QVBoxLayout(self.window)
        row = QHBoxLayout()
        row.addWidget(QLabel('Select objects:'))
        self.kind = QComboBox()
        self.kind.addItems(['Cells', 'Foci — current channel'])
        self.kind.currentIndexChanged.connect(panel.kind.setCurrentIndex)
        panel.kind.currentIndexChanged.connect(self.kind.setCurrentIndex)
        panel.kind.currentIndexChanged.connect(self.highlight)
        row.addWidget(self.kind)
        attach = QPushButton('Attach image')
        attach.clicked.connect(self.attach)
        row.addWidget(attach)
        layout.addLayout(row)
        layout.addWidget(QLabel('Mouse wheel: zoom · drag: pan · click: select · Delete/Backspace: exclude'))
        self.floating_layout = layout
        self.button = QPushButton('Detach image')
        self.button.clicked.connect(self.detach)
        preview._layout.addWidget(self.button)
        panel.table.itemSelectionChanged.connect(self.highlight)
        panel.foci_table.itemSelectionChanged.connect(self.highlight)
        panel.table.cellClicked.connect(lambda *_: panel.kind.setCurrentIndex(0))
        panel.foci_table.cellClicked.connect(lambda *_: panel.kind.setCurrentIndex(1))
        for widget in (self.canvas, panel.table, panel.foci_table):
            widget.installEventFilter(self)
        preview.installEventFilter(self)
        self.detach()

    def exclude(self):
        table = self.panel.table if self.panel.kind.currentIndex() == 0 else self.panel.foci_table
        if self.panel.isEnabled() and table.selectionModel().selectedRows():
            self.panel.edit(False)

    def detach(self):
        self.floating_layout.addWidget(self.canvas, 1)
        self.button.setEnabled(False)
        self.window.show()
        self.highlight()

    def attach(self):
        self.layout.insertWidget(self.index, self.canvas, 1)
        self.window.hide()
        self.button.setEnabled(True)

    def eventFilter(self, obj, event):
        if obj is not self.preview:
            if event.type() == QEvent.Type.KeyPress and event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
                if obj is self.panel.table:
                    self.panel.kind.setCurrentIndex(0)
                elif obj is self.panel.foci_table:
                    self.panel.kind.setCurrentIndex(1)
                self.exclude()
                return True
            return False
        if event.type() == QEvent.Type.Hide:
            self.window.hide()
        elif event.type() == QEvent.Type.Show and self.canvas.parentWidget() is self.window:
            self.window.show()
        return False

    def highlight(self, *_):
        self.canvas.object_selection_boxes = []
        size = self.canvas._image_size
        if not size:
            self.canvas.update()
            return
        mask = np.asarray(self.mask())
        sx, sy = size[0]/mask.shape[1], size[1]/mask.shape[0]
        cells = self.panel.kind.currentIndex() == 0
        table = self.panel.table if cells else self.panel.foci_table
        for selected in table.selectionModel().selectedRows():
            item = table.item(selected.row(), 0 if cells else 2)
            if item is None:
                continue
            if cells:
                yy, xx = np.where(mask == int(item.text()))
                if not len(xx):
                    continue
                x, y, width, height = xx.min()-1, yy.min()-1, np.ptp(xx)+3, np.ptp(yy)+3
            else:
                coords = item.data(Qt.ItemDataRole.UserRole)
                if not coords:
                    continue
                y, x = coords
                x, y, width, height = x-4, y-4, 9, 9
            self.canvas.object_selection_boxes.append((x*sx, y*sy, width*sx, height*sy))
        self.canvas.update()
