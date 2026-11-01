"""One native window and one canvas per figure, with editable publication options."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,QFileDialog,
    QMessageBox,QTabWidget,QWidget,QFormLayout,QLineEdit,QDoubleSpinBox,QSpinBox,QCheckBox,
    QComboBox,QTableWidget,QTableWidgetItem,QColorDialog,QDialogButtonBox)
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg,NavigationToolbar2QT
from bactomate.modules.figure_analysis import prepare,draw,export_bundle


class FigureOptions(QDialog):
    def __init__(self,window):
        super().__init__(window);self.target=window;self.setWindowTitle('Figure options');self.resize(630,690)
        layout=QVBoxLayout(self);tabs=QTabWidget();layout.addWidget(tabs);self.values={}
        def page(title):
            widget=QWidget();form=QFormLayout(widget);form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
            tabs.addTab(widget,title);return form
        def text(form,key,label,value):
            widget=QLineEdit(str(value));self.values[key]=widget;form.addRow(label,widget);return widget
        def spin(form,key,label,value,lo,hi,step=.1):
            widget=QDoubleSpinBox();widget.setRange(lo,hi);widget.setDecimals(3);widget.setSingleStep(step);widget.setValue(value)
            self.values[key]=widget;form.addRow(label,widget);return widget
        def check(form,key,label,value):
            widget=QCheckBox(label);widget.setChecked(value);self.values[key]=widget;form.addRow(widget);return widget
        spec=window.spec;ax=window.figure.axes[0]
        form=page('Labels / axes')
        text(form,'title','Title',spec.title);text(form,'xlabel','X label',spec.xlabel or ax.get_xlabel());text(form,'ylabel','Y label',spec.ylabel or ax.get_ylabel())
        for key,label in [('x_min','X minimum'),('x_max','X maximum'),('y_min','Y minimum'),('y_max','Y maximum')]:
            text(form,key,label,'' if getattr(spec,key) is None else getattr(spec,key)).setPlaceholderText('Automatic')
        spin(form,'x_tick_rotation','X label rotation (°)',spec.x_tick_rotation,-180,180,5)
        check(form,'show_title','Show title',spec.show_title)
        check(form,'show_grid','Show grid',spec.show_grid);check(form,'show_legend','Show legend',spec.show_legend)
        form=page('Categories')
        form.addRow(QLabel('Select a category and move it. Labels and colours can be edited.'))
        from bactomate.modules.figure_style import ordered_groups
        groups=ordered_groups(window.plot,spec) if 'group' in window.plot else []
        self.categories=QTableWidget(len(groups),3);self.categories.setHorizontalHeaderLabels(['Category','Display label','Colour'])
        self.categories.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        for row,(name,_) in enumerate(groups):
            item=QTableWidgetItem(name);item.setFlags(item.flags()&~Qt.ItemFlag.ItemIsEditable);self.categories.setItem(row,0,item)
            self.categories.setItem(row,1,QTableWidgetItem(spec.category_labels.get(name,name)))
            self.categories.setItem(row,2,QTableWidgetItem(spec.category_colors.get(name,'')))
        self.categories.horizontalHeader().setStretchLastSection(True);form.addRow(self.categories)
        buttons=QHBoxLayout()
        for title,callback in [('Move up',lambda:self.move(-1)),('Move down',lambda:self.move(1)),('Choose colour…',self.choose_color)]:
            button=QPushButton(title);button.clicked.connect(callback);buttons.addWidget(button)
        form.addRow(buttons)
        spin(form,'category_spacing','Box/violin X spacing',spec.category_spacing,.1,10)
        spin(form,'category_width','Box/violin width',spec.category_width,.05,5)
        form=page('Appearance')
        spin(form,'font_size','Font size (pt)',spec.font_size,4,60,1)
        spin(form,'point_size','Point size (pt²)',spec.point_size,1,500,1)
        spin(form,'point_alpha','Point / bar opacity',spec.point_alpha,.01,1)
        spin(form,'line_width','Line width',spec.line_width,.1,10)
        check(form,'show_outliers','Show box plot outliers',spec.show_outliers)
        check(form,'show_points','Show maxima points',spec.show_points)
        cmap=QComboBox();cmap.addItems(['viridis','inferno','magma','plasma','turbo','cividis','coolwarm','gray']);cmap.setCurrentText(spec.cmap)
        self.values['cmap']=cmap;form.addRow('Colour map',cmap)
        for key,label in [('colorbar_min','Colour scale minimum'),('colorbar_max','Colour scale maximum')]:
            text(form,key,label,'' if getattr(spec,key) is None else getattr(spec,key)).setPlaceholderText('Automatic')
        form=page('Export size')
        self.square=QCheckBox('Square export');self.square.setChecked(spec.figure_width==spec.figure_height);form.addRow(self.square)
        width=spin(form,'figure_width','Width (inches)',spec.figure_width,2,20)
        height=spin(form,'figure_height','Height (inches)',spec.figure_height,2,20)
        def match_square():
            height.setEnabled(not self.square.isChecked())
            if self.square.isChecked():height.setValue(width.value())
        width.valueChanged.connect(match_square);self.square.toggled.connect(match_square);match_square()
        dpi=QSpinBox();dpi.setRange(72,1200);dpi.setValue(spec.export_dpi);form.addRow('PNG DPI',dpi);self.values['export_dpi']=dpi
        form.addRow(QLabel('Display fills the window. Export size is independent of the screen size.'))
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Apply|QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply)
        buttons.rejected.connect(self.reject);layout.addWidget(buttons)

    def move(self,direction):
        table=self.categories;row=table.currentRow();target=row+direction
        if row<0 or not 0<=target<table.rowCount():return
        old=[table.takeItem(row,col) for col in range(3)];other=[table.takeItem(target,col) for col in range(3)]
        for col in range(3):table.setItem(row,col,other[col]);table.setItem(target,col,old[col])
        table.selectRow(target)

    def choose_color(self):
        row=self.categories.currentRow()
        if row<0:return
        color=QColorDialog.getColor(parent=self)
        if color.isValid():self.categories.item(row,2).setText(color.name())

    def apply(self):
        from matplotlib.colors import is_color_like
        try:
            values={}
            for key,widget in self.values.items():
                if isinstance(widget,QCheckBox):value=widget.isChecked()
                elif isinstance(widget,(QDoubleSpinBox,QSpinBox)):value=widget.value()
                elif isinstance(widget,QComboBox):value=widget.currentText()
                else:
                    value=widget.text()
                    if key in ('x_min','x_max','y_min','y_max','colorbar_min','colorbar_max'):value=float(value) if value.strip() else None
                values[key]=value
            order=[];labels={};colors={}
            for row in range(self.categories.rowCount()):
                name=self.categories.item(row,0).text();order.append(name)
                labels[name]=self.categories.item(row,1).text();color=self.categories.item(row,2).text().strip()
                if color:
                    if not is_color_like(color):raise ValueError(f'Invalid colour: {color}')
                    colors[name]=color
            values.update(group_order=tuple(order),category_labels=labels,category_colors=colors)
            self.target.redraw(replace(self.target.spec,**values))
        except Exception as exc:QMessageBox.warning(self,'Cannot apply figure options',str(exc))


class PublicationFigureWindow(QDialog):
    def __init__(self,tab,source,spec,provenance,labels):
        super().__init__(tab,Qt.WindowType.Window)
        self.tab=tab;self.source=source.copy();self.spec=deepcopy(spec);self.provenance=deepcopy(provenance)
        self.initial_labels=dict(labels);self.plan=None
        self.setWindowTitle(spec.title or spec.kind);self.resize(950,950)
        layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0)
        self.figure=Figure(figsize=(spec.figure_width,spec.figure_height));self.canvas=FigureCanvasQTAgg(self.figure)
        self.toolbar=NavigationToolbar2QT(self.canvas,self);layout.addWidget(self.toolbar)
        row=QHBoxLayout()
        for title,callback in [('Figure options…',self.options),('Edit with Figure guide…',self.edit_guide),('Export figure, data && code…',self.export)]:
            button=QPushButton(title);button.clicked.connect(callback);row.addWidget(button)
        layout.addLayout(row);layout.addWidget(self.canvas,1)
        self.redraw(spec)

    def reject(self):
        # Keep the figure visible when Escape is pressed.
        pass

    def redraw(self,spec):
        used,plot,labels=prepare(self.source,spec)
        # Friendly labels supplied by the guide; keep plot-type derived labels current.
        for key in ('xlabel','ylabel'):
            if key in self.initial_labels and spec.kind not in ('Demograph','Maxima map','Kymograph'):labels[key]=self.initial_labels[key]
        previous=self.spec
        try:draw(self.figure,plot,spec,labels)
        except Exception:
            if hasattr(self,'plot'):draw(self.figure,self.plot,previous,self.labels)
            raise
        self.spec=deepcopy(spec);self.used,self.plot,self.labels=used,plot,labels
        self.setWindowTitle(spec.title or spec.kind);self.toolbar.update();self.canvas.draw_idle()
        if getattr(self.tab,'_figure_windows',[]) and self.tab._figure_windows[-1] is self:
            self.tab.snapshot=(*self.snapshot(),)

    def snapshot(self):return (self.used.copy(),self.plot.copy(),deepcopy(self.spec),dict(self.labels),deepcopy(self.provenance))

    def options(self):
        dialog=FigureOptions(self);dialog.exec();dialog.deleteLater()

    def edit_guide(self):
        if not hasattr(self.tab,'open_figure_guide'):return
        root=self.provenance.get('root')
        current=self.tab.context_root()
        if root and current is not None and Path(root).resolve()!=Path(current).resolve():
            QMessageBox.information(self,'Figure from another project','Open this figure’s project to edit it with Figure guide. Figure options and export remain available.');return
        if self.plan is None:
            from bactomate.gui.figure_guide import FigurePlan
            goal={'Box plot':'distribution','Violin plot':'distribution','Histogram':'distribution','ECDF':'distribution',
                  'Scatter':'relationship','Mean curve':'relationship','Foci count':'counts'}.get(self.spec.kind)
            if goal is None:
                QMessageBox.information(self,'Advanced figure','Use Figure options for this figure, or start a new spatial figure with Figure guide.');return
            source=self.used.copy()
            if self.spec.group and 'Condition' not in source:source['Condition']=source[self.spec.group]
            if self.spec.replicate and 'Replicate' not in source:source['Replicate']=source[self.spec.replicate]
            key=f'Figure source {len(self.tab.tables)+1}'
            self.tab._spatial_tables[key]=source
            self.tab.set_tables({**self.tab.tables,key:source},self.provenance)
            self.plan=FigurePlan(goal=goal,kind=self.spec.kind,dataset=key,metric=self.spec.x,second_metric=self.spec.y,
                compare=bool(self.spec.group),replicate=bool(self.spec.replicate),title=self.spec.title)
        if self.plan is not None:
            plan=deepcopy(self.plan);plan.title=self.spec.title;plan.show_points=self.spec.show_points
            scientific={'kind','x','y','value','group','sort','bins','title','filter_column','filter_value','minimum','maximum',
                        'track_confirmed','normalization','replicate','show_replicates','relative_position','maxima_profile','show_points'}
            from dataclasses import fields
            plan.figure_options={field.name:deepcopy(getattr(self.spec,field.name)) for field in fields(self.spec) if field.name not in scientific}
            self.tab._last_figure_plan=plan
        self.tab.open_figure_guide(parent=self)

    def export(self):
        root=QFileDialog.getExistingDirectory(self,'Choose a folder for this figure')
        if not root:return
        try:
            from datetime import datetime
            folder=Path(root)/('figure_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
            export_bundle(folder,self.figure,self.used,self.plot,self.spec,self.labels,provenance=self.provenance)
            QMessageBox.information(self,'Figure exported',str(folder))
        except Exception as exc:QMessageBox.warning(self,'Export failed',str(exc))
