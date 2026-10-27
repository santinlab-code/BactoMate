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
