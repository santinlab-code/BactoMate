"""Interactive distances on real images, using the analysis pairing engine."""
from pathlib import Path
import numpy as np
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QComboBox,
                             QDoubleSpinBox, QCheckBox, QLabel, QSpinBox,
                             QPushButton, QToolButton, QMenu, QMessageBox)
from PyQt6.QtGui import QAction, QShortcut, QKeySequence
from PyQt6.QtCore import Qt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.patches import Circle, Rectangle
from bactomate.modules.analysis_coloc import ColocSettings, analyze_colocalization_foci_table


class PreviewToolbar(NavigationToolbar2QT):
    # History arrows are replaced by explicit cell navigation.
    toolitems = tuple(item for item in NavigationToolbar2QT.toolitems
                      if item[0] not in ('Home', 'Back', 'Forward', 'Pan', 'Zoom'))


class DistancePreview(QDialog):
    def __init__(self, tab, masks, image, channels, pixel_size=0, backgrounds=None, datasets=None, dataset_loader=None, current_path=None):
        super().__init__(tab)
        self.setWindowTitle('Foci distances — preview')
        self.resize(1050, 800)
        self.masks, self.image, self.channels = masks, image, dict(channels)
        self.pixel_size = pixel_size
        self.backgrounds = backgrounds or {'Phase': image}
        self.dataset_loader = dataset_loader
        self.current_path = current_path
        self._view_key = None
        self._drag_state = None
        self.layer_actions, self.luts = {}, {}
        layout = QVBoxLayout(self)
        mask_row = QHBoxLayout()
        mask_row.addWidget(QLabel('Mask / XY position'))
        self.mask_selector = QComboBox()
        for path in datasets or []:
            self.mask_selector.addItem(Path(path).name, path)
        if current_path is not None:
            self.mask_selector.setCurrentIndex(self.mask_selector.findData(current_path))
        self.mask_selector.setEnabled(self.mask_selector.count() > 1)
        mask_row.addWidget(self.mask_selector, 1)
        layout.addLayout(mask_row)
        row = QHBoxLayout()
        self.frame = QSpinBox()
        self.frame.setRange(1, max(masks)+1)
        self.cell = QComboBox()
        self.a, self.b = QComboBox(), QComboBox()
        for combo in (self.a, self.b):
            combo.addItems(list(self.channels))
        if self.b.count() > 1:
            self.b.setCurrentIndex(1)
        self.maximum, self.threshold = QDoubleSpinBox(), QDoubleSpinBox()
        for widget, source in ((self.maximum, tab.coloc_merge_max_distance),
                               (self.threshold, tab.coloc_merge_threshold)):
            widget.setRange(source.minimum(), source.maximum())
            widget.setDecimals(1)
            widget.setSuffix(' px')
            widget.setValue(source.value())
            widget.valueChanged.connect(source.setValue)
            source.valueChanged.connect(widget.setValue)
        self.same = QCheckBox('Same cell only')
        self.same.setChecked(tab.coloc_merge_same_cell_only.isChecked())
        self.same.toggled.connect(tab.coloc_merge_same_cell_only.setChecked)
        tab.coloc_merge_same_cell_only.toggled.connect(self.same.setChecked)
        for name, widget in [('Frame', self.frame), ('Cell', self.cell), ('A', self.a), ('B', self.b),
                             ('Max distance', self.maximum), ('Threshold', self.threshold)]:
            row.addWidget(QLabel(name))
            row.addWidget(widget)
            if name in ('Max distance', 'Threshold'):
                from bactomate.gui.widgets import create_info_icon
                help_text = (
                    'Max distance: search radius in image pixels between focus centers in channels A and B. '
                    'Only partners inside this radius can be matched. Pairing is one-to-one. '
                    'Same cell only restricts matching to foci assigned to the same cell.'
                    if name == 'Max distance' else
                    'Threshold: maximum center-to-center distance in image pixels for a matched pair '
                    'to count as colocalized. A pair above this threshold stays matched but is not '
                    'colocalized. Increasing Threshold beyond Max distance cannot recover unsearched pairs. '
                    'These circles show distances, not focus size.')
                row.addWidget(create_info_icon(help_text, parent_widget=self, compact=True))
        row.addWidget(self.same)
        layout.addLayout(row)
        bg_row = QHBoxLayout()
        self.layers_button = QToolButton()
        self.layers_button.setText('Images / channels…')
        self.layers_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.layers_menu = QMenu(self.layers_button)
        self.layers_button.setMenu(self.layers_menu)
        bg_row.addWidget(self.layers_button)
        bg_row.addWidget(QLabel('LUT channel'))
        self.lut_channel = QComboBox()
        bg_row.addWidget(self.lut_channel)
        auto = QPushButton('Auto LUT')
        auto.clicked.connect(self._auto_lut)
        bg_row.addWidget(auto)
        self.lut_channel.currentTextChanged.connect(self._show_lut)
        from bactomate.gui.preview.preview_window import HistogramLUTWidget, CollapsibleSection
        self.lut_widget = HistogramLUTWidget(self)
        self.lut_widget.lut_changed.connect(self._edit_lut)
        self._populate_layers()
        layout.addLayout(bg_row)
        self.lut_section = CollapsibleSection('LUTs', self.lut_widget, expanded=True, compact=True)
        layout.addWidget(self.lut_section)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.figure = Figure()
        self.canvas = FigureCanvasQTAgg(self.figure)
        nav_row = QHBoxLayout()
        self.previous_cell, self.next_cell = QPushButton('← Cell'), QPushButton('Cell →')
        self.previous_cell.clicked.connect(lambda: self.step_cell(-1))
        self.next_cell.clicked.connect(lambda: self.step_cell(1))
        nav_row.addWidget(self.previous_cell)
        nav_row.addWidget(self.next_cell)
        nav_row.addWidget(PreviewToolbar(self.canvas, self), 1)
        layout.addLayout(nav_row)
        for key, step in (('Left', -1), ('Right', 1)):
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(lambda delta=step: self.step_cell(delta))
        layout.addWidget(self.canvas)
        layout.addWidget(QLabel('A: cyan · B: magenta · dashed yellow circle: search radius · '
                                'green circle: threshold · green line: colocalized · orange line: rejected pair.\n'
                                'Click a cell in the overview to zoom. Grid spacing in the zoom: 1 image pixel. '
                                'Scroll over either image to zoom at the pointer. Hold left click and drag to move. '
                                'Values changed here also update Foci analysis.'))
        self.frame.valueChanged.connect(self._show_lut)
        self.frame.valueChanged.connect(self.populate_cells)
        for widget in (self.cell, self.a, self.b):
            widget.currentIndexChanged.connect(self.redraw)
        for widget in (self.maximum, self.threshold):
            widget.valueChanged.connect(self.redraw)
        self.same.toggled.connect(self.redraw)
        self.mask_selector.currentIndexChanged.connect(self._switch_dataset)
        self.canvas.mpl_connect('scroll_event', self.scroll_zoom)
        self.canvas.mpl_connect('button_press_event', self._mouse_press)
        self.canvas.mpl_connect('motion_notify_event', self._mouse_move)
        self.canvas.mpl_connect('button_release_event', self._mouse_release)
        self.populate_cells()

    def _plane(self, name):
        stack = self.backgrounds[name]
        return np.asarray(stack[min(self.frame.value()-1, len(stack)-1)])

    def _populate_layers(self):
        self.layers_menu.clear()
        self.layer_actions, self.luts = {}, {}
        self.lut_channel.blockSignals(True)
        self.lut_channel.clear()
        for i, name in enumerate(self.backgrounds):
            action = QAction(name, self.layers_menu)
            action.setCheckable(True)
            action.setChecked(i == 0)
            action.toggled.connect(lambda *_: self.redraw())
            self.layers_menu.addAction(action)
            self.layer_actions[name] = action
            lo, hi = np.percentile(self._plane(name), [1, 99.5])
            self.luts[name] = [float(lo), float(max(hi, lo+1)),
                               'Gray' if i == 0 else ('Green' if i % 2 else 'Magenta')]
            self.lut_channel.addItem(name)
        self.lut_channel.blockSignals(False)
        self._show_lut()

    def _show_lut(self, *_):
        lut = self.luts.get(self.lut_channel.currentText())
        if lut is None:
            return
        self.lut_widget.blockSignals(True)
        self.lut_widget.set_lut(lut[0], lut[1])
        self.lut_widget.set_frame(self._plane(self.lut_channel.currentText()), preserve_user_lut=True)
        self.lut_widget.blockSignals(False)

    def _edit_lut(self, lo, hi):
        name = self.lut_channel.currentText()
        if name not in self.luts or hi <= lo:
            return
        self.luts[name][:2] = [lo, hi]
        self.redraw()

    def _auto_lut(self):
        name = self.lut_channel.currentText()
        lo, hi = np.percentile(self._plane(name), [1, 99.5])
        self.luts[name][:2] = [float(lo), float(max(hi, lo+1))]
        self._show_lut()
        self.redraw()

    def _composite(self, shape):
        colors = {'Gray': (1, 1, 1), 'Green': (0, 1, 0), 'Magenta': (1, 0, 1),
                  'Cyan': (0, 1, 1), 'Red': (1, 0, 0), 'Blue': (0, 0, 1), 'Yellow': (1, 1, 0)}
        rgb = np.zeros((*shape, 3), dtype=float)
        for name, action in self.layer_actions.items():
            if action.isChecked():
                lo, hi, color = self.luts[name]
                plane = np.nan_to_num(np.asarray(self._plane(name), dtype=float))
                signal = np.clip((plane-lo)/(hi-lo), 0, 1)
                rgb += signal[..., None] * colors[color]
        return np.clip(rgb, 0, 1)

    def step_cell(self, delta):
        index = self.cell.currentIndex() + delta
        if 0 <= index < self.cell.count():
            self.cell.setCurrentIndex(index)

    def scroll_zoom(self, event):
        if event.inaxes not in self.figure.axes or event.xdata is None or event.ydata is None:
            return
        ax = event.inaxes
        scale = 1.05 ** (-max(-1.0, min(1.0, event.step)))
        xlim, ylim = ax.get_xlim(), ax.get_ylim()
        # Preserve image orientation and center the scale on the pointer.
        if not (1 <= abs(xlim[1]-xlim[0])*scale <= self.masks[self.frame.value()-1].shape[1]*10):
            return
        ax.set_xlim(*(event.xdata + (v-event.xdata)*scale for v in xlim))
        ax.set_ylim(*(event.ydata + (v-event.ydata)*scale for v in ylim))
        self.canvas.draw_idle()

    def _switch_dataset(self, index):
        path = self.mask_selector.itemData(index)
        if self.dataset_loader is None or path == self.current_path:
            return
        try:
            data = self.dataset_loader(path)
        except Exception as exc:
            QMessageBox.warning(self, 'Cannot load mask / XY', str(exc))
            self.mask_selector.blockSignals(True)
            self.mask_selector.setCurrentIndex(self.mask_selector.findData(self.current_path))
            self.mask_selector.blockSignals(False)
            return
        self.masks, self.image, channels, self.pixel_size, self.backgrounds = data
        self.channels = dict(channels)
        self.current_path = path
        self.frame.blockSignals(True)
        self.frame.setRange(1, max(self.masks)+1)
        self.frame.setValue(1)
        self.frame.blockSignals(False)
        for combo in (self.a, self.b):
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(list(self.channels))
            combo.blockSignals(False)
        self.b.blockSignals(True)
        self.b.setCurrentIndex(min(1, self.b.count()-1))
        self.b.blockSignals(False)
        self._populate_layers()
        self._view_key = None
        self.populate_cells()

    def populate_cells(self):
        mask = self.masks[self.frame.value()-1]
        self.cell.blockSignals(True)
        self.cell.clear()
        for label in np.unique(mask):
            if label > 0:
                self.cell.addItem(str(label), int(label))
        # Start near a detected focus when available.
        for rows in self.channels.values():
            candidate = next((int(r.get('cell_id', 0) or 0) for r in rows
                              if int(r.get('frame', 0)) == self.frame.value()-1), 0)
            idx = self.cell.findData(candidate)
            if idx >= 0:
                self.cell.setCurrentIndex(idx)
                break
        self.cell.blockSignals(False)
        self.redraw()

    def _mouse_press(self, event):
        if event.button != 1 or event.inaxes not in self.figure.axes:
            return
        self._drag_state = dict(ax=event.inaxes, x=event.x, y=event.y,
                                xlim=event.inaxes.get_xlim(), ylim=event.inaxes.get_ylim(),
                                moved=False)

    def _mouse_move(self, event):
        state = self._drag_state
        if state is None:
            return
        ax = state['ax']
        if ax not in self.figure.axes or event.x is None or event.y is None:
            return
        dx, dy = event.x-state['x'], event.y-state['y']
        if not state['moved'] and abs(dx)+abs(dy) <= 4:
            return
        state['moved'] = True
        xlim, ylim = state['xlim'], state['ylim']
        shift_x = dx*(xlim[1]-xlim[0])/ax.bbox.width
        shift_y = dy*(ylim[1]-ylim[0])/ax.bbox.height
        ax.set_xlim(xlim[0]-shift_x, xlim[1]-shift_x)
        ax.set_ylim(ylim[0]-shift_y, ylim[1]-shift_y)
        self.canvas.setCursor(Qt.CursorShape.ClosedHandCursor)
        self.canvas.draw_idle()

    def _mouse_release(self, event):
        if event.button != 1:
            return
        state, self._drag_state = self._drag_state, None
        self.canvas.unsetCursor()
        if state is not None and not state['moved'] and event.inaxes is state['ax']:
            self.click_cell(event)

    def click_cell(self, event):
        if event.inaxes is not self.overview or event.xdata is None or event.ydata is None:
            return
        mask = self.masks[self.frame.value()-1]
        y, x = int(round(event.ydata)), int(round(event.xdata))
        if 0 <= y < mask.shape[0] and 0 <= x < mask.shape[1]:
            idx = self.cell.findData(int(mask[y, x]))
            if idx >= 0:
                self.cell.setCurrentIndex(idx)

    def redraw(self, *_):
        self._drag_state = None
        frame = self.frame.value()-1
        mask = self.masks[frame]
        image = self._composite(mask.shape)
        label = self.cell.currentData()
        view_key = (self.current_path, frame, label)
        limits = [(ax.get_xlim(), ax.get_ylim()) for ax in self.figure.axes] if self._view_key == view_key else []
        self._view_key = view_key
        self.previous_cell.setEnabled(self.cell.currentIndex() > 0)
        self.next_cell.setEnabled(0 <= self.cell.currentIndex() < self.cell.count()-1)
        self.figure.clear()
        self.overview, zoom = self.figure.subplots(1, 2)
        from bactomate.modules.segmentation_display import label_outlines
        edges = label_outlines(mask)
        for ax in (self.overview, zoom):
            ax.imshow(image, interpolation='nearest')
            rgba = np.zeros((*mask.shape, 4))
            rgba[edges] = (0, 1, 0, 0.8)
            ax.imshow(rgba, interpolation='nearest')
        rows = []
        for name, color in ((self.a.currentText(), 'cyan'), (self.b.currentText(), 'magenta')):
            points = [dict(r, channel_name=name) for r in self.channels.get(name, [])
                      if int(r.get('frame', 0)) == frame]
            rows.extend(points)
            for ax in (self.overview, zoom):
                ax.scatter([r['x'] for r in points], [r['y'] for r in points],
                           s=18, facecolors='none', edgecolors=color)
        self.pairs = []
        if self.a.currentText() != self.b.currentText():
            result = analyze_colocalization_foci_table(rows, ColocSettings(
                coloc_max_distance=self.maximum.value(), coloc_threshold=self.threshold.value(),
                coloc_filter_boundaries=self.same.isChecked()),
                foci_channels=(self.a.currentText(), self.b.currentText()), frame=frame)
            self.pairs = result.pair_records
        for pair in self.pairs:
            y, x = pair['foci_coordinates']
            y2, x2 = pair['colocalized_foci_coordinates']
            zoom.plot([x, x2], [y, y2], color='lime' if pair['is_valid'] else 'orange')
        for r in self.channels.get(self.a.currentText(), []):
            if int(r.get('frame', 0)) == frame and (label is None or int(r.get('cell_id', 0) or 0) == label):
                zoom.add_patch(Circle((r['x'], r['y']), self.maximum.value(), fill=False,
                                      edgecolor='yellow', linestyle='--'))
                zoom.add_patch(Circle((r['x'], r['y']), self.threshold.value(), fill=False, edgecolor='lime'))
        yy, xx = np.where(mask == label) if label is not None else ([], [])
        if len(xx):
            margin = max(5, self.maximum.value()+1)
            x0, x1 = max(-0.5, min(xx)-margin), min(mask.shape[1]-0.5, max(xx)+margin)
            y0, y1 = max(-0.5, min(yy)-margin), min(mask.shape[0]-0.5, max(yy)+margin)
            zoom.set_xlim(x0, x1)
            zoom.set_ylim(y1, y0)
            if x1-x0 <= 160 and y1-y0 <= 160:
                zoom.set_xticks(np.arange(np.ceil(x0-0.5)+0.5, x1, 1), minor=True)
                zoom.set_yticks(np.arange(np.ceil(y0-0.5)+0.5, y1, 1), minor=True)
                zoom.grid(which='minor', alpha=0.25)
            zoom.add_patch(Rectangle((x0+1, y1-2), 1, 1, fill=False, edgecolor='white'))
            zoom.text(x0+2.5, y1-1, '1 px', color='white')
        self.overview.set_title('Click a cell')
        zoom.set_title(f'Cell {label} — pixel coordinates')
        valid = sum(bool(p['is_valid']) for p in self.pairs)
        calibration = f'1 px = {self.pixel_size:.4g} µm. ' if self.pixel_size > 0 else ''
        text = f'{calibration}Frame: {valid} colocalized / {len(self.pairs)} matched pairs.'
        if not rows:
            text += ' No detected foci CSV available: showing cells and pixel scale only.'
        if self.threshold.value() > self.maximum.value():
            text += ' Threshold exceeds Max distance: pairs outside the search radius cannot be matched.'
        self.status.setText(text)
        for ax, (xlim, ylim) in zip(self.figure.axes, limits):
            ax.set_xlim(xlim)
            ax.set_ylim(ylim)
        self.figure.tight_layout()
        self.canvas.draw_idle()


def _load_preview_dataset(tab, path):
    from bactomate.gui.tabs._analyze_masks_colocalization import _load_mask_frames
    from bactomate.gui.analysis_workbook import collect_channel_rows_for_mask
    from bactomate.gui.analysis_visualization import resolve_phase_image_for_mask
    from bactomate.gui.utils import safe_imread
    masks = _load_mask_frames(path)
    if not masks:
        raise ValueError('Select a readable segmentation mask first.')
    source = resolve_phase_image_for_mask(path)
    def load_stack(path):
        arr = np.asarray(safe_imread(str(path)))
        if arr.ndim == 2:
            arr = arr[None]
        if arr.ndim != 3 or arr.shape[-2:] != next(iter(masks.values())).shape:
            raise ValueError(f'Image and mask dimensions do not match: {path}')
        return arr
    image = load_stack(source) if source else np.stack(list(masks.values()))
    channels, _, _, artifacts = collect_channel_rows_for_mask(tab, path,
        prefer_filtered=tab.use_filtered_masks_cb.isChecked())
    backgrounds = {'Phase' if source else 'Mask (phase image unavailable)': image}
    for artifact in artifacts:
        backgrounds[artifact.channel_label] = load_stack(artifact.foci_stack)
    from bactomate.gui.filter_preview_utils import short_foci_stack_label
    known = {Path(a.foci_stack).resolve() for a in artifacts}
    for stack_path in tab._resolve_foci_paths_for_mask(path):
        if Path(stack_path).resolve() not in known:
            name = short_foci_stack_label(Path(stack_path))
            backgrounds[name] = load_stack(stack_path)
            channels.append((name, []))
    pixel_size = 0
    if source:
        import tifffile
        from bactomate.modules.tiff_metadata import _pixel_size_um_from_tiff_page
        with tifffile.TiffFile(source) as tf:
            pixel_size = _pixel_size_um_from_tiff_page(tf.pages[0], tf.imagej_metadata)
    return masks, image, channels, pixel_size or 0, backgrounds


def open_distance_preview(tab):
    from bactomate.gui.filter_preview_utils import pick_mask_path_for_preview
    from bactomate.gui.artifact_paths import (filtered_mask_path_for_mask,
        dedupe_mask_paths_prefer_filtered, is_cell_mask_tiff)
    path = pick_mask_path_for_preview(tab, tab.file_path.text())
    if path is None:
        return
    def selected_variant(mask_path):
        mask_path = Path(mask_path)
        if tab.use_filtered_masks_cb.isChecked():
            filtered = filtered_mask_path_for_mask(mask_path)
            if filtered.exists():
                return filtered
        return mask_path
    path = selected_variant(path)
    candidates = [selected_variant(p) for p in tab._get_mask_files_for_feedback()
                  if is_cell_mask_tiff(Path(p))]
    candidates = dedupe_mask_paths_prefer_filtered(candidates + [path])
    if path not in candidates:
        candidates.insert(0, path)
    data = _load_preview_dataset(tab, path)
    dlg = DistancePreview(tab, *data[:3], pixel_size=data[3], backgrounds=data[4],
                          datasets=candidates, dataset_loader=lambda p: _load_preview_dataset(tab, p),
                          current_path=path)
    tab._distance_preview = dlg
    dlg.show()
