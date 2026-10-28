import numpy as np
from PyQt6.QtWidgets import QWidget, QDoubleSpinBox, QCheckBox
from bactomate.gui.coloc_distance_preview import DistancePreview
from bactomate.modules.analysis_coloc import ColocSettings


def test_distances_update_real_pairing_and_analysis_controls(qapp):
    tab = QWidget()
    tab.coloc_merge_max_distance = QDoubleSpinBox(tab)
    tab.coloc_merge_max_distance.setValue(3)
    tab.coloc_merge_threshold = QDoubleSpinBox(tab)
    tab.coloc_merge_threshold.setValue(2)
    tab.coloc_merge_same_cell_only = QCheckBox(tab)
    tab.coloc_merge_same_cell_only.setChecked(True)
    mask = np.zeros((50, 60), np.int32)
    mask[10:35, 10:45] = 1
    channels = [('GFP', [{'x': 20, 'y': 20, 'frame': 0, 'cell_id': 1}]),
                ('mCh', [{'x': 23, 'y': 20, 'frame': 0, 'cell_id': 1}])]
    dlg = DistancePreview(tab, {0: mask}, np.zeros((1, 50, 60)), channels, 0.074)
    try:
        assert ColocSettings().coloc_max_distance == 3
        assert ColocSettings().coloc_threshold == 2
        assert len(dlg.pairs) == 1 and not dlg.pairs[0]['is_valid']
        dlg.threshold.setValue(3)
        assert dlg.pairs[0]['is_valid']
        assert tab.coloc_merge_threshold.value() == 3
        dlg.maximum.setValue(2)
        assert not dlg.pairs
        assert tab.coloc_merge_max_distance.value() == 2
        assert '1 px = 0.074' in dlg.status.text()
        dlg.canvas.draw()
    finally:
        dlg.close()
        tab.close()


def test_no_detections_does_not_invent_foci(qapp):
    tab = QWidget()
    for name in ('coloc_merge_max_distance', 'coloc_merge_threshold'):
        setattr(tab, name, QDoubleSpinBox(tab))
        getattr(tab, name).setValue(2)
    tab.coloc_merge_same_cell_only = QCheckBox(tab)
    dlg = DistancePreview(tab, {0: np.ones((20, 20), np.int32)}, np.zeros((1, 20, 20)), [])
    try:
        assert not dlg.pairs
        assert 'No detected foci' in dlg.status.text()
        dlg.canvas.draw()
    finally:
        dlg.close()
        tab.close()


def _preview_with_layers():
    tab = QWidget()
    for name in ('coloc_merge_max_distance', 'coloc_merge_threshold'):
        setattr(tab, name, QDoubleSpinBox(tab))
        getattr(tab, name).setValue(3)
    tab.coloc_merge_same_cell_only = QCheckBox(tab)
    mask = np.zeros((40, 50), np.int32)
    mask[4:12, 4:12] = 1
    mask[20:28, 30:40] = 2
    backgrounds = {'Phase': np.full((1, 40, 50), 2.),
                   'GFP': np.full((1, 40, 50), 5.),
                   'mCherry': np.full((1, 40, 50), 8.)}
    return tab, mask, backgrounds


def _drag_lut(dlg, lo, hi):
    from types import SimpleNamespace
    widget = dlg.lut_widget
    assert widget.has_histogram()
    for start, end in ((widget.current_lut()[0], lo), (widget.current_lut()[1], hi)):
        widget._on_press(SimpleNamespace(inaxes=widget._ax, xdata=start))
        widget._on_motion(SimpleNamespace(inaxes=widget._ax, xdata=end))
        widget._on_release(None)


def test_multi_channel_luts_do_not_change_pairing(qapp):
    tab, mask, backgrounds = _preview_with_layers()
    for stack in backgrounds.values():
        stack[0, 0, 1], stack[0, 0, 2] = 20, 0
    channels = [('GFP', [{'x': 6, 'y': 6, 'frame': 0, 'cell_id': 1}]),
                ('mCherry', [{'x': 8, 'y': 6, 'frame': 0, 'cell_id': 1}])]
    dlg = DistancePreview(tab, {0: mask}, backgrounds['Phase'], channels, backgrounds=backgrounds)
    try:
        pairs = list(dlg.pairs)
        for name in backgrounds:
            dlg.layer_actions[name].setChecked(name != 'Phase')
        dlg.lut_channel.setCurrentText('GFP')
        _drag_lut(dlg, 0, 10)
        gfp_lut = list(dlg.luts['GFP'])
        dlg.lut_channel.setCurrentText('mCherry')
        _drag_lut(dlg, 0, 16)
        assert dlg.luts['GFP'] == gfp_lut
        composite = dlg._composite(mask.shape)
        np.testing.assert_allclose(composite[0, 0], [.5, .5, .5])
        assert dlg.pairs == pairs
        dlg.layer_actions['GFP'].setChecked(False)
        np.testing.assert_allclose(dlg._composite(mask.shape)[0, 0], [.5, 0, .5])
        dlg.lut_channel.setCurrentText('GFP')
        assert dlg.lut_widget.current_lut() == (0, 10)
    finally:
        dlg.close()
        tab.close()


def test_cell_arrows_and_mouse_zoom(qapp):
    from types import SimpleNamespace
    from PyQt6.QtTest import QTest
    from PyQt6.QtCore import Qt
    tab, mask, backgrounds = _preview_with_layers()
    dlg = DistancePreview(tab, {0: mask}, backgrounds['Phase'], [], backgrounds=backgrounds)
    try:
        dlg.show()
        qapp.processEvents()
        assert dlg.cell.currentData() == 1
        assert not dlg.previous_cell.isEnabled()
        dlg.next_cell.click()
        assert dlg.cell.currentData() == 2
        assert not dlg.next_cell.isEnabled()
        dlg.previous_cell.click()
        assert dlg.cell.currentData() == 1
        dlg.canvas.setFocus()
        QTest.keyClick(dlg.canvas, Qt.Key.Key_Right)
        assert dlg.cell.currentData() == 2
        QTest.keyClick(dlg.canvas, Qt.Key.Key_Left)
        assert dlg.cell.currentData() == 1
        for ax in dlg.figure.axes:
            xlim, ylim = ax.get_xlim(), ax.get_ylim()
            event = SimpleNamespace(inaxes=ax, xdata=8., ydata=8., step=1)
            dlg.scroll_zoom(event)
            np.testing.assert_allclose(abs(ax.get_xlim()[1]-ax.get_xlim()[0]),
                                       abs(xlim[1]-xlim[0])/1.05)
            assert ax.get_ylim()[0] > ax.get_ylim()[1]
            event.step = -1
            dlg.scroll_zoom(event)
            np.testing.assert_allclose(ax.get_xlim(), xlim)
            np.testing.assert_allclose(ax.get_ylim(), ylim)
        ax = dlg.figure.axes[1]
        dlg.scroll_zoom(SimpleNamespace(inaxes=ax, xdata=8., ydata=8., step=1))
        limits = ax.get_xlim()
        dlg.threshold.setValue(2)
        np.testing.assert_allclose(dlg.figure.axes[1].get_xlim(), limits)
    finally:
        dlg.close()
        tab.close()


def test_xy_switch_reloads_mask_images_channels_and_calibration(qapp):
    tab, mask, backgrounds = _preview_with_layers()
    other_mask = np.zeros((25, 30), np.int32)
    other_mask[3:20, 4:15] = 7
    other_images = {'Phase': np.ones((2, 25, 30))}
    calls = []
    def load(path):
        calls.append(path)
        return {0: other_mask, 1: other_mask}, other_images['Phase'], [('RFP', [])], .2, other_images
    dlg = DistancePreview(tab, {0: mask}, backgrounds['Phase'], [('GFP', [])],
                          backgrounds=backgrounds, datasets=['XY001', 'XY002'],
                          current_path='XY001', dataset_loader=load)
    try:
        dlg.mask_selector.setCurrentIndex(1)
        assert calls == ['XY002']
        assert dlg.cell.currentData() == 7
        assert dlg.frame.maximum() == 2
        assert list(dlg.channels) == ['RFP']
        assert list(dlg.layer_actions) == ['Phase']
        assert dlg.pixel_size == .2
        assert '1 px = 0.2' in dlg.status.text()
        assert not dlg.pairs
        assert dlg._composite(other_mask.shape).shape == (25, 30, 3)
    finally:
        dlg.close()
        tab.close()


def test_left_drag_pans_without_selecting_cell(qapp):
    from matplotlib.backend_bases import MouseEvent
    from bactomate.gui.coloc_distance_preview import PreviewToolbar
    tab, mask, backgrounds = _preview_with_layers()
    dlg = DistancePreview(tab, {0: mask}, backgrounds['Phase'], [], backgrounds=backgrounds)
    try:
        assert not {'Home', 'Back', 'Forward', 'Pan', 'Zoom'} & {
            item[0] for item in PreviewToolbar.toolitems}
        dlg.canvas.draw()
        for ax in list(dlg.figure.axes):
            xlim, ylim = ax.get_xlim(), ax.get_ylim()
            # Use real canvas mouse events: hold left, move, release.
            x, y = ax.bbox.x0+ax.bbox.width/2, ax.bbox.y0+ax.bbox.height/2
            for name, px, py in [('button_press_event', x, y),
                                 ('motion_notify_event', x+20, y+10),
                                 ('button_release_event', x+20, y+10)]:
                event = MouseEvent(name, dlg.canvas, px, py, button=1)
                dlg.canvas.callbacks.process(name, event)
            assert dlg.cell.currentData() == 1
            new_x, new_y = ax.get_xlim(), ax.get_ylim()
            assert new_x != xlim and new_y != ylim
            np.testing.assert_allclose(new_x[1]-new_x[0], xlim[1]-xlim[0])
            np.testing.assert_allclose(new_y[1]-new_y[0], ylim[1]-ylim[0])
        # A simple left click still selects a cell in the overview.
        x, y = dlg.overview.transData.transform((35, 24))
        for name in ('button_press_event', 'button_release_event'):
            dlg.canvas.callbacks.process(name, MouseEvent(name, dlg.canvas, x, y, button=1))
        assert dlg.cell.currentData() == 2
    finally:
        dlg.close()
        tab.close()
