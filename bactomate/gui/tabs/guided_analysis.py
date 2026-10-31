"""Guided analysis of existing pipeline results, with explicit experimental groups."""
from pathlib import Path
from os.path import commonpath
import pandas as pd
from PyQt6.QtCore import QThread,QTimer,pyqtSignal,Qt
from PyQt6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QStackedWidget,QComboBox,
    QPushButton,QLabel,QCheckBox,QLineEdit,QDialog,QDialogButtonBox,QTableWidget,QTableWidgetItem,QMessageBox)
from bactomate.gui.tabs.figure_analysis import FigureAnalysisTab
from bactomate.modules.analysis_catalog import read_catalog,read_assignments,save_assignments,assemble_catalog

LABELS={kind:kind for kind in ('Histogram','Scatter','Mean curve','Box plot','Violin plot','ECDF',
    'Correlation','Demograph','Kymograph','Normalized cell heatmap','Heatmap','Maxima map','Foci count')}
METRICS={'area_um2':'Cell area (µm²)','Area (µm²)':'Cell area (µm²)',
         'length_um':'Cell length (µm)','width_um':'Cell width (µm)','mean_intensity':'Mean fluorescence',
         'frame':'Frame / time'}
SPATIAL={'Correlation','Demograph','Kymograph','Normalized cell heatmap','Heatmap','Maxima map','Foci count'}


class CatalogWorker(QThread):
    ready=pyqtSignal(object)
    failed=pyqtSignal(str)
    def __init__(self,root,parent,cache):super().__init__(parent);self.root=root;self.cache=cache
    def run(self):
        try:self.ready.emit(read_catalog(self.root,self.cache))
        except Exception as exc:self.failed.emit(str(exc))


class GuidedAnalysisTab(FigureAnalysisTab):
    results_ready=pyqtSignal()
    def __init__(self,parent=None):
        super().__init__(parent)
        self.project_window=parent
        self.entries=[];self.assignments={};self.catalog_root=None;self.catalog_worker=None
        self._guided_replicate='';self._errors=[];self._catalog_cache={}
        self._results_root=None
        self._spatial_tables={}
        self._figure_generation=0
        self._last_figure_plan=None
        outer=self.layout()
        # Existing controls remain intact, in an optional advanced view.
        old_actions=outer.takeAt(0)
        self.import_actions=QWidget();self.import_actions.setLayout(old_actions)
        self.split=outer.itemAt(0).widget()
        scroll=self.split.widget(0)
        advanced=scroll.takeWidget()
        self.control_stack=QStackedWidget()
        self.simple=QWidget();form=QFormLayout(self.simple);self.simple_form=form
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.dataset=QComboBox();form.addRow('1 · My data',self.dataset)
        self.figure_choice=QComboBox()
        for kind,label in LABELS.items():self.figure_choice.addItem(label,kind)
        self.figure_choice.setCurrentIndex(self.figure_choice.findData('Violin plot'))
        form.addRow('2 · My figure',self.figure_choice)
        self.metric=QComboBox();self.metric.setMinimumContentsLength(22);self.metric.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon);form.addRow('3 · My measurement',self.metric)
        self.second_metric=QComboBox();form.addRow('Other measurement / time',self.second_metric)
        self.compare=QCheckBox('Compare conditions');self.compare.setChecked(True);form.addRow(self.compare)
        self.rep_points=QCheckBox('Show replicate means');self.rep_points.setChecked(True);form.addRow(self.rep_points)
        self.frame_choice=QComboBox();form.addRow('Frame / time',self.frame_choice)
        self.groups_button=QPushButton('Conditions && replicates…')
        hint=QLabel('Cells form the distribution. Coloured points show replicate means.\nGive XYs from the same experiment the same replicate name. A file is not automatically a biological replicate.')
        hint.setWordWrap(True);form.addRow(hint);self.simple_hint=hint
        draw_button=QPushButton('Draw figure');self.simple_draw=draw_button;draw_button.clicked.connect(self.render);form.addRow(draw_button)
        export_button=QPushButton('Export figure, data && code…');export_button.clicked.connect(self.save_bundle)
        self.export.setVisible(False);self.simple_export=export_button;export_button.setEnabled(False);form.addRow(export_button)
        self.control_stack.addWidget(self.simple);self.control_stack.addWidget(advanced);scroll.setWidget(self.control_stack)
        header=QWidget();layout=QVBoxLayout(header)
        launch=QHBoxLayout();launch.addWidget(self.groups_button)
        self.guide_button=QPushButton('Figure guide…');self.guide_button.clicked.connect(self.open_figure_guide)
        launch.addWidget(self.guide_button);layout.addLayout(launch)
        self.catalog_status=QLabel('Looking for project results…');self.catalog_status.setWordWrap(True);layout.addWidget(self.catalog_status)
        buttons=QHBoxLayout();refresh=QPushButton('Refresh results');refresh.clicked.connect(self.refresh_catalog)
        self.advanced=QCheckBox('Advanced / MicrobeJ-style controls');buttons.addWidget(refresh);buttons.addWidget(self.advanced);layout.addLayout(buttons)
        layout.addWidget(self.import_actions);outer.insertWidget(0,header)
        self.import_actions.hide()
        self.dataset.currentTextChanged.connect(self.sheet.setCurrentText)
        self.sheet.currentTextChanged.connect(self.sync_metrics)
        self.figure_choice.currentIndexChanged.connect(self.figure_changed)
        self.groups_button.clicked.connect(self.edit_groups)
        self.advanced.toggled.connect(self.toggle_mode)
        for widget in (self.metric,self.second_metric,self.frame_choice):widget.currentIndexChanged.connect(self.mark_dirty)
        for widget in (self.compare,self.rep_points):widget.toggled.connect(self.mark_dirty)
        self.preview.hide();self.figure_changed()

    def open_figure_guide(self):
        from bactomate.gui.figure_guide import FigureGuide
        if self.worker is not None and self.worker.isRunning():
            QMessageBox.information(self,'Figure calculation running','Wait for the current calculation to finish.');return
        try:guide=FigureGuide(self)
        except Exception as exc:
            QMessageBox.warning(self,'Cannot open Figure guide',str(exc));return
        goal={'Demograph':'demograph','Maxima map':'maxima','Foci count':'counts'}.get(self.figure_choice.currentData())
        if goal:guide.goal.setCurrentIndex(guide.goal.findData(goal))
        self._figure_guide=guide
        guide.exec()
        self._figure_guide=None
        guide.deleteLater()

    def mark_dirty(self,*args):
        super().mark_dirty(*args)
        if hasattr(self,'simple_export'):self.simple_export.setEnabled(False)

    def set_tables(self,tables,provenance):
        super().set_tables(tables,provenance)
        if hasattr(self,'dataset'):
            if not tables:
                self.snapshot=None;self.figure.clear();self.canvas.draw_idle();self.preview.setRowCount(0)
            old=self.dataset.currentText();self.dataset.blockSignals(True)
            self.dataset.clear();self.dataset.addItems(list(tables));self.dataset.setCurrentText(old if old in tables else next(iter(tables),''))
            self.dataset.blockSignals(False);self.sheet.setCurrentText(self.dataset.currentText());self.sync_metrics()

    def sync_metrics(self,*_):
        if not hasattr(self,'metric'):return
        table=self.tables.get(self.sheet.currentText())
        if table is None:return
        previous_metric=self.metric.currentData()
        for combo in (self.metric,self.second_metric):
            old=combo.currentData();combo.clear()
            for c in table.select_dtypes(include='number').columns:
                if c.lower() not in ('cell_id','track_id','label'):combo.addItem(METRICS.get(c,c),c)
            index=combo.findData(old)
            if index>=0:combo.setCurrentIndex(index)
        frame_column=next((c for c in table if c.lower()=='frame'),None)
        previous_frame=self.frame_choice.currentData()
        self.frame_choice.clear();self.frame_choice.addItem('All (repeated observations)',None)
        self._frame_column=frame_column
        if frame_column:
            values=list(table[frame_column].dropna().unique())
            numeric=pd.to_numeric(pd.Series(values),errors='coerce')
            values=sorted(values,key=float if numeric.notna().all() else str)
            for value in values:self.frame_choice.addItem(str(value),str(value))
            if len(values)>1:
                self.frame_choice.setCurrentIndex(max(1,self.frame_choice.findData(previous_frame)))
        self.frame_choice.setVisible(frame_column is not None)
        self.simple_form.labelForField(self.frame_choice).setVisible(frame_column is not None)
        if self.metric.count() and self.metric.findData(previous_metric)<0:
            index=next((i for i in range(self.metric.count()) if 'area' in str(self.metric.itemData(i)).lower()),0)
            self.metric.setCurrentIndex(index)

    def figure_changed(self,*_):
        kind=self.figure_choice.currentData()
        guided=kind in ('Demograph','Maxima map','Foci count')
        self.metric.setVisible(not guided);self.simple_form.labelForField(self.metric).setVisible(not guided)
        self.second_metric.setVisible(kind in ('Scatter','Mean curve'))
        self.simple_form.labelForField(self.second_metric).setVisible(kind in ('Scatter','Mean curve'))
        self.compare.setVisible(not guided);self.rep_points.setVisible(not guided)
        has_frame=bool(getattr(self,'_frame_column',None)) and not guided
        self.frame_choice.setVisible(has_frame);self.simple_form.labelForField(self.frame_choice).setVisible(has_frame)
        self.simple_draw.setText('Edit with Figure guide…' if guided else 'Draw figure')
        self.simple_hint.setText({
            'Demograph':'One row per cell, sorted by length. Position runs from 0 to 1. Use Figure guide to choose the channel, condition, frame and pole alignment.',
            'Maxima map':'Maxima on a normalized reference cell. Use Figure guide to choose brightest pixels or kept detected foci. The outline is schematic.',
            'Foci count':'Percentage of cells with 0, 1, 2… foci. Use Figure guide to choose the count column and compare conditions.'
        }.get(kind,'Cells form the distribution. Coloured points show replicate means. Give XYs from the same biological replicate the same replicate name.'))
        if kind in SPATIAL-{'Demograph','Maxima map','Foci count'}:self.advanced.setChecked(True)
        if hasattr(self,'advanced') and self.advanced.isChecked():self.kind.setCurrentText(kind)
        self.mark_dirty()

    def toggle_mode(self,checked):
        self.control_stack.setCurrentIndex(1 if checked else 0)
        self.import_actions.setVisible(checked);self.preview.setVisible(checked)
        self.export.setVisible(checked)
        if checked:self.kind.setCurrentText(self.figure_choice.currentData())
        self.mark_dirty()

    def clear_session(self):
        self._figure_generation+=1
        self._last_figure_plan=None
        self.catalog_root=None;self._results_root=None;self._spatial_tables={}
        self.entries=[];self.assignments={};self._errors=[];self._catalog_cache={}
        self._guided_replicate='';self._guided_title=None
        self.set_tables({},{})
        for combo in (self.metric,self.second_metric,self.frame_choice,*self.fields.values()):combo.clear()
        for edit in (self.filter_value,self.minimum,self.maximum,self.title):edit.clear()
        self.preview.setColumnCount(0)
        self.confirm.setChecked(False)
        self.catalog_status.setText('No active session. Run an analysis to see its results here.')
        self.status.clear()

    def load_completed_results(self,paths):
        directories=[Path(p).resolve().parent for p in paths if Path(p).is_file()]
        if not directories:return
        root=Path(commonpath(directories))
        if root.name=='_analysis':root=root.parent
        workspace=getattr(self.project_window,'_workspace_root',None)
        if workspace and all(d.is_relative_to(Path(workspace).resolve()) for d in directories):
            root=Path(workspace).resolve()
        self._results_root=root
        self.refresh_catalog()

    def context_root(self):
        parent=self.parentWidget()
        # ModuleShell reparents this widget, so keep the explicit MainWindow reference.
        parent=getattr(self,'project_window',parent)
        if self._results_root is not None:return self._results_root
        workspace=getattr(parent,'_workspace_root',None)
        if workspace:return Path(workspace).resolve()
        for name in ('analyze_tab','filtering_tab','tracking_tab'):
            edit=getattr(getattr(parent,name,None),'file_path',None)
            if edit is not None and edit.text().strip():
                path=Path(edit.text().strip()).expanduser()
                if path.exists():
                    from bactomate.gui.analysis_paths import base_dir_for_mask
                    if path.is_file():return base_dir_for_mask(path).resolve()
                    if path.name=='filtered_masks' or path.name.startswith('_segmentation'):
                        return base_dir_for_mask(path/'session_masks.tif').resolve()
                    return path.resolve()
        return None

    def showEvent(self,event):
        super().showEvent(event)
        QTimer.singleShot(0,self.refresh_catalog)

    def refresh_catalog(self):
        root=self.context_root()
        if self.catalog_worker is not None and self.catalog_worker.isRunning():
            if root!=self.catalog_root:
                self.catalog_root=root;self.set_tables({},{})
                self.catalog_worker.finished.connect(self.refresh_catalog)
            return
        if root!=self.catalog_root:
            self._figure_generation+=1
            self._last_figure_plan=None
            self.set_tables({},{});self._catalog_cache={};self._spatial_tables={}
        if root is None:
            self.catalog_root=None;self.entries=[];self.assignments={};self.set_tables({},{})
            self.catalog_status.setText('Open the project folder in the Dashboard or run Segmentation → Analyze. Results will appear here automatically.')
            return
        self.catalog_root=root;self.catalog_status.setText(f'Looking for results: {root}')
        worker=CatalogWorker(root,self,self._catalog_cache);self.catalog_worker=worker
        worker.ready.connect(lambda result:self.receive_catalog(root,result))
        worker.failed.connect(lambda error:self.catalog_status.setText('Cannot read results: '+error))
        worker.start()

    def receive_catalog(self,root,result):
        if root!=self.catalog_root:return
        entries,errors=result;self.entries=entries;self._errors=errors
        try:self.assignments=read_assignments(root)
        except Exception as exc:
            self.catalog_status.setText('Cannot read group assignments: '+str(exc));return
        self.rebuild_catalog()
        self.results_ready.emit()

    def rebuild_catalog(self):
        tables={**assemble_catalog(self.entries,self.assignments),**self._spatial_tables}
        self.set_tables(tables,dict(root=str(self.catalog_root),files=sorted({e['path'] for e in self.entries}),assignments=self.assignments))
        count=len({e['id'] for e in self.entries})
        message=f'{count} result files · {sum(len(t) for t in tables.values()):,} rows · refreshed each time this section opens.'
        if not count:message='No results found. First run measurements in Segmentation → Analyze.'
        if self._errors:message+='\nUnread files: '+' ; '.join(self._errors)
        self.catalog_status.setText(message)

    def edit_groups(self):
        from bactomate.gui.spatial_sources import project_spatial_sources
        sources=project_spatial_sources(self)
        if not self.entries and not sources:
            QMessageBox.information(self,'Conditions & replicates','No results are available in this project.');return
        dialog=QDialog(self);dialog.setWindowTitle('Conditions & replicates');dialog.resize(850,500)
        layout=QVBoxLayout(dialog);layout.addWidget(QLabel('One row per file. Give files/XYs from the same biological replicate the same replicate name.'))
        table=QTableWidget(0,3);table.setHorizontalHeaderLabels(['File','Condition','Replicate']);layout.addWidget(table)
        ids=sorted({e['id'] for e in self.entries}|{s['source_id'] for s in sources});table.setRowCount(len(ids))
        for i,key in enumerate(ids):
            item=QTableWidgetItem(key);item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable);table.setItem(i,0,item)
            for j,field in ((1,'condition'),(2,'replicate')):table.setItem(i,j,QTableWidgetItem(self.assignments.get(key,{}).get(field,'')))
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        batch=QHBoxLayout();condition=QLineEdit();condition.setPlaceholderText('Condition')
        replicate=QLineEdit();replicate.setPlaceholderText('Replicate')
        apply=QPushButton('Apply to selected rows')
        def assign_selected():
            for index in table.selectionModel().selectedRows():
                if condition.text().strip():table.item(index.row(),1).setText(condition.text().strip())
                if replicate.text().strip():table.item(index.row(),2).setText(replicate.text().strip())
        apply.clicked.connect(assign_selected);batch.addWidget(condition);batch.addWidget(replicate);batch.addWidget(apply)
        layout.insertLayout(1,batch)
        table.horizontalHeader().setStretchLastSection(True);table.setColumnWidth(0,440)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);layout.addWidget(buttons)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        choices={**self.assignments,**{key:dict(condition=table.item(i,1).text().strip(),replicate=table.item(i,2).text().strip()) for i,key in enumerate(ids)}}
        try:save_assignments(self.catalog_root,choices)
        except Exception as exc:QMessageBox.warning(self,'Assignments not saved',str(exc));return
        self.assignments=choices
        for table in self._spatial_tables.values():
            for key,value in choices.items():
                selected=table['Source file'].eq(key)
                for column,field in [('Condition','condition'),('Replicate','replicate')]:
                    if value.get(field):table.loc[selected,column]=value[field]
        self.rebuild_catalog()

    def display_labels(self,labels):
        if self.advanced.isChecked():return labels
        return {key:METRICS.get(value,{'Count':'Count','Cumulative fraction':'Cumulative fraction'}.get(value,value)) for key,value in labels.items()}

    def render(self):
        self._guided_replicate='';self._guided_title=None
        if not self.advanced.isChecked():
            table=self.tables.get(self.sheet.currentText())
            if table is None:
                QMessageBox.information(self,'My data','Project results appear here after the analysis completes.');return
            kind=self.figure_choice.currentData()
            if kind in SPATIAL-{'Demograph','Maxima map','Foci count'}:self.advanced.setChecked(True);return
            compare=self.compare.isChecked()
            needs_rep=self.rep_points.isChecked() and kind in ('Violin plot','Box plot')
            frame_value=self.frame_choice.currentData()
            checked_table=table if frame_value is None or not self._frame_column else table[table[self._frame_column].astype(str)==frame_value]
            required=(['Condition'] if compare else [])+(['Replicate'] if needs_rep else [])
            if any(c not in checked_table or checked_table[c].str.strip().eq('').any() for c in required):
                QMessageBox.information(self,'Conditions & replicates','Fill in Conditions & replicates first. Biological replicates are never inferred.');return
            self.kind.setCurrentText(kind)
            self.fields['x'].setCurrentText(self.metric.currentData() or '')
            self.fields['y'].setCurrentText(self.second_metric.currentData() or '')
            self.fields['group'].setCurrentText('Condition' if compare else '')
            self.fields['filter_column'].setCurrentText(self._frame_column if frame_value is not None and self._frame_column else '')
            self.filter_value.setText(frame_value or '')
            self.minimum.clear();self.maximum.clear();self.normalization.setCurrentText('raw')
            self._guided_replicate='Replicate' if needs_rep else ''
            self._guided_title=f'{LABELS[kind]} — {self.metric.currentText()}'
        super().render()
        self.simple_export.setEnabled(self.export.isEnabled())
        if self.export.isEnabled() and self._guided_replicate:
            used,plot,*_=self.snapshot
            counts=used.groupby('Condition')['Replicate'].nunique().to_dict() if 'Condition' in used else {'All':used['Replicate'].nunique()}
            self.status.setText(f'{len(used):,} observations · {counts} replicates per condition. Points = replicate means; violins = cells.')

    @staticmethod
    def select_population(table,plan):
        table=table.copy()
        if plan.condition:
            if 'Condition' not in table:raise ValueError('Assign conditions with Conditions & replicates first.')
            table=table[table.Condition.eq(plan.condition)]
        frame=next((c for c in table if c.lower()=='frame'),None)
        if frame and plan.frame is not None:
            numeric=pd.to_numeric(table[frame],errors='coerce')
            if plan.frame=='first':
                first=numeric.groupby(table['Source file']).transform('min') if 'Source file' in table else numeric.min()
                table=table[numeric.eq(first)]
            else:
                try:value=float(plan.frame)
                except ValueError:raise ValueError('Frame must be a 0-based number, First frame, or All frames.')
                table=table[numeric.eq(value)]
        if table.empty:raise ValueError('No observations match this condition / frame.')
        return table

    def apply_figure_plan(self,plan,pairs):
        from bactomate.gui.spatial_sources import SpatialBatchWorker
        if plan.goal in ('demograph','maxima'):
            if not pairs:raise ValueError('No matching mask/channel images for this population.')
            if self.worker is not None and self.worker.isRunning():raise ValueError('Wait for the current calculation to finish.')
            if plan.goal=='maxima' and plan.maxima_profile=='focus' and any(not p['foci_csv'] for p in pairs):
                raise ValueError('Saved filtered foci are missing for one or more XYs. Run Filtering → Filter File/Folder first, or choose brightest pixels.')
            options=dict(pixel_size=plan.pixel_size,method=plan.method,orientation=plan.orientation,
                         use_foci=plan.goal=='maxima' and plan.maxima_profile=='focus')
            self.mark_dirty()
            self.guide_button.setEnabled(False)
            worker=SpatialBatchWorker(pairs,options,self.assignments,self);self.worker=worker
            worker.progress.connect(self.status.setText)
            generation=self._figure_generation;root=self.context_root()
            worker.ready.connect(lambda result:self.receive_spatial_result(result,plan)
                if generation==self._figure_generation and root==self.context_root() else None)
            worker.failed.connect(self.spatial_figure_failed)
            worker.finished.connect(lambda:self.guide_button.setEnabled(True))
            worker.start()
        else:
            table=self.tables.get(plan.dataset)
            if table is None:raise ValueError('Choose an available data table.')
            table=self.select_population(table,plan)
            if plan.goal=='counts' and not ('foci' in plan.metric.lower() and any(w in plan.metric.lower() for w in ('number','count','num '))):
                raise ValueError('Choose a per-cell foci count measurement, including cells with zero foci.')
            self.draw_figure_plan(table,plan,self.provenance)

    def spatial_figure_failed(self,error):
        self.status.setText('Cannot build spatial figure: '+error)
        QMessageBox.warning(self,'Cannot build spatial figure',error)

    def receive_spatial_result(self,result,plan):
        self._spatial_tables={'Spatial profiles':result['profiles'],'Profile cell measurements':result['cells']}
        provenance=dict(root=str(self.context_root()),sources=result['sources'],
                        normalization='Coordinates normalized per cell; outline schematic; no pole-age inference.',
                        density='96×96 histogram, Gaussian sigma=2 bins, peak scaled to 1; density below 1% of peak transparent')
        self.set_tables({**self.tables,**self._spatial_tables},provenance)
        try:self.draw_figure_plan(self.select_population(result['profiles'],plan),plan,provenance)
        except ValueError as exc:QMessageBox.warning(self,'Cannot draw spatial figure',str(exc))

    def draw_figure_plan(self,table,plan,provenance):
        from bactomate.modules.figure_analysis import FigureSpec
        spatial=plan.goal in ('demograph','maxima')
        needs_rep=not spatial and plan.replicate and plan.kind in ('Violin plot','Box plot')
        required=(['Condition'] if plan.compare and not spatial else [])+(['Replicate'] if needs_rep else [])
        if any(c not in table or table[c].fillna('').astype(str).str.strip().eq('').any() for c in required):
            raise ValueError('Fill in Conditions & replicates first, or turn off condition comparison / replicate means.')
        spec=FigureSpec(kind=plan.kind,title=plan.title or (plan.channel if spatial and plan.channel else plan.kind),
                        cmap='inferno' if spatial else 'viridis')
        if plan.goal=='demograph':
            spec.x='relative_position';spec.y='object_key';spec.value='intensity';spec.sort='length_um';spec.normalization=plan.normalization
        elif plan.goal=='maxima':
            spec.x='relative_width';spec.y='relative_position';spec.value='intensity'
            spec.maxima_profile=plan.maxima_profile;spec.show_points=plan.show_points
        else:
            spec.x=plan.metric;spec.y=plan.second_metric
            spec.group='Condition' if plan.compare else '';spec.replicate='Replicate' if needs_rep else ''
        # Validate before changing the current figure or its exported snapshot.
        from bactomate.modules.figure_analysis import prepare
        prepare(table,spec)
        name='Selected population'
        self.set_tables({**self.tables,name:table},provenance)
        self.sheet.setCurrentText(name);self.dataset.setCurrentText(name)
        self.figure_choice.blockSignals(True)
        self.figure_choice.setCurrentIndex(self.figure_choice.findData(spec.kind))
        self.figure_choice.blockSignals(False)
        self.kind.setCurrentText(spec.kind)
        self.metric.setCurrentIndex(self.metric.findData(spec.x))
        self.second_metric.setCurrentIndex(self.second_metric.findData(spec.y))
        self.compare.setChecked(bool(spec.group));self.rep_points.setChecked(bool(spec.replicate))
        self.figure_changed()
        for key,widget in self.fields.items():widget.setCurrentText(getattr(spec,key,''))
        self.minimum.clear();self.maximum.clear();self.filter_value.clear()
        self.title.setText(spec.title);self.cmap.setCurrentText(spec.cmap)
        self.normalization.setCurrentText(spec.normalization);self.relative_position.setChecked(False)
        self.maxima_source.setCurrentIndex(self.maxima_source.findData(spec.maxima_profile))
        self.show_maxima_points.setChecked(spec.show_points)
        self._guided_replicate=spec.replicate;self._guided_title=None
        self.plot_table(table,spec,provenance)
        self.simple_export.setEnabled(True)
        self._last_figure_plan=plan
        frame='first frame per XY' if plan.frame=='first' else ('all frames' if plan.frame is None else 'frame '+str(plan.frame))
        used,plotted,*_=self.snapshot
        detail=f"{used.object_key.nunique()} cells" if spatial else f"{len(used):,} observations"
        if plan.goal=='maxima':detail=f"{len(plotted)} points from "+detail
        self.status.setText(f"{plan.kind} · {plan.channel+' · ' if spatial else ''}{plan.condition or 'all conditions'} · {frame} · {detail}. Export includes source data and code.")

    def closeEvent(self,event):
        if self.catalog_worker is not None and self.catalog_worker.isRunning():
            event.ignore();return
        super().closeEvent(event)
