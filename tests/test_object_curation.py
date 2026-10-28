import numpy as np
import pytest
import tifffile
from bactomate.modules.object_curation import ObjectCuration


def test_keep_exclude_auto_frame_channel_and_restart(tmp_path):
    path = tmp_path/'mask.tif'
    tifffile.imwrite(path, np.zeros((16,16), np.uint16))
    cur = ObjectCuration(path)
    cur.set_objects('cells', 0, [1], False)
    cur.set_objects('cells', 0, [3], True)
    assert cur.cells(0, {1,2}, {1,2,3}) == {2,3}
    assert cur.cells(1, {1,2}, {1,2,3}) == {1,2}
    cur = ObjectCuration(path)
    assert cur.cells(0, {1,2}, {1,2,3}) == {2,3}
    cur.set_objects('cells', 0, [1,3], None)
    assert cur.cells(0, {1,2}, {1,2,3}) == {1,2}
    a, b = {'y':4,'x':5}, {'y':7,'x':8}
    cur.set_objects('foci', 0, [a], False, channel='GFP')
    cur.set_objects('foci', 0, [b], True, channel='GFP')
    assert cur.peaks(0,'GFP',[a],[b]) == ([b],[a])
    assert cur.peaks(0,'mCh',[a],[b]) == ([a],[b])
    assert cur.peaks(1,'GFP',[a],[b]) == ([a],[b])
    cur.set_objects('foci', 0, [a,b], None, channel='GFP')
    assert cur.peaks(0,'GFP',[a],[b]) == ([a],[b])


def test_history_retains_filter_values_and_segmentation_guard(tmp_path):
    path=tmp_path/'mask.tif'
    tifffile.imwrite(path,np.zeros((16,16),np.uint16))
    cur=ObjectCuration(path)
    settings={'min_area_um2':2.0}
    cur.record(0,400,400,{},action='Initial segmentation')
    cur.record(0,400,320,settings)
    settings['min_area_um2']=99
    cur.record(1,20,15,{})
    event=cur.record(0,400,325,{},action='Keep 5 cells')
    assert event['before']==320 and event['delta']==5
    restored=ObjectCuration(path)
    assert restored.data['history'][1]['settings']['min_area_um2']==2.0
    tifffile.imwrite(path,np.ones((16,16),np.uint16))
    with pytest.raises(ValueError,match='Segmentation changed'):
        ObjectCuration(path)


def test_preview_manual_edit_reaches_worker_and_survives_reset(tmp_path, qapp):
    from tests.test_filtering_preview_apply_flow import (_open_preview, _wait_for_filter_apply,
        _wait_for_apply_generation, _shutdown)
    from bactomate.gui.object_curation_panel import ObjectCurationPanel
    tab,parent,dlg=_open_preview(tmp_path)
    try:
        assert _wait_for_filter_apply(dlg)
        panel=dlg.findChild(ObjectCurationPanel)
        assert panel is not None and panel.table.rowCount()==4
        from PyQt6.QtWidgets import QPushButton
        assert dlg._pf_checkboxes['exclude_border'].isChecked()
        assert tab.get_filter_settings()['exclude_border'] is True
        assert not panel.isAncestorOf(panel.manual_controls)
        host = panel.manual_controls.parentWidget()
        layout = host.layout()
        cell_card = host.findChild(type(host), 'FilterCellGroup')
        assert cell_card is not None
        assert layout.indexOf(panel.manual_controls) == layout.indexOf(cell_card) + 1
        for title in ('Import filter settings…', 'Save filter settings…'):
            assert not any(b.text() == title for b in tab.findChildren(QPushButton))
            assert sum(b.text() == title for b in dlg.findChildren(QPushButton)) == 1
        panel.table.selectRow(0)
        rid=dlg._preview_request_id
        panel.edit(False)
        assert _wait_for_apply_generation(dlg,rid_before=rid)
        assert 1 not in dlg._last_preview['accepted']
        assert 1 in dlg._last_preview['rejected']
        assert panel.cur.data['history'][-1]['action']=='Exclude 1 cells'
        row=next(i for i in range(panel.table.rowCount()) if panel.table.item(i,0).text()=='1')
        panel.table.selectRow(row)
        rid=dlg._preview_request_id
        panel.edit(True)
        assert _wait_for_apply_generation(dlg,rid_before=rid)
        assert 1 in dlg._last_preview['accepted']
        row=next(i for i in range(panel.table.rowCount()) if panel.table.item(i,0).text()=='1')
        panel.table.selectRow(row)
        rid=dlg._preview_request_id
        panel.edit(None)
        assert _wait_for_apply_generation(dlg,rid_before=rid)
        assert '1' not in panel.cur.data['cells']['0']
    finally:
        _shutdown(tab,parent)


def test_foci_table_actions_use_the_active_channel(tmp_path, qapp):
    from PyQt6.QtWidgets import QTableWidget
    from bactomate.gui.object_curation_panel import ObjectCurationPanel
    from bactomate.gui.foci_filter_pipeline import populate_foci_preview_table
    path=tmp_path/'mask.tif'
    mask=np.zeros((32,32),np.int32)
    mask[2:28,2:28]=1
    tifffile.imwrite(path,mask)
    table=QTableWidget()
    a,b={'y':8,'x':9},{'y':10,'x':12}
    populate_foci_preview_table(table,frame_rows=[a,b],pass_peaks=[a],fail_peaks=[b],mask_2d=mask)
    changed=[]
    panel=ObjectCurationPanel(table,lambda:'GFP',lambda:changed.append(True),lambda *args:None)
    panel.context(path,0,mask,{1})
    panel.kind.setCurrentIndex(1)
    table.selectRow(0)
    panel.edit(False)
    assert changed==[True]
    assert panel.cur.peaks(0,'GFP',[a],[b]) == ([],[b,a])
    assert panel.cur.peaks(0,'mCh',[a],[b]) == ([a],[b])
    table.selectRow(1)
    panel.edit(True)
    assert panel.cur.peaks(0,'GFP',[a],[b]) == ([b],[a])
    panel.close()


def test_batch_writes_curated_cells(tmp_path, qapp, monkeypatch):
    from tests.test_filtering_preview_apply_flow import _write_mask_tif, _build_tab, _wait_until, _shutdown
    from bactomate.gui.artifact_paths import filtered_mask_path_for_mask
    path=_write_mask_tif(tmp_path)
    cur=ObjectCuration(path)
    cur.set_objects('cells',0,[1],False)
    cur.set_objects('cells',0,[3],True)
    tab,parent=_build_tab(tmp_path)
    tab.file_path.setText(str(path))
    monkeypatch.setattr(tab,'_show_finished_dialog_with_output_folder',lambda **kwargs:None)
    try:
        tab.filter_masks()
        assert _wait_until(lambda:not tab._filtering_in_progress)
        out=tifffile.imread(filtered_mask_path_for_mask(path))
        assert 1 not in np.unique(out)
        assert 3 in np.unique(out)
        assert ObjectCuration(path).data['history'][-1]['action']=='Export filtered masks'
        from bactomate.modules.filter_presets import load_filter_preset
        preset = filtered_mask_path_for_mask(path).with_suffix('.filter_settings.cells.json')
        restored = load_filter_preset(preset, tab._default_filter_settings())
        assert restored['min_aspect_ratio'] == tab.get_filter_settings()['min_aspect_ratio']
    finally:
        _shutdown(tab,parent)


def test_batch_foci_export_obeys_manual_keep_and_exclude(tmp_path, qapp, monkeypatch):
    import csv
    from tests.test_filtering_preview_apply_flow import _write_mask_tif, _build_tab, _wait_until, _shutdown
    from bactomate.gui import artifact_paths as artifacts, foci_filter_pipeline as pipeline
    from bactomate.gui.filter_preview_utils import foci_channel_key_for_path
    path=_write_mask_tif(tmp_path)
    source=tmp_path/'sample_fi_foci_GFP.tif'
    tifffile.imwrite(source,np.ones((256,256),np.uint16))
    a,b={'y':34,'x':35,'frame':0},{'y':64,'x':35,'frame':0}
    chosen=tmp_path/'detected.csv'
    chosen.write_text('y,x,frame\n34,35,0\n64,35,0\n')
    cur=ObjectCuration(path)
    key=foci_channel_key_for_path(source)
    cur.set_objects('foci',0,[a],False,channel=key)
    cur.set_objects('foci',0,[b],True,channel=key)
    monkeypatch.setattr(artifacts,'resolve_segmentation_foci_csv',lambda *args,**kwargs:chosen)
    monkeypatch.setattr(pipeline,'read_raw_foci_csv',lambda *args:[a,b])
    monkeypatch.setattr(pipeline,'process_foci_rows_for_mask',lambda *args,**kwargs:[a])
    tab,parent=_build_tab(tmp_path)
    tab.file_path.setText(str(path))
    monkeypatch.setattr(tab,'_resolve_foci_paths_for_mask',lambda *args:[source])
    monkeypatch.setattr(tab,'_show_finished_dialog_with_output_folder',lambda **kwargs:None)
    try:
        tab.filter_masks()
        assert _wait_until(lambda:not tab._filtering_in_progress)
        out=artifacts.filtered_foci_csv_path(artifacts.infer_pipeline_dir_from_mask(path),mask_path=path,foci_source_path=source)
        with out.open() as stream:
            rows=list(csv.DictReader(stream))
        assert len(rows)==1
        assert int(float(rows[0]['y']))==64
        assert int(float(rows[0]['x']))==35
    finally:
        _shutdown(tab,parent)


def test_multiple_rows_survive_refresh_but_not_frame_change(tmp_path, qapp):
    from PyQt6.QtCore import QItemSelectionModel
    from PyQt6.QtWidgets import QTableWidget
    from bactomate.gui.object_curation_panel import ObjectCurationPanel
    path=tmp_path/'mask.tif'
    mask=np.zeros((24,24),np.int32)
    mask[1:6,1:6]=1
    mask[8:13,8:13]=2
    mask[16:21,16:21]=3
    tifffile.imwrite(path,mask)
    panel=ObjectCurationPanel(QTableWidget(),lambda:'GFP',lambda:None,lambda *args:None)
    panel.context(path,0,mask,{1,2,3})
    for row in [0,2]:
        panel.table.selectionModel().select(panel.table.model().index(row,0),
            QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
    panel.context(path,0,mask,{1,3})
    assert len(panel.table.selectionModel().selectedRows())==2
    panel.context(path,1,mask,{1,2,3})
    assert not panel.table.selectionModel().selectedRows()
    panel.close()


def test_cell_table_dimensions(tmp_path, qapp):
    from PyQt6.QtWidgets import QTableWidget
    from skimage.measure import regionprops
    from bactomate.gui.object_curation_panel import ObjectCurationPanel

    mask = np.zeros((40, 50), dtype=np.uint16)
    mask[10:18, 12:36] = 1
    path = tmp_path / 'mask.tif'
    tifffile.imwrite(path, mask)
    panel = ObjectCurationPanel(QTableWidget(), lambda: 'GFP', lambda: None, lambda *args: None)
    panel.context(path, 0, mask, {1}, pixel_size=.2)
    region = regionprops(mask)[0]
    assert panel.table.columnCount() == 7
    assert panel.table.horizontalHeaderItem(3).text() == 'Length (µm)'
    assert float(panel.table.item(0, 3).text()) == pytest.approx(region.major_axis_length * .2, abs=.00005)
    assert float(panel.table.item(0, 4).text()) == pytest.approx(region.minor_axis_length * .2, abs=.00005)
    assert float(panel.table.item(0, 2).text()) == pytest.approx(192*.2**2)
    # Calibration changes must invalidate the table, even for the same labels.
    panel.context(path, 0, mask, {1}, pixel_size=.1)
    assert float(panel.table.item(0, 2).text()) == pytest.approx(192*.1**2)
    panel.context(path, 0, mask, {1})
    assert panel.table.item(0, 2).text() == '—'
    panel.close()
