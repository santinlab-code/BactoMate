"""Filtering display: unchanged background, selected cell edges, detected foci only."""
import numpy as np
from bactomate.modules.segmentation_display import label_outlines


def white_cell_contours(rgb, labels, *, accepted=None, color=(255,255,255)):
    result=np.asarray(rgb).copy()
    # Empty means no kept cells; None is reserved for callers showing all labels.
    visible=labels if accepted is None else np.where(np.isin(labels,list(accepted)),labels,0)
    result[label_outlines(visible)]=color
    return result


def draw_detected_foci(rgb, detected, passed, mask_shape):
    """Draw only CSV detections. Green=kept, red=excluded; never grow new spots."""
    def key(p):return (int(float(p['y'])),int(float(p['x'])))
    kept={key(p) for p in passed}
    sy,sx=rgb.shape[0]/mask_shape[0],rgb.shape[1]/mask_shape[1]
    for peak in detected:
        try:
            y,x=round(float(peak['y'])*sy),round(float(peak['x'])*sx)
            color=(0,255,0) if key(peak) in kept else (255,0,0)
        except (KeyError,ValueError,TypeError):continue
        for dy,dx in ((0,0),(-2,0),(2,0),(0,-2),(0,2),(-1,-1),(-1,1),(1,-1),(1,1)):
            yy,xx=y+dy,x+dx
            if 0<=yy<rgb.shape[0] and 0<=xx<rgb.shape[1]:rgb[yy,xx]=color
    return rgb


def ten_row_table(table):
    from PyQt6.QtCore import QEvent, QObject, QTimer
    if hasattr(table, '_ten_row_sizer'):
        table._ten_row_sizer.sync()
        return

    class TableSizer(QObject):
        pending = False

        def queue(self, *_):
            if not self.pending:
                self.pending = True
                QTimer.singleShot(0, self.sync)

        def eventFilter(self, obj, event):
            if event.type() in (QEvent.Type.Show, QEvent.Type.FontChange,
                                QEvent.Type.StyleChange):
                self.queue()
            return False

        def sync(self):
            from PyQt6 import sip
            if sip.isdeleted(table):
                return
            self.pending = False
            vertical, horizontal = table.verticalHeader(), table.horizontalHeader()
            row = max(22, table.fontMetrics().height() + 6, vertical.minimumSectionSize())
            if vertical.defaultSectionSize() != row:
                vertical.setDefaultSectionSize(row)
            header = max(horizontal.sizeHint().height(), horizontal.fontMetrics().height() + 8)
            if horizontal.isVisible():
                header = max(header, horizontal.height())
            # Headers can acquire their actual size only after columns/style exist.
            height = header + 10 * row + 2 * table.frameWidth() + table.horizontalScrollBar().sizeHint().height()
            if table.minimumHeight() != height or table.maximumHeight() != height:
                table.setFixedHeight(height)

    sizer = TableSizer(table)
    table._ten_row_sizer = sizer
    for widget in (table, table.horizontalHeader(), table.verticalHeader()):
        widget.installEventFilter(sizer)
    table.horizontalHeader().geometriesChanged.connect(sizer.queue)
    table.verticalHeader().geometriesChanged.connect(sizer.queue)
    sizer.sync()
