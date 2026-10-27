import json
import pytest

from bactomate.modules.filter_presets import save_filter_preset, load_filter_preset
from bactomate.gui.tabs._analyze_masks_filtering import FilteringTab


def test_roundtrip_all_cells_and_distinct_channels(tmp_path):
    defaults = FilteringTab._default_filter_settings(None)
    settings = dict(defaults, min_area_um2=0.15, focus_modality='brightfield',
                    foci_channels={'gfp': {'foci_prob_enabled': True, 'foci_prob_thresh': 0.8},
                                   'mch': {'foci_min_int_enabled': True, 'foci_min_int': 120.0}})
    path = tmp_path/'settings.json'
    save_filter_preset(path, settings)
    restored = load_filter_preset(path, defaults)
    assert restored['min_area_um2'] == 0.15
    assert restored['focus_modality'] == 'brightfield'
    assert restored['foci_channels']['gfp']['foci_prob_thresh'] == 0.8
    assert restored['foci_channels']['mch']['foci_min_int'] == 120


@pytest.mark.parametrize('change', [
    {'version': 99}, {'format': 'other'}, {'filter_settings': []},
    {'filter_settings': {'min_area_um2': 'wrong'}},
    {'filter_settings': {'exclude_border': 'false'}},
    {'filter_settings': {'foci_channels': {'gfp': {'foci_prob_thresh': float('nan')}}}},
])
def test_reject_invalid_presets(tmp_path, change):
    path = tmp_path/'settings.json'
    payload = {'format': 'bactomate-filter-settings', 'version': 1, 'filter_settings': {}}
    payload.update(change)
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError):
        load_filter_preset(path, FilteringTab._default_filter_settings(None))


def test_import_updates_open_preview_and_preserves_state_on_invalid_file(tmp_path, qapp):
    from tests.test_filtering_preview_apply_flow import (
        _open_preview, _wait_for_filter_apply, _wait_for_apply_generation, _shutdown, _wait_until,
        _preview_thread_idle)
    tab, parent, dlg = _open_preview(tmp_path)
    try:
        assert _wait_for_filter_apply(dlg)
        assert _wait_until(lambda: _preview_thread_idle(dlg) and not dlg.state().extra.get('filter_apply_busy'))
        path = tmp_path/'settings.json'
        settings = dict(tab.get_filter_settings(), min_area_um2=0.15, min_eccentricity=0.0,
                        foci_channels={'gfp': {'foci_prob_enabled': True, 'foci_prob_thresh': 0.87}})
        save_filter_preset(path, settings)
        rid = dlg._preview_request_id
        tab.load_filter_preset(path)
        assert _wait_for_apply_generation(dlg, rid_before=rid)
        assert dlg._pf_spinboxes['min_area_um2'].value() == pytest.approx(0.15)
        assert dlg._pf_spinboxes['min_eccentricity'].value() == 0.0
        assert tab.get_foci_channel_settings('gfp')['foci_prob_thresh'] == 0.87
        before = tab.get_filter_settings()
        path.write_text('{}')
        with pytest.raises(ValueError):
            tab.load_filter_preset(path)
        assert tab.get_filter_settings() == before
    finally:
        _shutdown(tab, parent)


def test_separate_files_import_only_their_scope(tmp_path, qapp):
    from bactomate.modules.filter_presets import save_separate_filter_presets
    from tests.test_filtering_preview_apply_flow import _build_tab, _shutdown
    defaults = FilteringTab._default_filter_settings(None)
    settings = dict(defaults, min_area_um2=0.3,
                    foci_channels={'GFP': {'foci_prob_thresh': 0.8},
                                   'mCh': {'foci_prob_thresh': 0.2}})
    files = save_separate_filter_presets(tmp_path/'filters.json', settings)
    assert len(files) == 3
    tab, parent = _build_tab(tmp_path)
    try:
        tab.set_filter_settings({'min_area_um2': 0.9})
        tab.set_foci_channel_settings('mCh', {'foci_prob_thresh': 0.4})
        tab.load_filter_preset(files[1])
        assert tab.get_filter_settings()['min_area_um2'] == 0.9
        assert tab.get_foci_channel_settings('GFP')['foci_prob_thresh'] == 0.8
        assert tab.get_foci_channel_settings('mCh')['foci_prob_thresh'] == 0.4
        tab.load_filter_preset(files[0])
        assert tab.get_filter_settings()['min_area_um2'] == 0.3
        assert tab.get_foci_channel_settings('GFP')['foci_prob_thresh'] == 0.8
        tab.load_filter_preset(files[2])
        assert tab.get_foci_channel_settings('mCh')['foci_prob_thresh'] == 0.2
    finally:
        _shutdown(tab, parent)


def test_switch_channels_preserves_unsaved_widget_edits(tmp_path, qapp):
    import numpy as np
    import tifffile
    from tests.test_filtering_preview_apply_flow import (
        _open_preview, _wait_for_filter_apply, _wait_until, _shutdown)
    for channel in ('GFP', 'mCh'):
        tifffile.imwrite(tmp_path/f'sample_foci_{channel}.tif', np.zeros((256, 256), np.uint16))
    tab, parent, dlg = _open_preview(tmp_path)
    try:
        assert _wait_for_filter_apply(dlg)
        combo = dlg._nav_ctrl._image_combo
        def switch(channel):
            i = next(i for i in range(combo.count()) if channel.lower() in combo.itemText(i).lower())
            combo.setCurrentIndex(i)
            assert _wait_until(lambda: dlg._pf_widget_channel.lower() == channel.lower())
        switch('GFP')
        dlg._pf_spinboxes['foci_prob_thresh'].setValue(0.82)
        dlg._pf_checkboxes['foci_prob_enabled'].setChecked(True)
        switch('mCh')
        assert dlg._pf_spinboxes['foci_prob_thresh'].value() == 0.5
        assert not dlg._pf_checkboxes['foci_prob_enabled'].isChecked()
        dlg._pf_spinboxes['foci_prob_thresh'].setValue(0.23)
        switch('GFP')
        assert dlg._pf_spinboxes['foci_prob_thresh'].value() == 0.82
        assert dlg._pf_checkboxes['foci_prob_enabled'].isChecked()
        switch('mCh')
        assert dlg._pf_spinboxes['foci_prob_thresh'].value() == 0.23
        tab.sync_filter_settings_from_preview_ui()
        fs = tab.get_filter_settings()
        assert fs['foci_channels']['GFP']['foci_prob_thresh'] == 0.82
        assert fs['foci_channels']['mCh']['foci_prob_thresh'] == 0.23
    finally:
        _shutdown(tab, parent)
