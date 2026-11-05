"""Independent Analysis section for quantitative tables and spatial profiles."""
from pathlib import Path
import copy
import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QComboBox,QPushButton,
    QLabel,QFileDialog,QSpinBox,QDoubleSpinBox,QLineEdit,QCheckBox,QMessageBox,QScrollArea,QFrame)
from PyQt6.QtCore import Qt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from bactomate.modules.figure_analysis import KINDS,FigureSpec,load_tables,extract_profiles,prepare,draw,export_bundle


class ProfileWorker(QThread):
    ready = pyqtSignal(object)
    failed = pyqtSignal(str)
    def __init__(self, mask, image, options, parent):
        super().__init__(parent); self.mask,self.image,self.options=mask,image,options
    def run(self):
        try:
            import tifffile
            cells,profiles=extract_profiles(tifffile.imread(self.mask),tifffile.imread(self.image),**self.options)
            self.ready.emit({'Cells':cells,'Spatial profiles':profiles})
        except Exception as exc: self.failed.emit(str(exc))


class SquareCanvasHost(QWidget):
    """Keep the live canvas square, including after splitter/window resizing."""
    def __init__(self,canvas):
        super().__init__();self.canvas=canvas;canvas.setParent(self)
        self.setMinimumSize(280,280)
    def resizeEvent(self,event):
        side=min(self.width(),self.height())
        self.canvas.setGeometry((self.width()-side)//2,(self.height()-side)//2,side,side)
        super().resizeEvent(event)


class FigureAnalysisTab(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.tables={}; self.provenance={}; self.snapshot=None; self.worker=None
        self._figure_windows=[]
        outer=QVBoxLayout(self)
        self.import_actions=QWidget()
        actions=QHBoxLayout(self.import_actions)
        actions.setContentsMargins(0,0,0,0)
        for text,callback in [('Load tables (CSV / TSV / XLSX)…',self.open_tables),
                              ('Build profiles from mask + fluorescence…',self.open_profiles)]:
            button=QPushButton(text); button.clicked.connect(callback); actions.addWidget(button)
        outer.addWidget(self.import_actions)
        self.sheet=QComboBox(); self.sheet.currentTextChanged.connect(self.change_sheet)
        self.kind=QComboBox(); self.kind.addItems(KINDS); self.kind.currentTextChanged.connect(self.suggest)
        self.fields={}
        for key,title in [('x','X / measured metric'),('y','Y / cell / time'),('value','Heatmap intensity'),
                          ('group','Group / track ID'),('sort','Demograph sort metric'),('filter_column','Filter column')]:
            combo=QComboBox(); self.fields[key]=combo
        self.filter_value=QLineEdit(); self.filter_value.setPlaceholderText('Exact value, e.g. 1 or GFP')
        self.minimum,self.maximum=QLineEdit(),QLineEdit()
        self.minimum.setPlaceholderText('Optional'); self.maximum.setPlaceholderText('Optional')
        self.bins=QSpinBox(); self.bins.setRange(2,500); self.bins.setValue(40)
        self.title=QLineEdit()
        self.cmap=QComboBox(); self.cmap.addItems(['viridis','magma','inferno','plasma','turbo','cividis','coolwarm','gray'])
        self.normalization=QComboBox(); self.normalization.addItems(['raw','per-cell max','per-cell min-max'])
        self.relative_position=QCheckBox('Convert −1…1 positions to 0…1')
        self.maxima_source=QComboBox();self.maxima_source.addItem('Brightest pixel per cell','maximum');self.maxima_source.addItem('Detected foci','focus')
        self.show_maxima_points=QCheckBox('Show individual maxima');self.show_maxima_points.setChecked(True)
        self.confirm=QCheckBox('Track IDs verified across frames')
        self.confirm.setToolTip('Check only after verifying that these IDs refer to the same cells across frames.')
        self.calibration=QDoubleSpinBox(); self.calibration.setDecimals(6); self.calibration.setRange(.000001,1000); self.calibration.setValue(.108)
        self.method=QComboBox(); self.method.addItems(['auto','medial axis','principal axis'])
        self.sampling=QComboBox();self.sampling.addItem('24 segments','fixed');self.sampling.addItem('Native → 24 positions','native')
        self.orientation=QComboBox(); self.orientation.addItems(['geometric','bright pole'])
        self.demograph_layout=QComboBox()
        self.demograph_layout.addItem('Length-scaled columns (VDemo)','length-scaled columns')
        self.demograph_layout.addItem('Normalized rows','normalized rows')
        self.cell_map_shape=QComboBox();self.cell_map_shape.addItem('Reference cell','capsule');self.cell_map_shape.addItem('Rectangular matrix','rectangle')
        self.map_background=QComboBox();self.map_background.addItems(['white','black'])
        from bactomate.gui.analysis_workspace import AnalysisCards, AnalysisDataWindow, settings_group
        self.advanced_controls=AnalysisCards()
        groups=[
            ('Figure and data', [('Data table',self.sheet),('Figure',self.kind),('Title',self.title)], ''),
            ('Axes and grouping', [('X / measured metric',self.fields['x']),('Y / cell / time',self.fields['y']),
                ('Heatmap intensity',self.fields['value']),('Group / track ID',self.fields['group']),('Demograph sort metric',self.fields['sort'])], ''),
            ('Filter observations', [('Filter column',self.fields['filter_column']),('Keep matching value',self.filter_value),
                ('Minimum X',self.minimum),('Maximum X',self.maximum)], 'Exact-value and numeric limits select the observations used to draw the figure. Source tables are not edited.'),
            ('Appearance', [('Histogram bins',self.bins),('Color map',self.cmap),('Map intensity',self.normalization),('',self.relative_position)],
                'Raw intensity keeps the measured values. Per-cell max divides each profile by its maximum; per-cell min-max maps its minimum to 0 and maximum to 1. Missing bins stay missing.'),
            ('Spatial maps and time', [('Demograph layout',self.demograph_layout),('Cell-map shape',self.cell_map_shape),('Background',self.map_background),('Maxima source',self.maxima_source),('',self.show_maxima_points),('',self.confirm)],
                'Kymograph: choose position for X, frame/time for Y, intensity for Value and a verified track ID for Group; filter to one track and source/XY. Normalized cell heatmaps give each occupied cell bin equal weight; counts can differ between bins.'),
            ('Extract cell profiles', [('Calibration (µm / px)',self.calibration),('Profile coordinates',self.method),
                ('Profile sampling',self.sampling),('Profile orientation',self.orientation)],
                'Medial axis follows a pixel skeleton for curved rods; ambiguous or branched axes are refused. Principal axis uses a straight projection. Geometric orientation is not pole age. Bright-pole alignment changes the population average. Calibrate before extraction.')]
        for name,rows,note in groups:
            self.advanced_controls.add_card(settings_group(name,rows,help_text=note))
        self.controls_scroll=QScrollArea(); self.controls_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.controls_scroll.setWidgetResizable(True); self.controls_scroll.setMinimumWidth(0)
        self.controls_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.controls_scroll.setWidget(self.advanced_controls); outer.addWidget(self.controls_scroll,1)
        footer=QVBoxLayout()
        self.advanced_actions=QWidget(); advanced_actions=QHBoxLayout(self.advanced_actions)
        advanced_actions.setContentsMargins(0,0,0,0)
        render=QPushButton('Draw figure'); render.clicked.connect(self.render);advanced_actions.addWidget(render)
        self.export=QPushButton('Export figure + data + code…'); self.export.setEnabled(False); self.export.clicked.connect(self.save_bundle);advanced_actions.addWidget(self.export)
        footer.addWidget(self.advanced_actions)
        common_actions=QHBoxLayout()
        reopen=QPushButton('Show latest figure');reopen.clicked.connect(self.show_latest_figure);common_actions.addWidget(reopen)
        common_actions.addStretch(1)
        self.show_data_table=QCheckBox('Show data table');common_actions.addWidget(self.show_data_table)
        footer.addLayout(common_actions)
        outer.addLayout(footer)
        self.figure=Figure(figsize=(6,6)); self.canvas=FigureCanvasQTAgg(self.figure); self.canvas.setMinimumSize(280,230)
        self.square_canvas=SquareCanvasHost(self.canvas);self.square_canvas.setParent(self)
        self._embedded_figure=self.figure;self._embedded_canvas=self.canvas
        self.square_canvas.hide()
        self.data_table_window=AnalysisDataWindow(self)
        self.preview=self.data_table_window.view
        self.show_data_table.toggled.connect(self._toggle_data_table)
        self.data_table_window.hidden.connect(self._data_table_hidden)
        self.status=QLabel('Load analysis results or extract real spatial profiles to start.'); self.status.setWordWrap(True); outer.addWidget(self.status)
        for combo in [self.kind,*self.fields.values(),self.cmap,self.normalization]: combo.currentTextChanged.connect(self.mark_dirty)
        for edit in [self.title,self.minimum,self.maximum,self.filter_value]: edit.textChanged.connect(self.mark_dirty)
        self.relative_position.toggled.connect(self.mark_dirty);self.show_maxima_points.toggled.connect(self.mark_dirty)
        self.maxima_source.currentIndexChanged.connect(self.mark_dirty)
        self.bins.valueChanged.connect(self.mark_dirty); self.confirm.toggled.connect(self.mark_dirty)

    def _toggle_data_table(self, checked):
        if checked:
            self.data_table_window.set_tables(self.sheet.currentText())
            self.data_table_window.show();self.data_table_window.raise_();self.data_table_window.activateWindow()
        else:
            self.data_table_window.hide()

    def _data_table_hidden(self):
        from PyQt6 import sip
        if sip.isdeleted(self.show_data_table):return
        self.show_data_table.blockSignals(True)
        self.show_data_table.setChecked(False)
        self.show_data_table.blockSignals(False)

    def mark_dirty(self,*_):
        self.export.setEnabled(False)

    def open_tables(self):
        paths,_=QFileDialog.getOpenFileNames(self,'Load analysis tables','','Tables (*.csv *.tsv *.xlsx *.xlsm)')
        if not paths:return
        try:
            tables={}
            for path in paths:
                for name,table in load_tables(path).items(): tables[f'{Path(path).name} / {name}']=table
            pools={}
            for name,table in tables.items():
                pools.setdefault(tuple(table.columns),[]).append((name,table))
            for number,entries in enumerate(pools.values(),1):
                if len(entries)>1:
                    frames=[]
                    for name,table in entries:
                        frame=table.copy(); frame['source_table']=name; frames.append(frame)
                    tables[f'Pooled matching columns / {number}']=pd.concat(frames,ignore_index=True)
            self.set_tables(tables,dict(files=paths))
        except Exception as exc: QMessageBox.warning(self,'Cannot load tables',str(exc))

    def set_tables(self,tables,provenance):
        self.tables=tables; self.provenance=provenance
        self.sheet.clear(); self.sheet.addItems(list(tables)); self.change_sheet()

    def change_sheet(self,*_):
        self.mark_dirty()
        table=self.tables.get(self.sheet.currentText())
        self.data_table_window.set_tables(self.sheet.currentText())
        if table is None:return
        columns=list(table.columns)
        for combo in self.fields.values():
            combo.clear(); combo.addItem(''); combo.addItems(columns)
        self.status.setText(f'{len(table):,} rows · {len(columns)} columns. Figures open in separate windows. Show data table opens the read-only source values.')
        self.suggest()

    def suggest(self,*_):
        table=self.tables.get(self.sheet.currentText())
        if table is None:return
        numeric=list(table.select_dtypes(include='number').columns)
        default_x=next((c for c in numeric if 'area' in c.lower()),numeric[0] if numeric else '')
        defaults=dict(x=default_x,y=numeric[1] if len(numeric)>1 else '')
        kind=self.kind.currentText()
        if kind in ('Demograph','Kymograph','Normalized cell heatmap'):
            defaults=dict(x='position',value='intensity',y='object_key' if kind=='Demograph' else ('frame' if kind=='Kymograph' else 'transverse'),sort='length_um' if kind=='Demograph' else '',group='cell_id' if kind=='Kymograph' else '')
        if kind=='Normalized cell heatmap' and {'relative_width','relative_position'}.issubset(table):
            defaults=dict(x='relative_width',y='relative_position',value='intensity',sort='',group='')
        if kind=='Demograph' and 'axis_length_um' in table:defaults['sort']='axis_length_um'
        if kind=='Maxima map':defaults=dict(x='relative_width',y='relative_position',value='intensity',group='',sort='')
        for key,value in defaults.items():
            if value in table.columns or not value:self.fields[key].setCurrentText(value)

    def open_profiles(self):
        if self.worker is not None and self.worker.isRunning():return
        mask,_=QFileDialog.getOpenFileName(self,'Choose one label mask/XY (TYX)','','TIFF (*.tif *.tiff)')
        if not mask:return
        image,_=QFileDialog.getOpenFileName(self,'Choose matching fluorescence channel (TYX)','','TIFF (*.tif *.tiff)')
        if not image:return
        options=dict(pixel_size=self.calibration.value(),source=Path(mask).stem,orientation=self.orientation.currentText(),method=self.method.currentText(),sampling=self.sampling.currentData())
        provenance=dict(mask=str(Path(mask).resolve()),image=str(Path(image).resolve()),**options)
        self.worker=ProfileWorker(mask,image,options,self)
        self.worker.ready.connect(lambda tables:self.set_tables(tables,provenance))
        self.worker.failed.connect(lambda msg:QMessageBox.warning(self,'Cannot build profiles',msg))
        self.status.setText('Building cell profiles from real pixels…'); self.worker.start()

    def render(self):
        try:
            table=self.tables.get(self.sheet.currentText())
            if table is None:raise ValueError('Load a table first.')
            spec=FigureSpec(kind=self.kind.currentText(),**{key:c.currentText() for key,c in self.fields.items()},
                filter_value=self.filter_value.text(),minimum=float(self.minimum.text()) if self.minimum.text().strip() else None,
                maximum=float(self.maximum.text()) if self.maximum.text().strip() else None,bins=self.bins.value(),
                title=getattr(self,'_guided_title',None) or self.title.text(),cmap=self.cmap.currentText(),track_confirmed=self.confirm.isChecked(),normalization=self.normalization.currentText(),replicate=getattr(self,'_guided_replicate',''),relative_position=self.relative_position.isChecked(),
                maxima_profile=self.maxima_source.currentData(),show_points=self.show_maxima_points.isChecked(),
                demograph_layout=self.demograph_layout.currentData(),cell_map_shape=self.cell_map_shape.currentData(),map_background=self.map_background.currentText())
            self.plot_table(table,spec,self.provenance)
        except Exception as exc:
            self.mark_dirty(); QMessageBox.warning(self,'Cannot draw figure',str(exc))

    def plot_table(self,table,spec,provenance):
        used,plot,labels=prepare(table,spec)
        if hasattr(self,'display_labels'):labels=self.display_labels(labels)
        from bactomate.gui.publication_figure_window import PublicationFigureWindow
        window=PublicationFigureWindow(self,table,spec,dict(provenance,table=self.sheet.currentText()),labels)
        self._figure_windows.append(window)
        self.figure,self.canvas=window.figure,window.canvas
        self.snapshot=window.snapshot()
        from PyQt6.QtCore import QTimer
        window.bring_to_front()
        QTimer.singleShot(0,lambda:window.bring_to_front(deferred=True))
        self.export.setEnabled(True)
        self.status.setText(f'{len(used):,} source rows used. Export includes source data, plotted values, square figures and Python/R/MATLAB code.')

    def show_latest_figure(self):
        if self._figure_windows:
            window=self._figure_windows[-1];window.show();window.raise_();window.activateWindow()

    def close_figure_windows(self):
        for window in self._figure_windows:
            window._allow_close=True;window.close();window.deleteLater()
        self._figure_windows=[]
        self.figure,self.canvas=self._embedded_figure,self._embedded_canvas

    def save_bundle(self):
        if self.snapshot is None or not self.export.isEnabled():return
        root=QFileDialog.getExistingDirectory(self,'Choose parent folder for a new figure bundle')
        if not root:return
        try:
            from datetime import datetime
            folder=Path(root)/('figure_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
            used,plot,spec,labels,provenance=self.snapshot
            export_bundle(folder,self.figure,used,plot,spec,labels,provenance=provenance,
                native_profiles=self._figure_windows[-1].source.query("profile == 'native longitudinal'") if self._figure_windows and 'profile' in self._figure_windows[-1].source else None)
            self.status.setText(f'Figure, table and scripts exported to {folder}')
        except Exception as exc:QMessageBox.warning(self,'Export failed',str(exc))

    def closeEvent(self,event):
        if self.worker is not None and self.worker.isRunning():
            QMessageBox.information(self,'Profile extraction running','Wait for profile extraction to finish before closing.')
            event.ignore(); return
        self.close_figure_windows()
        self.show_data_table.setChecked(False)
        super().closeEvent(event)
