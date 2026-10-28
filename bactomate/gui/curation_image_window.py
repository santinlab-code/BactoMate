"""Detachable Filtering canvas and keyboard/table selection feedback."""
import numpy as np
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtWidgets import QComboBox, QLabel


from bactomate.gui.preview.detachable_image import DetachablePreviewImage


class CurationImageWindow(DetachablePreviewImage):
    def __init__(self, preview, panel, mask):
        self.panel, self.mask = panel, mask
        super().__init__(preview, title='Filtering — image (click to select; Delete to exclude)')
        self.kind = QComboBox()
        self.kind.addItems(['Cells', 'Foci — current channel'])
        self.kind.currentIndexChanged.connect(panel.kind.setCurrentIndex)
        panel.kind.currentIndexChanged.connect(self.kind.setCurrentIndex)
        panel.kind.currentIndexChanged.connect(self.highlight)
        self.controls_layout.insertWidget(0, QLabel('Select objects:'))
        self.controls_layout.insertWidget(1, self.kind)
        self.floating_layout.insertWidget(1, QLabel('Click: select · Delete/Backspace: exclude'))
        panel.table.itemSelectionChanged.connect(self.highlight)
        panel.foci_table.itemSelectionChanged.connect(self.highlight)
        panel.table.cellClicked.connect(lambda *_: panel.kind.setCurrentIndex(0))
        panel.foci_table.cellClicked.connect(lambda *_: panel.kind.setCurrentIndex(1))
        for widget in (self.canvas, panel.table, panel.foci_table):
            widget.installEventFilter(self)
        self.detach()

    def exclude(self):
        table = self.panel.table if self.panel.kind.currentIndex() == 0 else self.panel.foci_table
        if self.panel.isEnabled() and table.selectionModel().selectedRows():
            self.panel.edit(False)

    def eventFilter(self, obj, event):
        if not hasattr(self, 'preview'):
            return False
        if obj is not self.preview:
            if event.type() == QEvent.Type.KeyPress and event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
                if obj is self.panel.table:
                    self.panel.kind.setCurrentIndex(0)
                elif obj is self.panel.foci_table:
                    self.panel.kind.setCurrentIndex(1)
                self.exclude()
                return True
            return False
        return super().eventFilter(obj, event)

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
