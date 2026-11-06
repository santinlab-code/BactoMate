"""A deterministic, data-aware figure guide. No remote service or free-text parser."""
from dataclasses import dataclass,field
from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QWizard,QWizardPage,QVBoxLayout,QFormLayout,QLabel,QComboBox,
                            QCheckBox,QDoubleSpinBox,QLineEdit,QPushButton,QSpinBox,QScrollArea,QWidget)
from bactomate.gui.spatial_sources import project_spatial_sources

GOALS={
    'Compare a cell measurement':'distribution',
    'Relate two measurements':'relationship',
    'See fluorescence along cells (demograph)':'demograph',
    'Map fluorescence on a normalized cell':'cell_heatmap',
    'Locate maxima on a normalized cell':'maxima',
    'Count foci per cell':'counts',
    'Follow one cell through a time-lapse (kymograph)':'kymograph',
}
SPATIAL_GOALS={'demograph','cell_heatmap','maxima','kymograph'}


@dataclass
class FigurePlan:
    goal:str
    kind:str
    dataset:str
    metric:str=''
    second_metric:str=''
    condition:str=''
    frame:str|None=None
    channel:str=''
    source_id:str=''
    normalization:str='raw'
    orientation:str='geometric'
    maxima_profile:str='maximum'
    show_points:bool=True
    pixel_size:float=0.0
    method:str='auto'
    compare:bool=True
    replicate:bool=True
    title:str=''
    track_id:int=1
    track_confirmed:bool=False
    tracked_mask:str=''
    time_interval:float=0.
    figure_options:dict=field(default_factory=dict)
    sampling:str='fixed'
    demograph_layout:str='length-scaled columns'
    demograph_value:str='intensity'
    map_background:str='white'
    palette:str='inferno'


class GuidePage(QWizardPage):
    def __init__(self,guide,title,subtitle):
        super().__init__();self.guide=guide;self.setTitle(title);self.setSubTitle(subtitle)
        outer=QVBoxLayout(self);scroll=QScrollArea();scroll.setWidgetResizable(True)
        body=QWidget();self.form=QFormLayout(body);scroll.setWidget(body);outer.addWidget(scroll)
        self.form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
    def initializePage(self):self.guide.update_step(self.wizard().currentId())
    def validatePage(self):return self.guide.validate_step(self.wizard().currentId())


class FigureGuide(QWizard):
    def __init__(self,tab):
        super().__init__(tab);self.tab=tab;self.sources=project_spatial_sources(tab)
        self.setWindowTitle('Figure guide');self.resize(680,680)
        self.setButtonText(QWizard.WizardButton.FinishButton,'Draw figure')
        self.setButtonText(QWizard.WizardButton.BackButton,'< Back')
        self.setButtonText(QWizard.WizardButton.NextButton,'Next >')
        self.setButtonText(QWizard.WizardButton.CancelButton,'Cancel')
        first=GuidePage(self,'1 · What would you like to show?',
            'Start with your question. The guide chooses axes and checks the required data.')
        self.goal=QComboBox()
        for label,key in GOALS.items():self.goal.addItem(label,key)
        first.form.addRow('My question',self.goal)
        self.description=QLabel();self.description.setWordWrap(True);first.form.addRow(self.description)
        self.addPage(first)
        data=GuidePage(self,'2 · Which population?',
            'Results and matching images come from the current project. No file import is needed.')
        self.dataset=QComboBox();self.dataset.addItems(list(tab.tables));data.form.addRow('Data',self.dataset)
        self.metric=QComboBox();data.form.addRow('Measurement',self.metric)
        self.other=QComboBox();data.form.addRow('Other measurement',self.other)
        self.sample=QComboBox();self.sample.addItem('All matching samples / XYs','')
        for key in sorted({s['source_id'] for s in self.sources}):self.sample.addItem(key,key)
        data.form.addRow('Sample / XY',self.sample)
        self.tracked=QComboBox();data.form.addRow('Tracking masks',self.tracked)
        self.track_id=QSpinBox();self.track_id.setRange(1,2147483647);data.form.addRow('Cell / track ID',self.track_id)
        self.track_confirmed=QCheckBox('I verified that this ID follows the same cell over time')
        data.form.addRow(self.track_confirmed)
        self.time_interval=QDoubleSpinBox();self.time_interval.setRange(0,100000);self.time_interval.setDecimals(4)
        self.time_interval.setSpecialValueText('Use metadata, otherwise frames');data.form.addRow('Frame interval (minutes)',self.time_interval)
        self.channel=QComboBox();self.channel.addItems(sorted({s['channel'] for s in self.sources}));data.form.addRow('Channel',self.channel)
        self.condition=QComboBox();self.condition.addItem('All conditions','')
        conditions={str(v.get('condition','')).strip() for v in tab.assignments.values()}
        for table in tab.tables.values():
            if 'Condition' in table:conditions.update(table.Condition.dropna().astype(str))
        for name in sorted(conditions-{''}):self.condition.addItem(name,name)
        data.form.addRow('Condition',self.condition)
        assign=QPushButton('Conditions && replicates…');assign.clicked.connect(self.edit_groups)
        data.form.addRow(assign)
        self.frame=QComboBox();self.frame.addItem('First frame', 'first');self.frame.addItem('All frames (repeated observations)',None)
        self.frame.setEditable(True);data.form.addRow('Frame (0-based)',self.frame)
        self.pixel_size=QDoubleSpinBox();self.pixel_size.setDecimals(6);self.pixel_size.setRange(0,1000)
        self.pixel_size.setValue(0);self.pixel_size.setSpecialValueText('Use image metadata')
        data.form.addRow('Fallback calibration (µm / px)',self.pixel_size)
        self.data_note=QLabel();self.data_note.setWordWrap(True);data.form.addRow(self.data_note)
        self.data_page=data;self.addPage(data)
        look=GuidePage(self,'3 · How should the figure look?',
            'All figures and exports are square. The choices below have a direct biological meaning.')
        self.style=QComboBox();look.form.addRow('Figure',self.style)
        self.normalization=QComboBox()
        for text,value in [('Keep absolute fluorescence','raw'),('Scale each cell to its maximum','per-cell max'),('Scale each cell from 0 to 1','per-cell min-max')]:self.normalization.addItem(text,value)
        look.form.addRow('Intensity',self.normalization)
        self.demograph_layout=QComboBox()
        self.demograph_layout.addItem('Length-scaled columns — cells ordered by length','length-scaled columns')
        self.demograph_layout.addItem('Normalized rows — each cell has equal displayed length','normalized rows')
        look.form.addRow('Demograph layout',self.demograph_layout)
        self.demograph_value=QComboBox();self.demograph_value.addItem('Fluorescence intensity','intensity')
        self.demograph_value.addItem('Local cell width (µm)','local_width_um');look.form.addRow('Demograph colour measures',self.demograph_value)
        self.background=QComboBox();self.background.addItems(['white','black']);look.form.addRow('Background',self.background)
        self.palette=QComboBox();self.palette.addItems(['inferno','turbo','magma','viridis','plasma','cividis','gray']);look.form.addRow('Colour map',self.palette)
        self.method=QComboBox();self.method.addItem('Automatic — follow curved cells','auto')
        self.method.addItem('Straight rods — principal axis','principal axis')
        self.method.addItem('Curved rods — medial axis','medial axis');look.form.addRow('Cell shape',self.method)
        self.sampling=QComboBox();self.sampling.addItem('24 segments (direct measurements)','fixed')
        self.sampling.addItem('Native resolution → 24 positions','native');look.form.addRow('Profile sampling',self.sampling)
        self.orientation=QComboBox();self.orientation.addItem('Geometric — no pole-age inference','geometric')
        self.orientation.addItem('Put the brighter pole at the left / top','bright pole');look.form.addRow('Cell orientation',self.orientation)
        self.maxima=QComboBox();self.maxima.addItem('Brightest pixel in each cell','maximum');self.maxima.addItem('Kept detected foci (saved Filtering results)','focus')
        look.form.addRow('What counts as a maximum?',self.maxima)
        self.points=QCheckBox('Show individual points over the density');self.points.setChecked(True);look.form.addRow(self.points)
        self.compare=QCheckBox('Compare conditions');self.compare.setChecked(True);look.form.addRow(self.compare)
        self.replicate=QCheckBox('Show replicate means');self.replicate.setChecked(True);look.form.addRow(self.replicate)
        self.title=QLineEdit();self.title.setPlaceholderText('Optional');look.form.addRow('Title',self.title)
        self.look_note=QLabel();self.look_note.setWordWrap(True);look.form.addRow(self.look_note)
        self.look_page=look;self.addPage(look)
        review=GuidePage(self,'4 · Review and draw',
            'Check what will be measured before creating the figure.')
        self.review=QLabel();self.review.setWordWrap(True);self.review.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        review.form.addRow(self.review);self.addPage(review)
        self.goal.currentIndexChanged.connect(self.update_description)
        self.demograph_value.currentIndexChanged.connect(self.update_intensity_controls)
        self.dataset.currentTextChanged.connect(self.update_metrics)
        self.sample.currentIndexChanged.connect(self.update_tracking_choices)
        self.update_metrics();self.update_description()
        previous=getattr(tab,'_last_figure_plan',None)
        self._previous_plan=previous
        if previous is not None:
            self.goal.setCurrentIndex(self.goal.findData(previous.goal))
            self.dataset.setCurrentText(previous.dataset)
            self.metric.setCurrentText(previous.metric);self.other.setCurrentText(previous.second_metric)
            self.sample.setCurrentIndex(max(0,self.sample.findData(previous.source_id)))
            self.channel.setCurrentText(previous.channel)
            self.condition.setCurrentIndex(max(0,self.condition.findData(previous.condition)))
            if previous.frame in ('first',None):self.frame.setCurrentIndex(self.frame.findData(previous.frame))
            else:self.frame.setEditText(str(previous.frame))
            self.orientation.setCurrentIndex(self.orientation.findData(previous.orientation))
            self.method.setCurrentIndex(self.method.findData(previous.method))
            self.demograph_layout.setCurrentIndex(self.demograph_layout.findData(previous.demograph_layout))
            self.demograph_value.setCurrentIndex(self.demograph_value.findData(previous.demograph_value))
            self.background.setCurrentText(previous.map_background);self.palette.setCurrentText(previous.palette)
            self.sampling.setCurrentIndex(self.sampling.findData(previous.sampling))
            self.maxima.setCurrentIndex(self.maxima.findData(previous.maxima_profile))
            self.pixel_size.setValue(previous.pixel_size);self.points.setChecked(previous.show_points)
            self.compare.setChecked(previous.compare);self.replicate.setChecked(previous.replicate)
            self.title.setText(previous.title)
            self.track_id.setValue(previous.track_id);self.track_confirmed.setChecked(previous.track_confirmed)
            self.time_interval.setValue(previous.time_interval)
            self.update_tracking_choices()
            self.tracked.setCurrentIndex(max(0,self.tracked.findData(previous.tracked_mask)))


    def edit_groups(self):
        self.tab.edit_groups()
        previous=self.condition.currentData()
        self.condition.clear();self.condition.addItem('All conditions','')
        values={str(v.get('condition','')).strip() for v in self.tab.assignments.values()}
        for table in self.tab.tables.values():
            if 'Condition' in table:values.update(table.Condition.dropna().astype(str))
        for name in sorted(values-{''}):self.condition.addItem(name,name)
        self.condition.setCurrentIndex(max(0,self.condition.findData(previous)))

    def update_description(self):
        self.description.setText({
            'distribution':'Compare cell areas, lengths or intensities. Recommended: a violin plot with one point per replicate mean.',
            'relationship':'Check whether two measurements vary together. Recommended: a scatter plot.',
            'demograph':'Order cells by their measured length, keeping their length envelope. Colour shows fluorescence or local cell width. Normalized-row layout is also available.',
            'cell_heatmap':'Average fluorescence on a straight reference cell. Curved cells are straightened along their own axes; choose one condition and a black or white background.',
            'maxima':'Place brightest pixels or kept foci on a normalized reference cell. Show individual points and relative density.',
            'kymograph':'Follow fluorescence along one cell across frames. Requires one XY and verified persistent cell/track identities. Saved tracking masks are detected automatically.',
            'counts':'Show the percentage of cells with 0, 1, 2… foci. Uses the per-cell table so cells without foci are included.'
        }[self.goal.currentData()])
        self.update_intensity_controls()

    def update_intensity_controls(self):
        width=self.goal.currentData()=='demograph' and self.demograph_value.currentData()=='local_width_um'
        self.normalization.setEnabled(not width)
        self.normalization.setToolTip('Local cell width stays in raw µm.' if width else '')

    def update_tracking_choices(self):
        old=self.tracked.currentData();self.tracked.clear()
        self.tracked.addItem('Source labels — only if identities were verified','')
        selected=self.sample.currentData()
        paths=sorted({path for source in self.sources if not selected or source['source_id']==selected for path in source.get('tracked_masks',[])})
        for path in paths:self.tracked.addItem(Path(path).name,path)
        found=self.tracked.findData(old)
        self.tracked.setCurrentIndex(found if found>0 else (1 if paths else 0))

    def update_metrics(self):
        table=self.tab.tables.get(self.dataset.currentText())
        for combo in (self.metric,self.other):
            old=combo.currentText();combo.clear()
            if table is not None:combo.addItems([str(c) for c in table.select_dtypes(include='number').columns if str(c).lower() not in ('cell_id','cell id','track_id','label')])
            if old:combo.setCurrentText(old)
        if self.other.count()>1 and self.other.findText(old)<0:self.other.setCurrentIndex(1)
        if self.goal.currentData()=='counts':
            names=[self.metric.itemText(i) for i in range(self.metric.count())]
            match=next((c for c in names if ('foci' in c.lower() and any(w in c.lower() for w in ('number','count','num ')))),None)
            if match and ('foci' not in self.metric.currentText().lower() or not any(w in self.metric.currentText().lower() for w in ('number','count','num '))):self.metric.setCurrentText(match)

    def _visible(self,page,widget,visible):
        widget.setVisible(visible)
        label=page.form.labelForField(widget)
        if label:label.setVisible(visible)

    def update_step(self,step):
        goal=self.goal.currentData();spatial=goal in SPATIAL_GOALS
        if step==1:
            kymo=goal=='kymograph'
            if kymo and not self.sample.currentData() and self.sample.count()>1:self.sample.setCurrentIndex(1)
            for widget in (self.tracked,self.track_id,self.time_interval):self._visible(self.data_page,widget,kymo)
            self.track_confirmed.setVisible(kymo)
            if kymo:self.update_tracking_choices()
            self.frame.setEnabled(not kymo)
            if kymo:self.frame.setCurrentIndex(self.frame.findData(None))
            for widget in (self.dataset,self.metric):self._visible(self.data_page,widget,not spatial)
            self._visible(self.data_page,self.other,goal=='relationship')
            for widget in (self.sample,self.channel,self.pixel_size):self._visible(self.data_page,widget,spatial)
            self.update_metrics()
            self.data_note.setText(f'{len(self.sources)} matching image/channel pairs found. Filtered masks are preferred. Calibration uses image metadata first.' if spatial else 'Use a per-cell table for cell distributions and foci counts. Conditions and replicates are set above the main figure view.')
        if step==2:
            options={'distribution':['Violin plot','Box plot','Histogram','ECDF'],'relationship':['Scatter','Mean curve'],
                     'demograph':['Demograph'],'cell_heatmap':['Normalized cell heatmap'],'maxima':['Maxima map'],'counts':['Foci count'],'kymograph':['Kymograph']}[goal]
            if goal!=getattr(self,'_appearance_goal',None):
                self.style.clear();self.style.addItems(options)
                self.normalization.setCurrentIndex(0)
                self.background.setCurrentText('black' if goal=='cell_heatmap' else 'white')
                self.palette.setCurrentText('turbo' if goal=='cell_heatmap' else 'inferno')
                if self._previous_plan is not None and self._previous_plan.goal==goal:
                    self.style.setCurrentText(self._previous_plan.kind)
                    self.normalization.setCurrentIndex(self.normalization.findData(self._previous_plan.normalization))
                    self.background.setCurrentText(self._previous_plan.map_background)
                    self.palette.setCurrentText(self._previous_plan.palette)
                self._appearance_goal=goal
            for widget in (self.orientation,self.method,self.sampling):self._visible(self.look_page,widget,spatial)
            self._visible(self.look_page,self.normalization,goal in ('demograph','cell_heatmap','kymograph'))
            for widget in (self.demograph_layout,self.demograph_value):self._visible(self.look_page,widget,goal=='demograph')
            for widget in (self.background,self.palette):self._visible(self.look_page,widget,spatial)
            self._visible(self.look_page,self.maxima,goal=='maxima');self.points.setVisible(goal=='maxima')
            self.compare.setVisible(not spatial);self.replicate.setVisible(goal=='distribution')
            note={
                'demograph':'In length-scaled columns, X is cell rank (short to long), and Y is axial distance divided by half the longest cell length. Cells keep their relative length envelope. Pole 0 is at the top. Local widths remain in µm.',
                'cell_heatmap':'Each cell contributes equally to each measured grid bin. Linear interpolation stays within measured pixel support; missing regions are not set to zero. The background changes only the display. Draw one condition at a time for separate comparable panels.',
                'kymograph':'Each row is a time point for the selected cell. Check tracking first. Geometric orientation does not establish pole identity when a cell rotates.',
                'maxima':'Automatic coordinates follow curved axes to the poles. Axial arc length and signed fraction of local width map to the reference cell; truly off-axis foci stay off-axis. Colour is relative point density, not fluorescence. Neither orientation identifies pole age.'
            }.get(goal,'Cells form each distribution. Replicate means are descriptive points; no significance test is inferred.')
            self.look_note.setText(note)
        if step==3:
            plan=self.plan();pairs=self.selected_pairs()
            self.review.setText(f'Figure: {plan.kind}\nPopulation: {plan.condition or "all conditions"}\nFrame: {plan.frame if plan.frame is not None else "all (repeated observations)"}\n'+
                (f'Channel: {plan.channel}\nXYs: {len(pairs)}\nUnfiltered masks: {sum(not p["filtered"] for p in pairs)}\nOrientation: {plan.orientation}\nCell coordinates: {plan.method}\nCell / track ID: {plan.track_id if plan.goal=="kymograph" else "not used"}\nMaxima: {plan.maxima_profile}\nIntensity: {plan.normalization}\nDemograph: {plan.demograph_layout}; {plan.demograph_value}\nBackground: {plan.map_background}\nProfiles will be calculated from the existing masks and images.\n' if spatial else f'Data: {plan.dataset}\nMeasurement: {plan.metric}\nCompare conditions: {plan.compare}\nReplicate means: {plan.replicate}\n')+
                '\nOutput: square figure + source rows + plot data + Python / R / MATLAB code.')

    def selected_pairs(self):
        return [s for s in self.sources if s['channel']==self.channel.currentText() and
                (not self.sample.currentData() or s['source_id']==self.sample.currentData()) and
                (not self.condition.currentData() or (self.tab.assignments.get(s['source_id'],{}).get('condition') or s.get('metadata',{}).get('condition',''))==self.condition.currentData())]

    def plan(self):
        options=dict(self._previous_plan.figure_options) if self._previous_plan and self._previous_plan.goal==self.goal.currentData() else {}
        for key in ('cmap','map_background','demograph_layout','cell_map_shape'):options.pop(key,None)
        if self._previous_plan and (self.metric.currentText()!=self._previous_plan.metric or self.other.currentText()!=self._previous_plan.second_metric):
            options.pop('xlabel',None);options.pop('ylabel',None)
        text=self.frame.currentText().strip()
        frame=self.frame.currentData() if text in ('First frame','All frames (repeated observations)') else text
        return FigurePlan(goal=self.goal.currentData(),kind=self.style.currentText(),dataset=self.dataset.currentText(),
            metric=self.metric.currentText(),second_metric=self.other.currentText(),condition=self.condition.currentData(),
            frame=frame,channel=self.channel.currentText(),source_id=self.sample.currentData(),
            normalization=('raw' if self.goal.currentData()=='demograph' and self.demograph_value.currentData()=='local_width_um' else self.normalization.currentData()),orientation=self.orientation.currentData(),
            maxima_profile=self.maxima.currentData(),show_points=self.points.isChecked(),pixel_size=self.pixel_size.value(),
            method=self.method.currentData(),track_id=self.track_id.value(),track_confirmed=self.track_confirmed.isChecked(),tracked_mask=self.tracked.currentData() or '',time_interval=self.time_interval.value(),sampling=self.sampling.currentData(),figure_options=options,compare=self.compare.isChecked(),replicate=self.replicate.isChecked(),title=self.title.text().strip(),
            demograph_layout=self.demograph_layout.currentData(),demograph_value=self.demograph_value.currentData(),map_background=self.background.currentText(),palette=self.palette.currentText())

    def validate_step(self,step):
        from PyQt6.QtWidgets import QMessageBox
        if step==1 and self.goal.currentData()=='kymograph':
            if len(self.selected_pairs())!=1 or not self.track_confirmed.isChecked():
                QMessageBox.information(self,'Check cell identity','Choose one sample/XY and verify that the selected ID follows the same cell over time. Run Tracking first if IDs change.');return False
        if step==1 and self.frame.currentText() not in ('First frame','All frames (repeated observations)'):
            try:float(self.frame.currentText())
            except ValueError:
                QMessageBox.information(self,'Invalid frame','Use a 0-based frame number, First frame, or All frames.');return False
        if step==1 and self.goal.currentData() in SPATIAL_GOALS and not self.selected_pairs():
            QMessageBox.information(self,'No matching images','No matching mask/channel pair was found for this population. Check the project folder and Conditions & replicates. Advanced controls still allow manual profile extraction.');return False
        if step==1 and self.goal.currentData() not in SPATIAL_GOALS and not self.metric.currentText():
            QMessageBox.information(self,'No measurement','Choose a table with numeric measurements.');return False
        if step==3:
            try:self.tab.apply_figure_plan(self.plan(),self.selected_pairs())
            except ValueError as exc:QMessageBox.information(self,'Check figure choices',str(exc));return False
        return True
