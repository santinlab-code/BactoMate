"""Detachable Filtering canvas and keyboard/table selection feedback."""
import numpy as np
from PyQt6.QtCore import Qt, QEvent, QPointF
from PyQt6.QtWidgets import QLabel, QPushButton, QMenu, QMessageBox


from bactomate.gui.preview.detachable_image import DetachablePreviewImage


class CurationImageWindow(DetachablePreviewImage):
    def __init__(self, preview, panel, mask):
        self.panel, self.mask = panel, mask
        self._polygon=None;self.context_menu=None
        super().__init__(preview, title='Filtering — image (click to select; Delete to exclude)',
                         extra_widgets=(panel.manual_controls,))
        self.kind = panel.kind
        self.outline_color=QPushButton('Contour color…')
        self.outline_color.clicked.connect(lambda: self.preview._pf_choose_outline_color())
        self.controls_layout.addWidget(self.outline_color)
        panel.kind.currentIndexChanged.connect(self.highlight)
        self.floating_layout.insertWidget(1, QLabel(
            'Left click: select · Shift+click: add clicked object · right click: object menu · Delete: exclude'))
        panel.table.itemSelectionChanged.connect(self.highlight)
        panel.foci_table.itemSelectionChanged.connect(self.highlight)
        panel.table.cellClicked.connect(lambda *_: panel.kind.setCurrentIndex(0))
        panel.foci_table.cellClicked.connect(lambda *_: panel.kind.setCurrentIndex(1))
        for widget in (self.canvas, panel.table, panel.foci_table):
            widget.installEventFilter(self)
        self.detach()

    def detach(self):
        super().detach()
        if self.home is not self.preview:
            self.home.hide()
        self.preview._layout.setAlignment(Qt.AlignmentFlag(0))
        self.preview.setMinimumHeight(0)
        self.preview.updateGeometry()

    def attach(self):
        if self.home is not self.preview:
            self.home.show()
        super().attach()
        self.preview._layout.setAlignment(Qt.AlignmentFlag(0))
        self.preview.updateGeometry()

    def exclude(self):
        table = self.panel.table if self.panel.kind.currentIndex() == 0 else self.panel.foci_table
        if self.panel.isEnabled() and table.selectionModel().selectedRows():
            self.panel.edit(False)

    def _native_position(self,position):
        image=self.canvas._widget_to_image(position);size=self.canvas._image_size
        if image is None or not size:return None
        shape=np.asarray(self.mask()).shape
        point=(image[0]*shape[1]/size[0],image[1]*shape[0]/size[1])
        return point if 0<=point[0]<shape[1] and 0<=point[1]<shape[0] else None

    def _target_at(self,position):
        choose_kind=getattr(self.preview,'_pf_image_object_kind',None)
        if choose_kind is not None:
            kind=choose_kind()
            if kind is not None:self.panel.kind.setCurrentIndex(kind)
        point=self._native_position(position)
        if point is None:return None
        x,y=point;mask=np.asarray(self.mask());cells=self.panel.kind.currentIndex()==0
        table=self.panel.table if cells else self.panel.foci_table
        if cells:
            label=int(mask[int(y),int(x)])
            return next((row for row in range(table.rowCount()) if int(table.item(row,0).text())==label),None)
        radius=max(2.,5./max(self.canvas.view_scale(),1e-6))*mask.shape[1]/self.canvas._image_size[0]
        best=(float('inf'),None)
        for row in range(table.rowCount()):
            item=table.item(row,2);coords=item.data(Qt.ItemDataRole.UserRole) if item else None
            if coords:
                distance=(float(coords[0])-y)**2+(float(coords[1])-x)**2
                if distance<best[0]:best=(distance,row)
        return best[1] if best[0]<=radius**2 else None

    def _edit_at(self,position,keep):
        row=self._target_at(position)
        if row is None:
            if keep:self.create_at(position)
            return
        table=self.panel.table if self.panel.kind.currentIndex()==0 else self.panel.foci_table
        if row not in {i.row() for i in table.selectionModel().selectedRows()}:
            from PyQt6.QtCore import QItemSelectionModel
            table.selectionModel().select(table.model().index(row,0),QItemSelectionModel.SelectionFlag.ClearAndSelect|QItemSelectionModel.SelectionFlag.Rows)
        self.canvas.setFocus();self.panel.edit(keep)

    def keep_at(self,position):
        # Explicit API; right clicks themselves only open the menu.
        self._edit_at(position,True)

    def show_object_menu(self,position,global_position):
        if not self.panel.isEnabled() or self._native_position(position) is None:return
        if self.context_menu is not None:self.context_menu.close();self.context_menu.deleteLater()
        menu=QMenu(self.window);self.context_menu=menu
        menu.addAction('Add / keep object',lambda:self._edit_at(position,True))
        remove=menu.addAction('Remove / exclude object',lambda:self._edit_at(position,False))
        remove.setEnabled(self._target_at(position) is not None)
        menu.addSeparator()
        menu.addAction('Create new object here…',lambda:self.create_at(position))
        menu.popup(global_position)

    def create_at(self,position):
        point=self._native_position(position)
        if point is None:return
        if self.panel.kind.currentIndex()==0:
            self._polygon=[point];self._update_polygon()
            self.canvas.setToolTip('New cell: click contour points; double-click or Enter to finish; Escape to cancel.')
            self.canvas.setFocus()
        else:self._create('foci',[point])

    def _create(self,kind,points):
        previous=getattr(self.panel,'pending_action','Apply filters')
        try:
            self.panel.pending_action='Create manual '+('cell' if kind=='cells' else 'focus')
            self.preview._pf_create_object(kind,points)
        except Exception as exc:
            self.panel.pending_action=previous
            QMessageBox.warning(self.window,'Cannot create object',str(exc))

    def _update_polygon(self):
        shape=np.asarray(self.mask()).shape;size=self.canvas._image_size
        self.canvas.manual_polygon=[(x*size[0]/shape[1],y*size[1]/shape[0]) for x,y in self._polygon] if self._polygon else []
        self.canvas.update()

    def _finish_polygon(self):
        points=self._polygon;self._polygon=None;self._update_polygon()
        if points:self._create('cells',points)

    def eventFilter(self,obj,event):
        if not hasattr(self,'preview'):return False
        if obj is self.preview:return super().eventFilter(obj,event)
        if obj is self.canvas:
            if self._polygon is not None:
                if event.type()==QEvent.Type.KeyPress and event.key()==Qt.Key.Key_Escape:
                    self._polygon=None;self._update_polygon();return True
                if event.type()==QEvent.Type.KeyPress and event.key() in (Qt.Key.Key_Enter,Qt.Key.Key_Return):
                    self._finish_polygon();return True
                if event.type()==QEvent.Type.MouseButtonDblClick:
                    self._finish_polygon();return True
                if event.type()==QEvent.Type.MouseButtonPress and event.button()==Qt.MouseButton.LeftButton:
                    point=self._native_position(event.position())
                    if point:self._polygon.append(point);self._update_polygon()
                    return True
            if event.type()==QEvent.Type.MouseButtonPress:
                if event.button()==Qt.MouseButton.RightButton:
                    self.show_object_menu(QPointF(event.position()),event.globalPosition().toPoint());return True
                self.canvas.setProperty('filter_additive_click',bool(event.modifiers()&Qt.KeyboardModifier.ShiftModifier))
        if event.type()==QEvent.Type.KeyPress and event.key() in (Qt.Key.Key_Delete,Qt.Key.Key_Backspace):
            if obj is self.panel.table:self.panel.kind.setCurrentIndex(0)
            elif obj is self.panel.foci_table:self.panel.kind.setCurrentIndex(1)
            self.exclude();return True
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
