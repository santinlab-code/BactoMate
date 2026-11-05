"""Full-width analysis settings and an optional, read-only data window."""
import pandas as pd
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import (QComboBox, QDialog, QFormLayout, QGridLayout,
                             QGroupBox, QHBoxLayout, QLabel, QLayout, QSizePolicy,
                             QStackedWidget, QTableView, QVBoxLayout, QWidget)


class AnalysisControlStack(QStackedWidget):
    """A hidden long advanced form must not add empty scrolling to simple mode."""
    def __init__(self):
        super().__init__()
        self.layout().setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        self.currentChanged.connect(self.updateGeometry)

    def sizeHint(self):
        page = self.currentWidget()
        return page.sizeHint() if page is not None else QSize(0, 0)

    def minimumSizeHint(self):
        page = self.currentWidget()
        return QSize(0, page.minimumSizeHint().height()) if page is not None else QSize(0, 0)


class AnalysisCards(QWidget):
    """Reflow settings groups, keeping whole controls at their native heights."""
    def __init__(self, parent=None, *, max_columns=3):
        super().__init__(parent)
        self.cards = []
        self.max_columns = max_columns
        self.columns = 0
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(12)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.grid.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

    def add_card(self, card):
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self.cards.append(card)
        self.reflow()

    def reflow(self):
        columns = max(1, min(self.max_columns, (self.width() + 12) // 372))
        if columns != self.columns:
            for index, card in enumerate(self.cards):
                self.grid.removeWidget(card)
                self.grid.addWidget(card, index // columns, index % columns,
                                    Qt.AlignmentFlag.AlignTop)
            for col in range(self.max_columns):
                self.grid.setColumnStretch(col, 1 if col < columns else 0)
            self.columns = columns
        elif self.grid.count() != len(self.cards):
            for index, card in enumerate(self.cards):
                self.grid.removeWidget(card)
                self.grid.addWidget(card, index // columns, index % columns,
                                    Qt.AlignmentFlag.AlignTop)
        self.grid.invalidate()
        self.setMinimumHeight(self.grid.minimumSize().height())
        self.updateGeometry()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.reflow()

    def showEvent(self, event):
        super().showEvent(event)
        self.reflow()


def settings_group(title, rows, *, help_text=''):
    group = QGroupBox(title)
    outer = QVBoxLayout(group)
    form = QFormLayout()
    form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
    form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
    for label, widget in rows:
        widget.setMinimumWidth(0)
        if isinstance(widget, QComboBox):
            widget.setMinimumContentsLength(8)
            widget.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        if label:
            form.addRow(label, widget)
        else:
            form.addRow(widget)
    outer.addLayout(form)
    if help_text:
        from bactomate.gui.widgets import create_info_icon
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(create_info_icon(help_text, parent_widget=group, compact=True))
        outer.addLayout(row)
    return group


class AnalysisDataModel(QAbstractTableModel):
    """Show all source rows lazily; never edit or copy the scientific table."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.table = pd.DataFrame()

    def set_table(self, table):
        self.beginResetModel()
        self.table = table if table is not None else pd.DataFrame()
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.table)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.table.columns)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if (index.isValid() and 0 <= index.row() < len(self.table)
                and 0 <= index.column() < len(self.table.columns)
                and role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ToolTipRole)):
            return str(self.table.iloc[index.row(), index.column()])
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return str(self.table.columns[section]) if 0 <= section < len(self.table.columns) else None
        return str(section + 1) if 0 <= section < len(self.table) else None


class AnalysisDataWindow(QDialog):
    hidden = pyqtSignal()

    def __init__(self, owner):
        super().__init__(owner, Qt.WindowType.Window)
        self.setWindowTitle('Analysis — data table')
        self.setModal(False)
        self.resize(1000, 600)
        self.owner = owner
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        row.addWidget(QLabel('Data table'))
        self.dataset = QComboBox()
        row.addWidget(self.dataset, 1)
        layout.addLayout(row)
        self.info = QLabel()
        layout.addWidget(self.info)
        self.model = AnalysisDataModel(self)
        self.view = QTableView()
        self.view.setModel(self.model)
        self.view.setAlternatingRowColors(True)
        layout.addWidget(self.view, 1)
        self.dataset.currentTextChanged.connect(self.refresh)

    def set_tables(self, selected):
        self.dataset.blockSignals(True)
        self.dataset.clear()
        self.dataset.addItems(list(self.owner.tables))
        self.dataset.setCurrentText(selected)
        self.dataset.blockSignals(False)
        self.refresh()

    def refresh(self, *_):
        table = self.owner.tables.get(self.dataset.currentText())
        self.model.set_table(table)
        rows, cols = self.model.rowCount(), self.model.columnCount()
        self.info.setText(f'{rows:,} source rows · {cols} columns · read-only. Figure-specific values are included in figure exports.')

    def hideEvent(self, event):
        super().hideEvent(event)
        self.hidden.emit()
