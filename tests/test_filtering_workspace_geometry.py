"""Bounded, styled previews must not squeeze fields or overlap table/history rows."""
import numpy as np
import pytest
import tifffile
from PyQt6.QtCore import QPoint
from PyQt6.QtWidgets import (QDoubleSpinBox, QGroupBox, QLayout, QPushButton,
                             QVBoxLayout, QWidget)

from tests.test_filtering_preview_apply_flow import (
    _build_tab, _write_mask_tif, _write_phase_tif, _wait_for_filter_apply,
    _wait_until, _preview_thread_idle, _shutdown)


def _settle(qapp):
    for _ in range(15):
        qapp.processEvents()


def _table_is_not_overlapped(table, history, details):
    parent = table.parentWidget()
    assert table.y() + table.height() <= history.mapTo(parent, QPoint()).y()
    assert history.mapTo(parent, QPoint()).y() + history.height() <= details.mapTo(parent, QPoint()).y()
    assert table.height() >= (table.horizontalHeader().height()
                              + 10 * table.verticalHeader().defaultSectionSize())


@pytest.mark.parametrize('width,height,large_font', [(820, 760, False), (1040, 850, True)])
def test_bounded_filtering_tables_fields_and_detach_roundtrips(tmp_path, qapp, width, height, large_font):
    from bactomate.gui.styles import get_modern_stylesheet
    from bactomate.gui.tabs._analyze_masks_preview_filtering import show_filter_preview
    old_style = qapp.styleSheet()
    style = get_modern_stylesheet()
    qapp.setStyleSheet(style.replace('11pt', '14pt') if large_font else style)
    path = _write_mask_tif(tmp_path)
    _write_phase_tif(tmp_path, pixel_size_um=.1, nonzero=True)
    tifffile.imwrite(tmp_path/'sample_foci_GFP.tif', np.ones((1,256,256), np.uint16))
    tab, parent = _build_tab(tmp_path)
    mount = QWidget()
    mount.setFixedSize(width, height)
    layout = QVBoxLayout(mount)
    layout.setContentsMargins(0,0,0,0)
    layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
    mount.show()
    tab.attach_module_preview_mount(mount)
    try:
        show_filter_preview(tab, str(path))
        dlg = tab._filter_preview_dialog
        assert _wait_for_filter_apply(dlg)
        assert _wait_until(lambda: _preview_thread_idle(dlg))
        controller = dlg._curation_image_window
        panel = controller.panel
        tabs = dlg._filter_tables
        for detached in (True, False, True, False):
            controller.detach() if detached else controller.attach()
            _settle(qapp)
            assert controller.home.isVisible() is (not detached)
            assert panel.manual_controls.isVisible()
            for button in panel.manual_controls.findChildren(QPushButton):
                assert button.isVisible() and button.height() >= button.minimumSizeHint().height()
                assert button.width() >= button.sizeHint().width()
                assert button.x() >= 0 and button.x() + button.width() <= panel.manual_controls.width()
            for index in (0,1,2,3,0):
                tabs.setCurrentIndex(index)
                _settle(qapp)
                area = tabs.widget(index)
                content = area.widget().content
                assert content.isVisible()
                assert content.height() >= content.minimumSizeHint().height()
                if index == 0:
                    _table_is_not_overlapped(panel.table, panel.history, panel.details)
                    # All ten rows are accessible without scrolling the entire page.
                    assert panel.table.mapTo(area.viewport(), QPoint()).y() + panel.table.height() <= area.viewport().height()
                elif index == 1:
                    from PyQt6.QtWidgets import QComboBox, QTextEdit
                    _table_is_not_overlapped(panel.foci_table,
                        content.findChild(QComboBox, 'FociHistory'), content.findChild(QTextEdit))
                else:
                    card = content
                    assert isinstance(card, QGroupBox)
                    for spin in card.findChildren(QDoubleSpinBox):
                        assert spin.isVisible()
                        assert spin.height() >= spin.minimumSizeHint().height()
                        point = spin.mapTo(card, QPoint())
                        assert point.y() >= 0 and point.y() + spin.height() <= card.height()
                    # The page's overflow allows reaching the final setting if needed.
                    area.verticalScrollBar().setValue(area.verticalScrollBar().maximum())
                    _settle(qapp)
            assert controller.window.isVisible() is detached
        tabs.setCurrentIndex(2)
        _settle(qapp)
        assert _wait_until(lambda: panel.isEnabled() and _preview_thread_idle(dlg))
        panel.kind.setCurrentIndex(0)
        shape = controller.mask().shape
        size = dlg.canvas._image_size
        dlg.canvas.clicked_image.emit(round(40 * size[0] / shape[1]), round(34 * size[1] / shape[0]))
        assert tabs.currentIndex() == 0
        assert panel.table.selectionModel().selectedRows()
    finally:
        _shutdown(tab, parent)
        mount.close()
        qapp.setStyleSheet(old_style)


def test_wrapping_controls_keep_widgets_visible_when_reparented(qapp):
    from bactomate.gui.filtering_workspace import WrappingControls
    host = QWidget()
    layout = QVBoxLayout(host)
    controls = WrappingControls(*(QPushButton(text) for text in
                                  ('Keep selected objects', 'Exclude selected objects', 'Use filters')))
    layout.addWidget(controls)
    host.show()
    try:
        for width in (800, 260, 700, 280):
            host.resize(width, 300)
            _settle(qapp)
            buttons = controls.findChildren(QPushButton)
            assert len(buttons) == 3 and all(button.isVisible() for button in buttons)
            rects = [button.geometry() for button in buttons]
            assert all(not a.intersects(b) for i,a in enumerate(rects) for b in rects[i+1:])
            assert controls.height() >= controls.layout().minimumSize().height()
    finally:
        host.close()
