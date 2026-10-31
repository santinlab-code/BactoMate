"""Cell table and persisted manual selection controls for Filtering previews."""
import json
import numpy as np
from PyQt6.QtCore import Qt, QItemSelectionModel, pyqtSignal
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                            QTableWidgetItem, QComboBox, QLabel, QPushButton, QMessageBox, QTextEdit)
from bactomate.modules.object_curation import ObjectCuration


class ObjectCurationPanel(QWidget):
    history_updated=pyqtSignal()
    def __init__(self, foci_table, channel, changed, focus_cell, parent=None):
        super().__init__(parent)
        self.foci_table, self.channel = foci_table, channel
        self.changed, self.focus_cell = changed, focus_cell
        self.cur = None
        self.frame = 0
        layout = QVBoxLayout(self)
        self.summary = QLabel('Selection — current frame')
        layout.addWidget(self.summary)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(['Cell ID', 'Selected', 'Area (µm²)', 'Length (µm)', 'Width (µm)', 'X (px)', 'Y (px)'])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        from bactomate.gui.filtering_display import ten_row_table
        ten_row_table(self.table)
        self.table.cellDoubleClicked.connect(self._focus)
        layout.addWidget(self.table)
        self.manual_controls = QWidget(self)
        self.manual_controls.setObjectName("ManualObjectSelection")
        row = QHBoxLayout(self.manual_controls)
        row.setContentsMargins(0, 0, 0, 0)
        self.kind = QComboBox()
        self.kind.addItems(['Cells', 'Foci — current channel'])
        row.addWidget(self.kind)
        for title, keep in [('Keep selected objects', True), ('Exclude selected objects', False),
                            ('Use filters for selected objects', None)]:
            button = QPushButton(title)
            button.clicked.connect(lambda checked=False, k=keep: self.edit(k))
            row.addWidget(button)
        layout.addWidget(self.manual_controls)
        self.history = QComboBox()
        self.history.setMaxVisibleItems(10)
        self.history.setToolTip('History for this segmentation and frame; filter values are shown in the tooltip.')
        layout.addWidget(self.history)
        self.history.currentIndexChanged.connect(self._history_detail)
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setMaximumHeight(90)
        layout.addWidget(self.details)

    def context(self, path, frame, mask, accepted, pixel_size=None):
        from pathlib import Path
        if self.cur is None or self.cur.mask_path != Path(path).resolve():
            self.cur = ObjectCuration(path)
        self.frame = int(frame)
        self.kind.setItemText(1, f'Foci — {self.channel()}')
        labels = set(int(x) for x in np.unique(mask) if x > 0)
        accepted = self.cur.cells(frame, accepted, labels)
        self.summary.setText(f'Frame {frame+1} — {len(accepted)} selected / {len(labels)} segmented cells')
        ps = float(pixel_size) if pixel_size is not None else 0.0
        if not np.isfinite(ps) or ps <= 0:
            ps = 0.0
        self.table.setToolTip(f'Calibration: {ps:g} µm / px' if ps else
                              'Calibration unavailable: physical dimensions cannot be shown.')
        context_key = (str(self.cur.mask_path), frame, frozenset(labels), frozenset(accepted), ps)
        previous_key = getattr(self, '_context_key', None)
        if previous_key == context_key:
            return accepted
        self._context_key = context_key
        chosen = {self.table.item(i.row(), 0).text() for i in self.table.selectionModel().selectedRows()
                  if self.table.item(i.row(), 0)}
        if previous_key is None or previous_key[:2] != context_key[:2]:
            chosen = set()
        self.table.clearSelection()
        self.table.setRowCount(len(labels))
        from skimage.measure import regionprops
        for i, region in enumerate(regionprops(mask)):
            y, x = region.centroid
            values = [region.label, 'Yes' if region.label in accepted else 'No', round(region.area * ps**2, 4) if ps else '—',
                      round(region.major_axis_length * ps, 4) if ps else '—',
                      round(region.minor_axis_length * ps, 4) if ps else '—', round(x, 1), round(y, 1)]
            for j, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.ItemDataRole.UserRole, (int(region.label), float(y), float(x)))
                self.table.setItem(i, j, item)
            if str(region.label) in chosen:
                self.table.selectionModel().select(self.table.model().index(i, 0),
                    QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
        if not any(h['frame'] == frame for h in self.cur.data['history']):
            self.cur.record(frame, len(labels), len(labels), {}, action='Initial segmentation')
        self.refresh_history()
        return accepted

    def refresh_history(self):
        self.history.blockSignals(True)
        self.history.clear()
        for h in self.cur.data['history']:
            if h['frame'] == self.frame:
                text = f"{h['action']}: {h['before']} → {h['selected']} / {h['total']} cells ({h['delta']:+d})"
                foci = ', '.join(f"{k}: {v['selected']}/{v['total']} foci" for k, v in h.get('foci', {}).items())
                self.history.addItem(text + (' | ' + foci if foci else ''), h)
        self.history.setCurrentIndex(self.history.count()-1)
        self.history.blockSignals(False)
        self._history_detail()
        self.history_updated.emit()

    def _history_detail(self, *_):
        h = self.history.currentData()
        self.history.setToolTip(json.dumps(h, indent=2, ensure_ascii=False) if h else '')
        if h:
            filters = '\n'.join(f"{key.replace('_', ' ')}: {value}" for key, value in h['settings'].items()
                                if value is not None and value is not False)
            self.details.setPlainText(f"{h['time']} — {h['action']}\n" + (filters or 'Initial segmentation, no filters'))
        else:
            self.details.clear()

    def _focus(self, row, column):
        item = self.table.item(row, 0)
        if item:
            self.focus_cell(*item.data(Qt.ItemDataRole.UserRole))

    def edit(self, keep):
        if self.cur is None:
            return
        kind = 'cells' if self.kind.currentIndex() == 0 else 'foci'
        table = self.table if kind == 'cells' else self.foci_table
        objects = []
        for selected in table.selectionModel().selectedRows():
            row = selected.row()
            if kind == 'cells':
                objects.append(int(table.item(row, 0).text()))
            else:
                item = table.item(row, 2)
                coords = item.data(Qt.ItemDataRole.UserRole) if item else None
                if coords:
                    objects.append({'y': coords[0], 'x': coords[1]})
        if not objects:
            QMessageBox.information(self, 'Choose objects', 'Select rows in the Cell table or Foci table first.')
            return
        try:
            self.cur.set_objects(kind, self.frame, objects, keep, channel=self.channel())
            self.pending_action = f"{'Keep' if keep is True else 'Exclude' if keep is False else 'Automatic'} {len(objects)} {kind}"
            self.changed()
        except Exception as exc:
            QMessageBox.warning(self, 'Curation could not be saved', str(exc))
