"""Detaching keeps the same canvas, LUT, and preview state."""
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QPixmap
from PyQt6.QtTest import QTest


def test_segmentation_image_detach_attach_and_lifecycle(qapp):
    from bactomate.gui.preview.preview_window import PreviewDialogBase
    from bactomate.gui.preview.detachable_image import DetachablePreviewImage
    preview = PreviewDialogBase(title='Segmentation Preview')
    controller = DetachablePreviewImage(preview)
    try:
        preview.show()
        qapp.processEvents()
        pixmap = QPixmap(100, 80)
        pixmap.fill(Qt.GlobalColor.gray)
        preview.canvas.set_pixmap(pixmap, (100, 80))
        original = preview.canvas
        preview.lut_widget.set_lut(20, 80)
        controller.button.click()
        assert original.parentWidget() is controller.window
        assert controller.window.isVisible()
        assert preview.lut_widget.current_lut() == (20, 80)
        controller.window.close()
        assert original.parentWidget() is controller.home
        controller.button.click()
        preview.hide()
        assert not controller.window.isVisible()
        preview.show()
        qapp.processEvents()
        assert controller.window.isVisible()
    finally:
        preview.close()


def test_image_click_and_drag_stay_distinct(qapp):
    from bactomate.gui.image_canvas import ImageCanvas
    canvas = ImageCanvas()
    canvas.resize(400, 300)
    pixmap = QPixmap(200, 150)
    pixmap.fill(Qt.GlobalColor.gray)
    canvas.set_pixmap(pixmap, (200, 150))
    clicks = []
    canvas.clicked_image.connect(lambda x, y: clicks.append((x, y)))
    canvas.show()
    qapp.processEvents()
    try:
        QTest.mouseClick(canvas, Qt.MouseButton.LeftButton, pos=QPoint(100, 100))
        assert clicks == [(50, 50)]
        QTest.mousePress(canvas, Qt.MouseButton.LeftButton, pos=QPoint(100, 100))
        QTest.mouseMove(canvas, QPoint(130, 110))
        QTest.mouseMove(canvas, QPoint(150, 120))
        QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, pos=QPoint(150, 120))
        assert clicks == [(50, 50)]
        assert not canvas._dragging
        assert not canvas._pan_offset.isNull()
    finally:
        canvas.close()
