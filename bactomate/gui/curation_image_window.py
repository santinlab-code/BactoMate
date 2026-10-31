"""Detachable Filtering canvas and keyboard/table selection feedback."""
import numpy as np
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtWidgets import QLabel, QPushButton


from bactomate.gui.preview.detachable_image import DetachablePreviewImage


class CurationImageWindow(DetachablePreviewImage):
    def __init__(self, preview, panel, mask):
        self.panel, self.mask = panel, mask
        super().__init__(preview, title='Filtering — image (click to select; Delete to exclude)',
                         extra_widgets=(panel.manual_controls,))
        self.kind = panel.kind
        self.outline_color=QPushButton('Contour color…')
        self.outline_color.clicked.connect(lambda: self.preview._pf_choose_outline_color())
        self.controls_layout.addWidget(self.outline_color)
        panel.kind.currentIndexChanged.connect(self.highlight)
        self.floating_layout.insertWidget(1, QLabel(
            'Left click: select · right click: keep · Delete: exclude · foci: green kept / red excluded · cells: kept contours'))
        panel.table.itemSelectionChanged.connect(self.highlight)
        panel.foci_table.itemSelectionChanged.connect(self.highlight)
        panel.table.cellClicked.connect(lambda *_: panel.kind.setCurrentIndex(0))
        panel.foci_table.cellClicked.connect(lambda *_: panel.kind.setCurrentIndex(1))
        for widget in (self.canvas, panel.table, panel.foci_table):
            widget.installEventFilter(self)
        self.detach()

    def detach(self):
        super().detach()
        self.preview._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.preview.setMinimumHeight(0)
        self.preview.updateGeometry()

    def attach(self):
        super().attach()
        self.preview._layout.setAlignment(Qt.AlignmentFlag(0))
        self.preview.updateGeometry()

    def exclude(self):
        table = self.panel.table if self.panel.kind.currentIndex() == 0 else self.panel.foci_table
        if self.panel.isEnabled() and table.selectionModel().selectedRows():
            self.panel.edit(False)

    def keep_at(self, position):
        if not self.panel.isEnabled():
            return
        choose_kind=getattr(self.preview,'_pf_image_object_kind',None)
        if choose_kind is not None:
            kind=choose_kind()
            if kind is not None:self.panel.kind.setCurrentIndex(kind)
        image_pos = self.canvas._widget_to_image(position)
        size = self.canvas._image_size
        if image_pos is None or not size:
            return
        mask = np.asarray(self.mask())
        x, y = image_pos[0]*mask.shape[1]/size[0], image_pos[1]*mask.shape[0]/size[1]
        cells = self.panel.kind.currentIndex() == 0
        table = self.panel.table if cells else self.panel.foci_table
        row = None
        if cells:
            label = int(mask[int(y), int(x)])
            row = next((i for i in range(table.rowCount())
                        if int(table.item(i, 0).text()) == label), None)
        else:
            best = (float('inf'), None)
            for i in range(table.rowCount()):
                item = table.item(i, 2)
                coords = item.data(Qt.ItemDataRole.UserRole) if item else None
                if coords:
                    distance = (float(coords[0])-y)**2 + (float(coords[1])-x)**2
                    if distance < best[0]:
                        best = (distance, i)
            radius=max(2.0,5.0/max(self.canvas.view_scale(),1e-6))*mask.shape[1]/size[0]
            if best[0] <= radius**2:
                row = best[1]
        if row is None:
            return
        # A right click inside a multi-selection keeps that entire selection.
        if row not in {i.row() for i in table.selectionModel().selectedRows()}:
            self.canvas.clicked_image.emit(*image_pos)
        self.canvas.setFocus()
        self.panel.edit(True)

    def eventFilter(self, obj, event):
        if not hasattr(self, 'preview'):
            return False
        if obj is not self.preview:
            if (obj is self.canvas and event.type() == QEvent.Type.MouseButtonPress
                    and event.button() == Qt.MouseButton.RightButton):
                self.keep_at(event.position())
                return True
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
