"""Interactive distances on real images, using the analysis pairing engine."""
from pathlib import Path
import numpy as np
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QComboBox,
                             QDoubleSpinBox, QCheckBox, QLabel, QSpinBox)
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.patches import Circle, Rectangle
from bactomate.modules.analysis_coloc import ColocSettings, analyze_colocalization_foci_table


class DistancePreview(QDialog):
    def __init__(self, tab, masks, image, channels, pixel_size=0, backgrounds=None):
        super().__init__(tab)
        self.setWindowTitle('Foci distances — preview')
        self.resize(1050, 800)
        self.masks, self.image, self.channels = masks, image, dict(channels)
        self.pixel_size = pixel_size
        self.backgrounds = backgrounds or {'Phase': image}
        layout = QVBoxLayout(self)
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
        row.addWidget(self.same)
        layout.addLayout(row)
        bg_row = QHBoxLayout()
        bg_row.addWidget(QLabel('Image background'))
        self.background = QComboBox()
        self.background.addItems(list(self.backgrounds))
        bg_row.addWidget(self.background)
        layout.addLayout(bg_row)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.figure = Figure()
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout.addWidget(NavigationToolbar2QT(self.canvas, self))
        layout.addWidget(self.canvas)
        layout.addWidget(QLabel('A: cyan · B: magenta · dashed yellow circle: search radius · '
                                'green circle: threshold · green line: colocalized · orange line: rejected pair.\n'
                                'Click a cell in the overview to zoom. Grid spacing in the zoom: 1 image pixel. '
                                'Values changed here also update Foci analysis.'))
        self.frame.valueChanged.connect(self.populate_cells)
        for widget in (self.cell, self.a, self.b):
            widget.currentIndexChanged.connect(self.redraw)
        for widget in (self.maximum, self.threshold):
            widget.valueChanged.connect(self.redraw)
        self.same.toggled.connect(self.redraw)
        self.background.currentIndexChanged.connect(self.redraw)
        self.canvas.mpl_connect('button_press_event', self.click_cell)
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
        frame = self.frame.value()-1
        mask = self.masks[frame]
        stack = self.backgrounds[self.background.currentText()]
        image = stack[min(frame, len(stack)-1)]
        label = self.cell.currentData()
        self.figure.clear()
        self.overview, zoom = self.figure.subplots(1, 2)
        from bactomate.modules.segmentation_display import label_outlines
        edges = label_outlines(mask)
        lo, hi = np.percentile(image, [1, 99.5])
        for ax in (self.overview, zoom):
            ax.imshow(image, cmap='gray', vmin=lo, vmax=max(hi, lo+1), interpolation='nearest')
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
        self.figure.tight_layout()
        self.canvas.draw_idle()


def open_distance_preview(tab):
    from bactomate.gui.filter_preview_utils import pick_mask_path_for_preview
    from bactomate.gui.tabs._analyze_masks_colocalization import _load_mask_frames
    from bactomate.gui.analysis_workbook import collect_channel_rows_for_mask
    from bactomate.gui.analysis_visualization import resolve_phase_image_for_mask
    from bactomate.gui.utils import safe_imread
    path = pick_mask_path_for_preview(tab, tab.file_path.text())
    if path is None:
        return
    path = Path(path)
    if tab.use_filtered_masks_cb.isChecked():
        from bactomate.gui.artifact_paths import filtered_mask_path_for_mask
        filtered = filtered_mask_path_for_mask(path)
        if filtered.exists():
            path = filtered
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
    dlg = DistancePreview(tab, masks, image, channels, pixel_size, backgrounds)
    tab._distance_preview = dlg
    dlg.show()
