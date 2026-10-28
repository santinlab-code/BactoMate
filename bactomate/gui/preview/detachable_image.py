"""Move a preview canvas to another screen without rebuilding its controls."""
from PyQt6.QtCore import Qt, QEvent, QObject
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel


class _ImageWindow(QDialog):
    def closeEvent(self, event):
        self.controller.attach()
        event.ignore()


class DetachablePreviewImage(QObject):
    def __init__(self, preview, *, title='Segmentation — image', auto_detach=False):
        super().__init__(preview)
        self.preview, self.canvas = preview, preview.canvas
        self.home = self.canvas.parentWidget()
        self.layout = self.home.layout()
        self.index = self.layout.indexOf(self.canvas)
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
            self.index = self.layout.indexOf(self.canvas)
        self.floating_layout.addWidget(self.canvas, 1)
        self.button.setEnabled(False)
        self.window.show()
        self.highlight()

    def attach(self):
        self.layout.insertWidget(self.index, self.canvas, 1)
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
