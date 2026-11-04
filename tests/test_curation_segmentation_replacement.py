"""Segmentation -> Filtering after rerunning into the same Windows folder."""
import json
import os
import time

import numpy as np
import pytest
import tifffile

from bactomate.modules.object_curation import ObjectCuration


def _mask(tmp_path):
    path = tmp_path / 'xy001_masks.tif'
    mask = np.zeros((32, 32), np.uint16)
    mask[4:12, 5:20] = 1
    tifffile.imwrite(path, mask)
    return path, mask


@pytest.mark.parametrize('legacy', [False, True])
def test_resegmentation_archives_choices_but_keeps_recipe(tmp_path, legacy):
    path, mask = _mask(tmp_path)
    cur = ObjectCuration(path)
    cur.data['filter_settings'] = {'min_area_um2': .7, 'foci_channel_settings': {'GFP': {'foci_prob_thresh': .8}}}
    cur.set_objects('cells', 0, [1], False)
    cur.add_focus(0, 'GFP', 8, 9, 100)
    cur.add_cell(0, [(20,20), (28,20), (28,28)], mask)
    cur.record(0, 2, 1, {}, action='Old choices')
    if legacy:
        saved = json.loads(cur.path.read_text())
        saved.pop('segmentation_labels_sha256')
        cur.path.write_text(json.dumps(saved))
    original = cur.path.read_bytes()
    mask[15:20, 5:20] = 1  # Same ID now describes a different segmentation.
    tifffile.imwrite(path, mask)
    mask_bytes = path.read_bytes()

    fresh = ObjectCuration(path)
    assert fresh.archived_path.parent.name == 'curation_archive'
    assert fresh.archived_path.read_bytes() == original
    assert path.read_bytes() == mask_bytes
    assert fresh.data['cells'] == fresh.data['foci'] == {}
    assert fresh.data['history'] == []
    assert not fresh.data.get('manual_cells') and not fresh.data.get('manual_foci')
    assert fresh.data['filter_settings'] == cur.data['filter_settings']
    assert fresh.cells(0, {1}, {1}) == {1}
    assert ObjectCuration(path).archived_path is None
    assert len(list(fresh.archived_path.parent.iterdir())) == 1


def test_rewritten_tiff_preserves_choices_when_labels_are_identical(tmp_path):
    path, mask = _mask(tmp_path)
    cur = ObjectCuration(path)
    cur.set_objects('cells', 0, [1], False)
    old_hash = cur.data['segmentation_sha256']
    tifffile.imwrite(path, mask[None].astype(np.int32), description='New metadata')
    restored = ObjectCuration(path)
    assert restored.data['segmentation_sha256'] != old_hash
    assert restored.cells(0, {1}, {1}) == set()
    assert restored.archived_path is None
    assert ObjectCuration(path).data == restored.data


def test_legacy_unchanged_file_is_upgraded_without_losing_choices(tmp_path):
    path, _ = _mask(tmp_path)
    cur = ObjectCuration(path)
    cur.set_objects('cells', 0, [1], False)
    saved = json.loads(cur.path.read_text())
    saved.pop('segmentation_labels_sha256')
    cur.path.write_text(json.dumps(saved))
    restored = ObjectCuration(path)
    assert restored.cells(0, {1}, {1}) == set()
    assert 'segmentation_labels_sha256' in restored.data
    restored.save()
    assert ObjectCuration(path).data == restored.data


def test_old_open_preview_cannot_overwrite_new_curation(tmp_path):
    path, mask = _mask(tmp_path)
    old = ObjectCuration(path)
    old.set_objects('cells', 0, [1], False)
    mask[20,20] = 2
    tifffile.imwrite(path, mask)
    current = ObjectCuration(path)
    current.set_objects('cells', 0, [2], False)
    before = current.path.read_bytes()
    with pytest.raises(ValueError, match='Reopen Filtering'):
        old.set_objects('cells', 0, [1], True)
    assert current.path.read_bytes() == before
    assert not list(tmp_path.glob('*.tmp'))


def test_windows_short_replace_lock_is_retried_without_scratch_left(tmp_path, monkeypatch):
    from bactomate.modules import object_curation as module
    path, _ = _mask(tmp_path)
    cur = ObjectCuration(path)
    replace = os.replace
    calls = []
    def locked_once(source, destination):
        calls.append(source)
        if len(calls) == 1:
            exc = PermissionError('File in use')
            exc.winerror = 32
            raise exc
        replace(source, destination)
    monkeypatch.setattr(module.os, 'replace', locked_once)
    monkeypatch.setattr(module.time, 'sleep', lambda _: None)
    cur.set_objects('cells', 0, [1], False)
    assert len(calls) == 2
    assert ObjectCuration(path).cells(0, {1}, {1}) == set()
    assert not list(tmp_path.glob('*.tmp'))


def test_failed_save_keeps_last_valid_json_and_cleans_scratch(tmp_path, monkeypatch):
    from bactomate.modules import object_curation as module
    path, _ = _mask(tmp_path)
    cur = ObjectCuration(path)
    cur.save()
    before = cur.path.read_bytes()
    def denied(*_):
        raise PermissionError('Access denied')
    monkeypatch.setattr(module.os, 'replace', denied)
    with pytest.raises(PermissionError):
        cur.set_objects('cells', 0, [1], False)
    assert cur.path.read_bytes() == before
    assert not list(tmp_path.glob('*.tmp'))


def test_failed_migration_keeps_active_json_and_archive(tmp_path, monkeypatch):
    from bactomate.modules import object_curation as module
    path, mask = _mask(tmp_path)
    cur = ObjectCuration(path)
    cur.set_objects('cells', 0, [1], False)
    before = cur.path.read_bytes()
    mask[20,20] = 2
    tifffile.imwrite(path, mask)
    def denied(*_):
        raise PermissionError('Access denied')
    monkeypatch.setattr(module.os, 'replace', denied)
    with pytest.raises(PermissionError):
        ObjectCuration(path)
    assert cur.path.read_bytes() == before
    archives = list((tmp_path/'curation_archive').glob('*.json'))
    assert len(archives) == 1 and archives[0].read_bytes() == before
    assert not list(tmp_path.glob('*.tmp'))


def test_only_old_owned_scratch_is_removed(tmp_path):
    path, _ = _mask(tmp_path)
    cur = ObjectCuration(path)
    old = tmp_path / (cur.path.name + '3oy4z3a9.tmp')
    old.write_text('incomplete write')
    os.utime(old, (time.time()-172800, time.time()-172800))
    other = tmp_path / 'xy002_masks.tif.curation.json3oy4z3a9.tmp'
    other.write_text('unrelated')
    recent = tmp_path / (cur.path.name + '12345678.tmp')
    recent.write_text('active write')
    custom = tmp_path / (cur.path.name + '.user-backup.tmp')
    custom.write_text('keep')
    ObjectCuration(path)
    assert not old.exists()
    assert other.exists() and recent.exists() and custom.exists()


def test_filtering_opens_resegmented_mask_without_restore_warning(tmp_path, qapp, monkeypatch):
    from tests.test_filtering_preview_apply_flow import (
        _write_mask_tif, _make_mixed_mask, _build_tab, _wait_for_filter_apply, _shutdown)
    from bactomate.gui.tabs._analyze_masks_preview_filtering import show_filter_preview
    path = _write_mask_tif(tmp_path)
    cur = ObjectCuration(path)
    cur.data['filter_settings'] = {'min_area_um2': 1.2, 'max_aspect_ratio': 20.}
    cur.set_objects('cells', 0, [1], False)
    # Reproduce the saved format from the affected Windows installation.
    saved = json.loads(cur.path.read_text())
    saved.pop('segmentation_labels_sha256')
    cur.path.write_text(json.dumps(saved))
    masks = _make_mixed_mask()
    masks[0, 38, 30:130] = 1
    tifffile.imwrite(path, masks)
    before = path.read_bytes()
    notices = []
    monkeypatch.setattr('bactomate.gui.tabs._analyze_masks_preview_filtering.show_message_dialog',
                        lambda *a, **kw: notices.append((a, kw)))
    tab, parent = _build_tab(tmp_path)
    try:
        show_filter_preview(tab, str(path), mask_path=path)
        dlg = tab._filter_preview_dialog
        assert dlg is not None and _wait_for_filter_apply(dlg)
        assert not notices
        assert 1 in dlg._last_preview['accepted']
        assert dlg._pf_spinboxes['min_area_um2'].value() == 1.2
        assert ObjectCuration(path).data['cells'] == {}
        assert path.read_bytes() == before
        assert len(list((path.parent/'curation_archive').glob('*.json'))) == 1
    finally:
        _shutdown(tab, parent)
