"""Filtering pages keep native control heights inside a bounded preview pane."""
from PyQt6.QtCore import QEvent, QSize, Qt, QTimer
from PyQt6.QtWidgets import (QFrame, QGridLayout, QLayout, QScrollArea, QSizePolicy,
                             QSplitter, QTabWidget, QVBoxLayout, QWidget)


class WrappingControls(QWidget):
    """Wrap whole controls without reparenting or hiding them during resize."""
    def __init__(self, *items, parent=None):
        super().__init__(parent)
        self._items = []
        self._grid = QGridLayout(self)
        self._grid.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(6)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        for item in items:
            self.add_widget(item)

    def minimumSizeHint(self):
        width = max((max(item.minimumSizeHint().width(), item.sizeHint().width())
                     for item in self._items), default=0)
        return QSize(width, self._grid.minimumSize().height())

    def add_widget(self, item):
        self._items.append(item)
        self.reflow()

    def reflow(self):
        row = col = used = 0
        for item in self._items:
            width = max(item.sizeHint().width(), item.minimumSizeHint().width(), 1)
            if col and used + 6 + width > self.width():
                row += 1
                col = used = 0
            self._grid.removeWidget(item)
            self._grid.addWidget(item, row, col, Qt.AlignmentFlag.AlignLeft)
            col += 1
            used += width + 6
        self._grid.invalidate()
        self.setMinimumHeight(self._grid.minimumSize().height())
        self.updateGeometry()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.reflow()

    def showEvent(self, event):
        super().showEvent(event)
        self.reflow()


class _FilterPage(QWidget):
    def __init__(self, content):
        super().__init__()
        self.content = content
        self._pending = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(content)
        content.installEventFilter(self)

    def minimumSizeHint(self):
        # Let grids reflow to the actual width, while preserving their row heights.
        return QSize(0, max(self.content.sizeHint().height(),
                            self.content.minimumSizeHint().height(), 0))

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Type.LayoutRequest, QEvent.Type.Resize,
                            QEvent.Type.Show, QEvent.Type.FontChange):
            if not self._pending:
                self._pending = True
                QTimer.singleShot(0, self._sync_height)
        return False

    def _sync_height(self):
        from PyQt6 import sip
        if sip.isdeleted(self) or sip.isdeleted(self.content):
            return
        self._pending = False
        height = self.minimumSizeHint().height()
        if self.minimumHeight() != height:
            self.setMinimumHeight(height)
            self.updateGeometry()


class FilteringWorkspaceTabs(QTabWidget):
    """Independent fixed pages; overflow is available only when space is too small."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pages = {}
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tabBar().setExpanding(False)
        self.tabBar().setElideMode(Qt.TextElideMode.ElideRight)

    def addTab(self, content, title):
        page = _FilterPage(content)
        area = QScrollArea()
        area.setFrameShape(QFrame.Shape.NoFrame)
        area.setWidgetResizable(True)
        area.setWidget(page)
        area.setMinimumSize(0, 0)
        self._pages[content] = area
        index = super().addTab(area, title)
        self.setTabToolTip(index, title)
        return index

    def setCurrentWidget(self, content):
        super().setCurrentWidget(self._pages.get(content, content))


def mount_filtering_workspace(preview, settings, manual_controls):
    """Put the attached image beside the workspace, rather than below all tables."""
    outer = preview._layout
    index = outer.indexOf(settings)
    for widget in (settings, preview.canvas, preview.lut_section):
        outer.removeWidget(widget)
    image = QWidget()
    image.setObjectName('FilteringAttachedImage')
    manual_controls.ensurePolished()
    image.setMinimumWidth(max(160, manual_controls.minimumSizeHint().width()))
    layout = QVBoxLayout(image)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(manual_controls)
    layout.addWidget(preview.canvas, 1)
    layout.addWidget(preview.lut_section)
    body = QSplitter(Qt.Orientation.Horizontal)
    body.setObjectName('FilteringWorkspaceSplitter')
    body.setChildrenCollapsible(False)
    body.addWidget(settings)
    body.addWidget(image)
    body.setStretchFactor(0, 3)
    body.setStretchFactor(1, 2)
    body.setSizes([600, 220])
    outer.insertWidget(index, body, 1)
    preview._filter_workspace_body = body
    preview._filter_image_home = image
