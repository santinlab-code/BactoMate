"""Guided analysis of existing pipeline results, with explicit experimental groups."""
from pathlib import Path
from os.path import commonpath
import pandas as pd
from PyQt6.QtCore import QThread,QTimer,pyqtSignal,Qt
from PyQt6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QStackedWidget,QComboBox,
    QPushButton,QLabel,QCheckBox,QLineEdit,QDialog,QDialogButtonBox,QTableWidget,QTableWidgetItem,QMessageBox)
from bactomate.gui.tabs.figure_analysis import FigureAnalysisTab
from bactomate.modules.analysis_catalog import read_catalog,read_assignments,save_assignments,assemble_catalog

LABELS={'Histogram':'Histogramme','Scatter':'Nuage de points','Mean curve':'Courbe moyenne',
        'Box plot':'Boîte à moustaches','Violin plot':'Violon','ECDF':'Répartition cumulée',
        'Correlation':'Corrélations','Demograph':'Démographe','Kymograph':'Kymographe',
        'Normalized cell heatmap':'Carte sur cellule normalisée','Heatmap':'Carte de chaleur'}
METRICS={'area_um2':'Aire cellulaire (µm²)','Area (µm²)':'Aire cellulaire (µm²)',
         'length_um':'Longueur (µm)','width_um':'Largeur (µm)','mean_intensity':'Fluorescence moyenne',
         'frame':'Frame / temps'}
SPATIAL={'Correlation','Demograph','Kymograph','Normalized cell heatmap','Heatmap'}


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
        self.dataset=QComboBox();form.addRow('1 · Mes données',self.dataset)
        self.figure_choice=QComboBox()
        for kind,label in LABELS.items():self.figure_choice.addItem(label,kind)
        self.figure_choice.setCurrentIndex(self.figure_choice.findData('Violin plot'))
        form.addRow('2 · Ma figure',self.figure_choice)
        self.metric=QComboBox();self.metric.setMinimumContentsLength(22);self.metric.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon);form.addRow('3 · Ma mesure',self.metric)
        self.second_metric=QComboBox();form.addRow('Autre mesure / temps',self.second_metric)
        self.compare=QCheckBox('Comparer les conditions');self.compare.setChecked(True);form.addRow(self.compare)
        self.rep_points=QCheckBox('Afficher les moyennes des réplicats');self.rep_points.setChecked(True);form.addRow(self.rep_points)
        self.frame_choice=QComboBox();form.addRow('Temps / frame',self.frame_choice)
        self.groups_button=QPushButton('4 · Conditions et réplicats…');form.addRow(self.groups_button)
        hint=QLabel('Les cellules forment la distribution. Les points colorés indiquent la moyenne de chaque réplicat.\nAttribue le même réplicat aux fichiers/XY d’une même expérience. Un fichier n’est pas automatiquement un réplicat biologique.')
        hint.setWordWrap(True);form.addRow(hint)
        draw_button=QPushButton('Créer la figure');draw_button.clicked.connect(self.render);form.addRow(draw_button)
        export_button=QPushButton('Exporter figure, tableur et code…');export_button.clicked.connect(self.save_bundle)
        self.export.setVisible(False);self.simple_export=export_button;export_button.setEnabled(False);form.addRow(export_button)
        self.control_stack.addWidget(self.simple);self.control_stack.addWidget(advanced);scroll.setWidget(self.control_stack)
        header=QWidget();layout=QVBoxLayout(header)
        self.catalog_status=QLabel('Recherche des résultats du projet…');self.catalog_status.setWordWrap(True);layout.addWidget(self.catalog_status)
        buttons=QHBoxLayout();refresh=QPushButton('Actualiser les résultats');refresh.clicked.connect(self.refresh_catalog)
        self.advanced=QCheckBox('Réglages avancés');buttons.addWidget(refresh);buttons.addWidget(self.advanced);layout.addLayout(buttons)
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
        self.frame_choice.clear();self.frame_choice.addItem('Toutes (observations répétées)',None)
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
        self.second_metric.setVisible(kind in ('Scatter','Mean curve'))
        self.simple_form.labelForField(self.second_metric).setVisible(kind in ('Scatter','Mean curve'))
        if kind in SPATIAL:self.advanced.setChecked(True)
        if hasattr(self,'advanced') and self.advanced.isChecked():self.kind.setCurrentText(kind)
        self.mark_dirty()

    def toggle_mode(self,checked):
        self.control_stack.setCurrentIndex(1 if checked else 0)
        self.import_actions.setVisible(checked);self.preview.setVisible(checked)
        self.export.setVisible(checked)
        if checked:self.kind.setCurrentText(self.figure_choice.currentData())
        self.mark_dirty()

    def clear_session(self):
        self.catalog_root=None;self._results_root=None
        self.entries=[];self.assignments={};self._errors=[];self._catalog_cache={}
        self._guided_replicate='';self._guided_title=None
        self.set_tables({},{})
        for combo in (self.metric,self.second_metric,self.frame_choice,*self.fields.values()):combo.clear()
        for edit in (self.filter_value,self.minimum,self.maximum,self.title):edit.clear()
        self.preview.setColumnCount(0)
        self.confirm.setChecked(False)
        self.catalog_status.setText('Aucune session active. Lance une analyse pour retrouver ses résultats ici.')
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
            self.set_tables({},{});self._catalog_cache={}
        if root is None:
            self.catalog_root=None;self.entries=[];self.assignments={};self.set_tables({},{})
            self.catalog_status.setText('Ouvre le dossier du projet dans le Dashboard, ou lance une analyse depuis Segmentation. Les résultats seront repris ici automatiquement.')
            return
        self.catalog_root=root;self.catalog_status.setText(f'Recherche des résultats : {root}')
        worker=CatalogWorker(root,self,self._catalog_cache);self.catalog_worker=worker
        worker.ready.connect(lambda result:self.receive_catalog(root,result))
        worker.failed.connect(lambda error:self.catalog_status.setText('Lecture des résultats impossible : '+error))
        worker.start()

    def receive_catalog(self,root,result):
        if root!=self.catalog_root:return
        entries,errors=result;self.entries=entries;self._errors=errors
        try:self.assignments=read_assignments(root)
        except Exception as exc:
            self.catalog_status.setText('Attributions illisibles : '+str(exc));return
        self.rebuild_catalog()
        self.results_ready.emit()

    def rebuild_catalog(self):
        tables=assemble_catalog(self.entries,self.assignments)
        self.set_tables(tables,dict(root=str(self.catalog_root),files=sorted({e['path'] for e in self.entries}),assignments=self.assignments))
        count=len({e['id'] for e in self.entries})
        message=f'{count} fichiers de résultats · {sum(len(t) for t in tables.values()):,} lignes · actualisation à chaque ouverture de cette section.'
        if not count:message='Aucun résultat trouvé dans ce projet. Lance d’abord les mesures depuis Segmentation → Analyze.'
        if self._errors:message+='\nFichiers non lus : '+' ; '.join(self._errors)
        self.catalog_status.setText(message)

    def edit_groups(self):
        if not self.entries:
            QMessageBox.information(self,'Conditions et réplicats','Aucun résultat disponible dans le projet.');return
        dialog=QDialog(self);dialog.setWindowTitle('Conditions et réplicats');dialog.resize(850,500)
        layout=QVBoxLayout(dialog);layout.addWidget(QLabel('Une ligne par fichier. Les fichiers/XY d’un même réplicat doivent porter le même nom de réplicat.'))
        table=QTableWidget(0,3);table.setHorizontalHeaderLabels(['Fichier','Condition','Réplicat']);layout.addWidget(table)
        ids=sorted({e['id'] for e in self.entries});table.setRowCount(len(ids))
        for i,key in enumerate(ids):
            item=QTableWidgetItem(key);item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable);table.setItem(i,0,item)
            for j,field in ((1,'condition'),(2,'replicate')):table.setItem(i,j,QTableWidgetItem(self.assignments.get(key,{}).get(field,'')))
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        batch=QHBoxLayout();condition=QLineEdit();condition.setPlaceholderText('Condition')
        replicate=QLineEdit();replicate.setPlaceholderText('Réplicat')
        apply=QPushButton('Appliquer aux lignes choisies')
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
        except Exception as exc:QMessageBox.warning(self,'Attributions non enregistrées',str(exc));return
        self.assignments=choices;self.rebuild_catalog()

    def display_labels(self,labels):
        if self.advanced.isChecked():return labels
        return {key:METRICS.get(value,{'Count':'Effectif','Cumulative fraction':'Fraction cumulée'}.get(value,value)) for key,value in labels.items()}

    def render(self):
        self._guided_replicate='';self._guided_title=None
        if not self.advanced.isChecked():
            table=self.tables.get(self.sheet.currentText())
            if table is None:
                QMessageBox.information(self,'Mes données','Les résultats du projet apparaîtront ici après leur calcul.');return
            kind=self.figure_choice.currentData()
            if kind in SPATIAL:self.advanced.setChecked(True);return
            compare=self.compare.isChecked()
            needs_rep=self.rep_points.isChecked() and kind in ('Violin plot','Box plot')
            frame_value=self.frame_choice.currentData()
            checked_table=table if frame_value is None or not self._frame_column else table[table[self._frame_column].astype(str)==frame_value]
            required=(['Condition'] if compare else [])+(['Réplicat'] if needs_rep else [])
            if any(c not in checked_table or checked_table[c].str.strip().eq('').any() for c in required):
                QMessageBox.information(self,'Conditions et réplicats','Complète les conditions et réplicats avec le bouton « Conditions et réplicats… ». Aucun réplicat biologique n’est deviné.');return
            self.kind.setCurrentText(kind)
            self.fields['x'].setCurrentText(self.metric.currentData() or '')
            self.fields['y'].setCurrentText(self.second_metric.currentData() or '')
            self.fields['group'].setCurrentText('Condition' if compare else '')
            self.fields['filter_column'].setCurrentText(self._frame_column if frame_value is not None and self._frame_column else '')
            self.filter_value.setText(frame_value or '')
            self.minimum.clear();self.maximum.clear();self.normalization.setCurrentText('raw')
            self._guided_replicate='Réplicat' if needs_rep else ''
            self._guided_title=f'{LABELS[kind]} — {self.metric.currentText()}'
        super().render()
        self.simple_export.setEnabled(self.export.isEnabled())
        if self.export.isEnabled() and self._guided_replicate:
            used,plot,*_=self.snapshot
            counts=used.groupby('Condition')['Réplicat'].nunique().to_dict() if 'Condition' in used else {'Toutes':used['Réplicat'].nunique()}
            self.status.setText(f'{len(used):,} observations · {counts} réplicats par condition. Points = moyennes des réplicats ; violons = cellules.')

    def closeEvent(self,event):
        if self.catalog_worker is not None and self.catalog_worker.isRunning():
            event.ignore();return
        super().closeEvent(event)
