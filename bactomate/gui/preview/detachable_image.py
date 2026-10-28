"""Move a preview canvas to another screen without rebuilding its controls."""
from PyQt6.QtCore import Qt, QEvent, QObject
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel


class _ImageWindow(QDialog):
    def closeEvent(self, event):
        self.controller.attach()
        event.ignore()


class DetachablePreviewImage(QObject):
    def __init__(self, preview, *, title='Segmentation — image', auto_detach=False, extra_widgets=()):
        super().__init__(preview)
        self.preview, self.canvas = preview, preview.canvas
        self.home = self.canvas.parentWidget()
        self.layout = self.home.layout()
        self.index = self.layout.indexOf(self.canvas)
        self._docked = [(widget, widget.parentWidget().layout(), 0)
                        for widget in (self.canvas, *extra_widgets, preview.lut_section)]
        self.window = _ImageWindow(preview, Qt.WindowType.Window)
        self.window.controller = self
        self.window.setWindowTitle(title)
        self.window.resize(1000, 800)
        self.floating_layout = QVBoxLayout(self.window)
        self.controls_layout = QHBoxLayout()
        attach = QPushButton('Attach image')
        attach.clicked.connect(self.attach)
        self.controls_layout.addWidget(attach)
        self.floating_layout.addLayout(self.controls_layout)
        self.floating_layout.addWidget(QLabel('Mouse wheel: zoom · drag: pan'))
        self.button = QPushButton('Detach image')
        self.button.clicked.connect(self.detach)
        preview._layout.addWidget(self.button)
        preview.installEventFilter(self)
        if auto_detach:
            self.detach()

    def detach(self):
        if self.canvas.parentWidget() is self.home:
            self._docked = [(widget, layout, layout.indexOf(widget))
                            for widget, layout, _ in self._docked]
            self.index = self.layout.indexOf(self.canvas)
        # Manual actions above the image; the same LUT widget below it.
        for widget, _, _ in self._docked[1:-1]:
            self.floating_layout.addWidget(widget)
        self.floating_layout.addWidget(self.canvas, 1)
        self.floating_layout.addWidget(self.preview.lut_section)
        self.button.setEnabled(False)
        self.window.show()
        self.highlight()

    def attach(self):
        for widget, layout, index in sorted(self._docked, key=lambda slot: slot[2]):
            layout.insertWidget(index, widget, 1 if widget is self.canvas else 0)
        self.window.hide()
        self.button.setEnabled(True)

    def eventFilter(self, obj, event):
        if obj is getattr(self, 'preview', None):
            if event.type() == QEvent.Type.Hide:
                self.window.hide()
            elif event.type() == QEvent.Type.Show and self.canvas.parentWidget() is self.window:
                self.window.show()
        return False

    def highlight(self, *_):
        pass
