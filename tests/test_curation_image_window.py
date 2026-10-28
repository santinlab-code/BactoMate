import numpy as np
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtTest import QTest


def test_detach_click_highlight_keyboard_exclusion_and_attach(tmp_path, qapp):
    from tests.test_filtering_preview_apply_flow import (
        _open_preview, _wait_for_filter_apply, _wait_for_apply_generation, _shutdown, _wait_until)
    tab, parent, dlg = _open_preview(tmp_path)
    try:
        assert _wait_for_filter_apply(dlg)
        controller = dlg._curation_image_window
        assert controller.window.isVisible()
        assert dlg.canvas.parentWidget() is controller.window
        panel = controller.panel
        assert _wait_until(lambda: panel.isEnabled())
        shape = np.asarray(controller.mask()).shape
        size = dlg.canvas._image_size
        # Exercise a real left click with zoom and pan applied.
        canvas = dlg.canvas
        canvas._zoom = 1.7
        image_x, image_y = 40*size[0]/shape[1], 34*size[1]/shape[0]
        canvas.center_on_image_point(image_x, image_y)
        scale = canvas.view_scale()
        click = canvas._total_offset(scale) + QPointF(image_x*scale, image_y*scale)
        QTest.mouseClick(canvas, Qt.MouseButton.LeftButton, pos=click.toPoint())
        assert not canvas._dragging
        assert not canvas._left_potential_click
        assert panel.table.selectedItems()[0].text() == '1'
        assert len(dlg.canvas.object_selection_boxes) == 1
        rid = dlg._preview_request_id
        QTest.keyClick(dlg.canvas, Qt.Key.Key_Delete)
        assert _wait_for_apply_generation(dlg, rid_before=rid)
        assert 1 not in dlg._last_preview['accepted']
        assert panel.cur.data['cells']['0']['1'] is False
        assert panel.manual_controls.parentWidget() is controller.window
        assert dlg.lut_section.parentWidget() is controller.window
        assert _wait_until(lambda: panel.isEnabled())
        # Right click restores the excluded object at its image location.
        scale = canvas.view_scale()
        click = canvas._total_offset(scale) + QPointF(image_x*scale, image_y*scale)
        rid = dlg._preview_request_id
        QTest.mouseClick(canvas, Qt.MouseButton.RightButton, pos=click.toPoint())
        assert _wait_for_apply_generation(dlg, rid_before=rid)
        assert 1 in dlg._last_preview['accepted']
        assert panel.cur.data['cells']['0']['1'] is True
        slots = list(controller._docked)
        controller.window.close()
        assert not controller.window.isVisible()
        assert dlg.canvas.parentWidget() is controller.home
        assert dlg.lut_section.parentWidget() is dlg
        for widget, layout, index in slots:
            assert layout.indexOf(widget) == index
        controller.detach()
        assert dlg.lut_section.parentWidget() is controller.window
        assert panel.manual_controls.parentWidget() is controller.window
        assert controller.window.isVisible()
        dlg.hide()
        assert not controller.window.isVisible()
    finally:
        _shutdown(tab, parent)


def test_foci_table_highlight_and_backspace_are_channel_specific(tmp_path, qapp):
    from PyQt6.QtWidgets import QTableWidgetItem
    from tests.test_filtering_preview_apply_flow import _open_preview, _wait_for_filter_apply, _shutdown, _wait_until
    tab, parent, dlg = _open_preview(tmp_path)
    try:
        assert _wait_for_filter_apply(dlg)
        controller = dlg._curation_image_window
        panel = controller.panel
        assert _wait_until(lambda: panel.isEnabled())
        panel.kind.setCurrentIndex(1)
        table = panel.foci_table
        table.setColumnCount(4)
        table.setRowCount(1)
        item = QTableWidgetItem('34')
        item.setData(Qt.ItemDataRole.UserRole, (34, 40))
        table.setItem(0, 2, item)
        table.selectRow(0)
        assert len(dlg.canvas.object_selection_boxes) == 1
        called = []
        panel.changed = lambda: called.append(True)
        QTest.keyClick(dlg.canvas, Qt.Key.Key_Backspace)
        assert called
        assert panel.cur.peaks(0, panel.channel(), [{'y':34, 'x':40}], [])[0] == []
        size = dlg.canvas._image_size
        shape = np.asarray(controller.mask()).shape
        image_x, image_y = 40*size[0]/shape[1], 34*size[1]/shape[0]
        dlg.canvas.center_on_image_point(image_x, image_y)
        scale = dlg.canvas.view_scale()
        point = dlg.canvas._total_offset(scale) + QPointF(image_x*scale, image_y*scale)
        QTest.mouseClick(dlg.canvas, Qt.MouseButton.RightButton, pos=point.toPoint())
        assert len(called) == 2
        assert panel.cur.peaks(0, panel.channel(), [{'y':34, 'x':40}], []) == ([{'y':34, 'x':40}], [])
        assert panel.cur.peaks(0, 'unrelated', [], [{'y':34, 'x':40}]) == ([], [{'y':34, 'x':40}])
    finally:
        _shutdown(tab, parent)
