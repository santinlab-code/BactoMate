"""Cell outlines retain image detail and can be recolored without changing masks."""
import numpy as np
import pytest
import tifffile

from bactomate.modules.segmentation_display import label_outlines, segmentation_outline_rgb


def test_outlines_include_touching_labels_and_image_edges():
    mask = np.zeros((12, 16), np.int64)
    mask[0:10, 0:8] = 1
    mask[2:10, 8:15] = 1_000_000_000
    before = mask.copy()
    edge = label_outlines(mask)
    assert edge[0, 4] and edge[4, 0]  # image border
    assert edge[4, 7] and edge[4, 8]  # touching cells stay distinct
    assert not edge[4, 4] and not edge[4, 11]  # interiors
    assert not np.any(edge[mask == 0])
    np.testing.assert_array_equal(mask, before)


def test_color_changes_only_boundaries_preserving_lut_and_masks():
    image = np.arange(20*20, dtype=np.uint16).reshape(20,20) % 200 + 20
    image = image.astype(np.uint8)
    mask = np.zeros_like(image)
    mask[3:17,3:17] = 1
    before = mask.copy()
    edge = label_outlines(mask)
    for color in [(0,255,0), (255,0,255), (0,0,0), (255,255,255)]:
        result = segmentation_outline_rgb(image, mask, color)
        assert np.all(result[edge] == color)
        np.testing.assert_array_equal(result[~edge], np.repeat(image[...,None],3,axis=2)[~edge])
        np.testing.assert_array_equal(mask, before)
    np.testing.assert_array_equal(segmentation_outline_rgb(image, mask*0), np.repeat(image[...,None],3,axis=2))


def test_display_helper_delegates_outlines_without_tinting():
    from bactomate.gui.image_utils import build_segmentation_overlay
    image = np.full((12,12), 128, np.uint8)
    mask = np.zeros_like(image)
    mask[2:10,2:10] = 1
    result = build_segmentation_overlay(image, mask, outline_color=(255,0,255))
    assert tuple(result[5,5]) == (128,128,128)
    assert tuple(result[2,5]) == (255,0,255)


@pytest.fixture
def isolated_preferences(monkeypatch, tmp_path):
    from PyQt6.QtCore import QSettings
    from bactomate.gui import preferences
    monkeypatch.setattr(preferences, '_settings', lambda: QSettings(str(tmp_path/'prefs.ini'), QSettings.Format.IniFormat))
    return preferences


def test_color_picker_persists_emits_and_cancel_does_nothing(qapp, monkeypatch, isolated_preferences):
    from PyQt6.QtGui import QColor
    from bactomate.gui.preview.navigation_controls import PreviewNavigationControls, PreviewNavSpec, QColorDialog
    spec = PreviewNavSpec(frame_count=3, show_cell_overlay_toggle=True, show_cell_outline_color=True)
    nav = PreviewNavigationControls(spec=spec)
    changes = []
    nav.outline_color_changed.connect(lambda: changes.append(True))
    monkeypatch.setattr(QColorDialog, 'getColor', lambda *args: QColor('#ff00ff'))
    nav._outline_color_btn.click()
    assert isolated_preferences.get_segmentation_outline_color() == (255,0,255)
    assert changes == [True]
    assert nav._show_cells_cb.text() == 'Show cell outlines'
    assert '#ff00ff' in nav._outline_color_btn.styleSheet()
    monkeypatch.setattr(QColorDialog, 'getColor', lambda *args: QColor())
    nav._outline_color_btn.click()
    assert changes == [True]
    again = PreviewNavigationControls(spec=spec)
    assert '#ff00ff' in again._outline_color_btn.styleSheet()
    nav.close()
    again.close()


def test_short_timelapse_export_keeps_every_frame_and_color(tmp_path, isolated_preferences):
    from bactomate.scripts.batch_process_tiff_sequence import overlay_masks_on_images
    isolated_preferences.set_segmentation_outline_color('#00ffff')
    images = np.stack([np.full((20,24), 80, np.uint8), np.full((20,24), 140, np.uint8)])
    masks = np.zeros_like(images)
    masks[0,2:10,2:10] = 1
    masks[1,8:18,10:20] = 2
    out = tmp_path/'overlay.tif'
    overlay_masks_on_images(images, masks, out)
    result = tifffile.imread(out)
    assert result.shape == (2,20,24,3)
    for i in range(2):
        np.testing.assert_array_equal(result[i],segmentation_outline_rgb(images[i],masks[i],(0,255,255)))
