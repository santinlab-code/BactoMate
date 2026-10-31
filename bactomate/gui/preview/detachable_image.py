"""Move a canvas and its controls to another screen without losing state."""
from PyQt6.QtCore import Qt, QEvent, QObject
from PyQt6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,
                             QWidget,QGridLayout,QScrollBar,QSplitter,QSizePolicy)


class _ImageWindow(QDialog):
    def reject(self):
        # Escape must not dismiss an image being inspected.
        pass

    def closeEvent(self,event):
        self.controller.attach()
        event.ignore()


class DetachablePreviewImage(QObject):
    def __init__(self,preview,*,title='Segmentation — image',auto_detach=False,extra_widgets=()):
        super().__init__(preview)
        self.preview,self.canvas=preview,preview.canvas
        self._lut_policy=preview.lut_section.sizePolicy()
        self.home=self.canvas.parentWidget(); self.layout=self.home.layout()
        self.index=self.layout.indexOf(self.canvas); self.is_detached=False
        self._docked=[(widget,widget.parentWidget().layout(),0)
                      for widget in (self.canvas,*extra_widgets,preview.lut_section)]
        self.window=_ImageWindow(preview,Qt.WindowType.Window); self.window.controller=self
        self.window.setWindowTitle(title); self.window.resize(1280,800)
        self.floating_layout=QVBoxLayout(self.window); self.controls_layout=QHBoxLayout()
        attach=QPushButton('Attach image'); attach.clicked.connect(self.attach)
        self.recenter=QPushButton('Recenter / fit image'); self.recenter.clicked.connect(self.canvas.reset_view)
        self.controls_layout.addWidget(attach); self.controls_layout.addWidget(self.recenter)
        self.floating_layout.addLayout(self.controls_layout)
        self.floating_layout.addWidget(QLabel('Mouse wheel: zoom · drag: pan · scrollbars: visible center in image pixels'))
        self.body=QSplitter(Qt.Orientation.Horizontal)
        self.image_host=QWidget(); grid=QGridLayout(self.image_host); grid.setContentsMargins(0,0,0,0)
        self.horizontal=QScrollBar(Qt.Orientation.Horizontal); self.vertical=QScrollBar(Qt.Orientation.Vertical)
        grid.addWidget(self.horizontal,1,0); grid.addWidget(self.vertical,0,1)
        grid.setColumnStretch(0,1); grid.setRowStretch(0,1)
        self.lut_sidebar=QWidget(); self.lut_layout=QVBoxLayout(self.lut_sidebar)
        self.lut_layout.setContentsMargins(4,0,0,0)
        self.lut_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.lut_sidebar.setMinimumWidth(260); self.lut_sidebar.setMaximumWidth(400)
        self.body.addWidget(self.image_host); self.body.addWidget(self.lut_sidebar)
        self.body.setStretchFactor(0,1); self.body.setSizes([900,320])
        self.floating_layout.addWidget(self.body,1)
        self.horizontal.valueChanged.connect(self._scroll); self.vertical.valueChanged.connect(self._scroll)
        self.canvas.viewport_changed.connect(self._sync_scrollbars)
        self.canvas.view_scale_changed.connect(self._sync_scrollbars)
        self.button=QPushButton('Detach image'); self.button.clicked.connect(self.detach)
        preview._layout.addWidget(self.button); preview.installEventFilter(self)
        if auto_detach:self.detach()

    def detach(self):
        if not self.is_detached:
            self._docked=[(w,layout,layout.indexOf(w)) for w,layout,_ in self._docked]
            self.index=self.layout.indexOf(self.canvas)
            self._lut_expanded=self.preview.lut_section.is_expanded()
            self._lut_header_hidden=self.preview.lut_section._header.isHidden()
        self.preview.lut_section.set_expanded(True)
        self.preview.lut_section._header.hide()
        for widget,_,_ in self._docked[1:-1]:
            self.floating_layout.insertWidget(self.floating_layout.indexOf(self.body),widget)
        self.image_host.layout().addWidget(self.canvas,0,0)
        self.preview.lut_section.setSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Maximum)
        self.lut_layout.addWidget(self.preview.lut_section)
        self.is_detached=True; self.button.setEnabled(False); self.window.show()
        self._sync_scrollbars(); self.highlight()

    def attach(self):
        if not self.is_detached:return
        self.preview.lut_section._header.setVisible(not self._lut_header_hidden)
        self.preview.lut_section.set_expanded(self._lut_expanded)
        self.preview.lut_section.setSizePolicy(self._lut_policy)
        for widget,layout,index in sorted(self._docked,key=lambda slot:slot[2]):
            layout.insertWidget(index,widget,1 if widget is self.canvas else 0)
        self.is_detached=False; self.window.hide(); self.button.setEnabled(True)

    def _sync_scrollbars(self,*_):
        size=self.canvas._image_size
        if not self.is_detached or not size:return
        scale=max(self.canvas.view_scale(),1e-9); offset=self.canvas._total_offset(scale)
        centers=((self.canvas.width()/2-offset.x())/scale,(self.canvas.height()/2-offset.y())/scale)
        for bar,extent,visible,center in zip((self.horizontal,self.vertical),size,
                (self.canvas.width()/scale,self.canvas.height()/scale),centers):
            bar.blockSignals(True)
            bar.setRange(0,round(extent*100)); bar.setPageStep(max(1,round(visible*100)))
            bar.setSingleStep(100); bar.setValue(round(center*100))
            bar.setToolTip(f'Visible center: {center:.1f} / {extent} px')
            bar.blockSignals(False)

    def _scroll(self,*_):
        if not self.is_detached:return
        self.canvas.center_on_image_point(self.horizontal.value()/100,self.vertical.value()/100)
        self._sync_scrollbars()

    def eventFilter(self,obj,event):
        if obj is getattr(self,'preview',None):
            if event.type()==QEvent.Type.Hide:self.window.hide()
            elif event.type()==QEvent.Type.Show and self.is_detached:self.window.show()
        return False

    def highlight(self,*_):
        pass
