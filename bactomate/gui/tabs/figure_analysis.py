"""Independent Analysis section for quantitative tables and spatial profiles."""
from pathlib import Path
import copy
import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QComboBox,QPushButton,
    QLabel,QFileDialog,QSpinBox,QDoubleSpinBox,QLineEdit,QCheckBox,QMessageBox,QSplitter,
    QTableWidget,QTableWidgetItem,QScrollArea,QGroupBox)
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


class FigureAnalysisTab(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.tables={}; self.provenance={}; self.snapshot=None; self.worker=None
        outer=QVBoxLayout(self)
        actions=QHBoxLayout()
        for text,callback in [('Load tables (CSV / TSV / XLSX)…',self.open_tables),
                              ('Build profiles from mask + fluorescence…',self.open_profiles)]:
            button=QPushButton(text); button.clicked.connect(callback); actions.addWidget(button)
        outer.addLayout(actions)
        split=QSplitter(Qt.Orientation.Horizontal); outer.addWidget(split,1)
        controls=QWidget(); controls.setMinimumWidth(270); form=QFormLayout(controls); form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.sheet=QComboBox(); self.sheet.currentTextChanged.connect(self.change_sheet); form.addRow('Data table',self.sheet)
        self.kind=QComboBox(); self.kind.addItems(KINDS); self.kind.currentTextChanged.connect(self.suggest); form.addRow('Figure',self.kind)
        self.fields={}
        for key,title in [('x','X / measured metric'),('y','Y / cell / time'),('value','Heatmap intensity'),
                          ('group','Group / track ID'),('sort','Demograph sort metric'),('filter_column','Filter column')]:
            combo=QComboBox(); self.fields[key]=combo; form.addRow(title,combo)
        self.filter_value=QLineEdit(); self.filter_value.setPlaceholderText('Exact value, e.g. 1 or GFP'); form.addRow('Keep matching value',self.filter_value)
        self.minimum,self.maximum=QLineEdit(),QLineEdit()
        self.minimum.setPlaceholderText('Optional'); self.maximum.setPlaceholderText('Optional')
        form.addRow('Minimum X',self.minimum); form.addRow('Maximum X',self.maximum)
        self.bins=QSpinBox(); self.bins.setRange(2,500); self.bins.setValue(40); form.addRow('Histogram bins',self.bins)
        self.title=QLineEdit(); form.addRow('Title',self.title)
        self.cmap=QComboBox(); self.cmap.addItems(['viridis','magma','inferno','cividis','coolwarm','gray']); form.addRow('Color map',self.cmap)
        self.normalization=QComboBox(); self.normalization.addItems(['raw','per-cell max','per-cell min-max']); form.addRow('Map intensity',self.normalization)
        self.confirm=QCheckBox('I verified that track IDs persist across frames'); form.addRow(self.confirm)
        self.calibration=QDoubleSpinBox(); self.calibration.setDecimals(6); self.calibration.setRange(.000001,1000); self.calibration.setValue(.108)
        form.addRow('Profiles: µm / px',self.calibration)
        self.method=QComboBox(); self.method.addItems(['medial axis','principal axis']); form.addRow('Profile coordinates',self.method)
        self.orientation=QComboBox(); self.orientation.addItems(['geometric','bright pole']); form.addRow('Profile orientation',self.orientation)
        note=QLabel('Medial-axis mode follows a pixel skeleton for curved rods; ambiguous/branched axes are refused. Principal-axis mode uses a straight projection. Geometric orientation is not pole age. Bright-pole alignment changes the population average. Map intensity controls normalization; raw is the default. Missing bins stay missing. Calibrate before extraction.\n\nKymograph: choose position for X, frame/time for Y, intensity for Value, a verified track ID for Group, then filter to one track and source/XY.\n\nNormalized cell heatmaps average each occupied cell bin equally. Cell counts may differ between bins.'); note.setWordWrap(True); note.setMaximumWidth(340); form.addRow(note)
        render=QPushButton('Draw figure'); render.clicked.connect(self.render); form.addRow(render)
        self.export=QPushButton('Export figure + data + code…'); self.export.setEnabled(False); self.export.clicked.connect(self.save_bundle); form.addRow(self.export)
        scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setMinimumWidth(285); scroll.setMaximumWidth(390); scroll.setWidget(controls); split.addWidget(scroll)
        right=QWidget(); layout=QVBoxLayout(right); split.addWidget(right); split.setStretchFactor(1,3); split.setSizes([330,850])
        self.figure=Figure(); self.canvas=FigureCanvasQTAgg(self.figure); self.canvas.setMinimumSize(280,230)
        layout.addWidget(NavigationToolbar2QT(self.canvas,self)); layout.addWidget(self.canvas,3)
        self.preview=QTableWidget(); self.preview.setMaximumHeight(170); self.preview.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers); layout.addWidget(self.preview)
        self.status=QLabel('Load analysis results or extract real spatial profiles to start.'); self.status.setWordWrap(True); outer.addWidget(self.status)
        for combo in [self.kind,*self.fields.values(),self.cmap,self.normalization]: combo.currentTextChanged.connect(self.mark_dirty)
        for edit in [self.title,self.minimum,self.maximum,self.filter_value]: edit.textChanged.connect(self.mark_dirty)
        self.bins.valueChanged.connect(self.mark_dirty); self.confirm.toggled.connect(self.mark_dirty)

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
        if table is None:return
        columns=list(table.columns)
        for combo in self.fields.values():
            combo.clear(); combo.addItem(''); combo.addItems(columns)
        self.preview.setColumnCount(len(columns)); self.preview.setHorizontalHeaderLabels(columns)
        self.preview.setRowCount(min(100,len(table)))
        for i,row in enumerate(table.head(100).itertuples(index=False,name=None)):
            for j,value in enumerate(row):self.preview.setItem(i,j,QTableWidgetItem(str(value)))
        self.status.setText(f'{len(table):,} rows · {len(columns)} columns · preview: first 100 rows. Each workbook sheet is separate to avoid mixing cells, foci and summaries.')
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
        for key,value in defaults.items():
            if value in table.columns or not value:self.fields[key].setCurrentText(value)

    def open_profiles(self):
        if self.worker is not None and self.worker.isRunning():return
        mask,_=QFileDialog.getOpenFileName(self,'Choose one label mask/XY (TYX)','','TIFF (*.tif *.tiff)')
        if not mask:return
        image,_=QFileDialog.getOpenFileName(self,'Choose matching fluorescence channel (TYX)','','TIFF (*.tif *.tiff)')
        if not image:return
        options=dict(pixel_size=self.calibration.value(),source=Path(mask).stem,orientation=self.orientation.currentText(),method=self.method.currentText())
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
                title=self.title.text(),cmap=self.cmap.currentText(),track_confirmed=self.confirm.isChecked(),normalization=self.normalization.currentText())
            used,plot,labels=prepare(table,spec); draw(self.figure,plot,spec,labels); self.canvas.draw_idle()
            self.snapshot=(used.copy(),plot.copy(),copy.deepcopy(spec),dict(labels),dict(self.provenance,table=self.sheet.currentText()))
            self.export.setEnabled(True); self.status.setText(f'{len(used):,} source rows used. Export includes these rows, plotted values, figures, metadata and Python/R/MATLAB scripts. No rows sampled for plotting.')
        except Exception as exc:
            self.mark_dirty(); QMessageBox.warning(self,'Cannot draw figure',str(exc))

    def save_bundle(self):
        if self.snapshot is None or not self.export.isEnabled():return
        root=QFileDialog.getExistingDirectory(self,'Choose parent folder for a new figure bundle')
        if not root:return
        try:
            from datetime import datetime
            folder=Path(root)/('figure_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
            used,plot,spec,labels,provenance=self.snapshot
            export_bundle(folder,self.figure,used,plot,spec,labels,provenance=provenance)
            self.status.setText(f'Figure, table and scripts exported to {folder}')
        except Exception as exc:QMessageBox.warning(self,'Export failed',str(exc))

    def closeEvent(self,event):
        if self.worker is not None and self.worker.isRunning():
            QMessageBox.information(self,'Profile extraction running','Wait for profile extraction to finish before closing.')
            event.ignore(); return
        super().closeEvent(event)
