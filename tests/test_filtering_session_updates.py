"""Filtering regressions: independent XY recipes, exact clicks, manual objects and LUTs."""
import numpy as np
import tifffile
from pathlib import Path
from PyQt6.QtCore import Qt,QPointF
from PyQt6.QtTest import QTest
from tests.test_filtering_preview_apply_flow import (_open_preview,_write_phase_tif,_wait_for_filter_apply,
    _wait_until,_preview_thread_idle,_shutdown,_make_mixed_mask,_build_tab,_wait_for_apply_generation)


def point(canvas,x,y):
    scale=canvas.view_scale()
    return canvas._total_offset(scale)+QPointF(x*scale,y*scale)


def test_user_luts_survive_fast_three_channel_roundtrips(tmp_path,qapp):
    from bactomate.gui.preview.navigation_controls import PreviewNavState
    _write_phase_tif(tmp_path,pixel_size_um=.108,nonzero=True)
    tifffile.imwrite(tmp_path/'sample_foci_GFP.tif',np.arange(65536,dtype=np.uint16).reshape(1,256,256))
    tifffile.imwrite(tmp_path/'sample_fi_mCherry.tif',np.full((1,256,256),100,np.uint16))
    tab,parent,dlg=_open_preview(tmp_path)
    try:
        assert _wait_for_filter_apply(dlg)
        indices={('GFP' if 'GFP' in p.name else 'mCherry' if 'mCherry' in p.name else 'phase'):i for i,p in enumerate(dlg._bg_paths)}
        ranges={'phase':(1400.,3000.),'GFP':(500.,50000.),'mCherry':(2000.,4000.)}
        def switch(name):dlg._nav_ctrl.set_state(PreviewNavState(source_key=('file',indices[name]),frame_idx=0),emit=True);qapp.processEvents()
        for name in ranges:
            switch(name);dlg.lut_widget.set_lut(*ranges[name]);dlg.lut_widget.lut_changed.emit(*ranges[name])
        for name in ['GFP','phase','mCherry','GFP','mCherry','phase']:
            switch(name);dlg.refresh()
            assert dlg.lut_widget.current_lut()==ranges[name]
            assert (dlg.state().vmin,dlg.state().vmax)==ranges[name]
        assert _wait_until(lambda:_preview_thread_idle(dlg))
    finally:_shutdown(tab,parent)


def test_mask_recipes_are_independent_inherited_and_persisted(tmp_path,qapp):
    from bactomate.gui.tabs._analyze_masks_filtering import FilteringTab
    from PyQt6.QtWidgets import QWidget
    masks=[]
    for name in ('a','b','c'):
        path=tmp_path/(name+'_masks.tif');tifffile.imwrite(path,_make_mixed_mask());masks.append(path)
    parent=QWidget();tab=FilteringTab(parent)
    tab.activate_mask_settings(masks[0]);tab.set_filter_settings({'min_area_um2':1.2})
    tab.set_foci_channel_settings('GFP',{'foci_prob_thresh':.9})
    tab.activate_mask_settings(masks[1])
    assert tab.get_filter_settings()['min_area_um2']==1.2
    tab.set_filter_settings({'min_area_um2':3.4});tab.set_foci_channel_settings('GFP',{'foci_prob_thresh':.2})
    tab.activate_mask_settings(masks[0])
    assert tab.get_filter_settings()['min_area_um2']==1.2
    assert tab.get_foci_channel_settings('GFP')['foci_prob_thresh']==.9
    tab.activate_mask_settings(masks[2]);assert tab.get_filter_settings()['min_area_um2']==1.2
    tab.activate_mask_settings(masks[1]);assert tab.get_filter_settings()['min_area_um2']==3.4
    tab.save_active_mask_settings()
    other=FilteringTab(parent);other.activate_mask_settings(masks[1])
    assert other.get_foci_channel_settings('GFP')['foci_prob_thresh']==.2
    assert other.get_filter_settings()['min_area_um2']==3.4
    assert other._default_filter_settings()['foci_exclude_outside_clear'] is True
    other.close();tab.close();parent.close()


def test_folder_picker_uses_all_sources_and_each_recipe(tmp_path,qapp,monkeypatch):
    from bactomate.gui.artifact_paths import filtered_mask_path_for_mask
    folder=tmp_path/'_segmentation';folder.mkdir()
    a,b=[folder/(name+'_masks.tif') for name in ('a','b')]
    for path in (a,b):tifffile.imwrite(path,_make_mixed_mask())
    tab,parent=_build_tab(tmp_path)
    try:
        tab.activate_mask_settings(a);tab.set_filter_settings({'min_area_um2':1.,'max_aspect_ratio':20.})
        tab.activate_mask_settings(b);tab.set_filter_settings({'min_area_um2':1000.})
        tab.file_path.setText(str(b));tab._filter_batch_root=folder
        picked=[]
        def choose(parent,files,**kw):
            picked.extend(files);assert callable(kw['result_status']);return list(files),''
        monkeypatch.setattr('bactomate.gui.tabs._analyze_masks_filtering.show_file_selection_dialog',choose)
        monkeypatch.setattr(tab,'_show_finished_dialog_with_output_folder',lambda **kw:None)
        tab.filter_masks();assert _wait_until(lambda:not tab._filtering_in_progress)
        assert set(picked)=={a,b}
        assert tifffile.imread(filtered_mask_path_for_mask(a)).max()>0
        assert tifffile.imread(filtered_mask_path_for_mask(b)).max()==0
        assert tab.get_filter_settings()['min_area_um2']==1000.
    finally:_shutdown(tab,parent)


def test_shift_click_adds_only_clicked_cells_and_context_does_not_edit(tmp_path,qapp):
    tab,parent,dlg=_open_preview(tmp_path)
    try:
        assert _wait_for_filter_apply(dlg);controller=dlg._curation_image_window;canvas=dlg.canvas;panel=controller.panel
        assert _wait_until(lambda:panel.isEnabled())
        QTest.mouseClick(canvas,Qt.MouseButton.LeftButton,pos=point(canvas,40,34).toPoint())
        QTest.mouseClick(canvas,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.ShiftModifier,pos=point(canvas,40,110).toPoint())
        labels={panel.table.item(index.row(),0).text() for index in panel.table.selectionModel().selectedRows()}
        assert labels=={'1','3'}
        before=dict(panel.cur.data['cells'])
        QTest.mouseClick(canvas,Qt.MouseButton.RightButton,pos=point(canvas,40,34).toPoint())
        assert controller.context_menu.isVisible() and panel.cur.data['cells']==before
        assert any('Create new' in action.text() for action in controller.context_menu.actions())
        controller.context_menu.close()
    finally:_shutdown(tab,parent)


def test_manual_cell_contour_and_focus_export_preserve_sources(tmp_path,qapp,monkeypatch):
    from bactomate.gui.artifact_paths import filtered_mask_path_for_mask,filtered_foci_csv_path,infer_pipeline_dir_from_mask
    _write_phase_tif(tmp_path,pixel_size_um=.108,nonzero=True)
    source=tmp_path/'sample_fi_GFP.tif';tifffile.imwrite(source,np.ones((1,256,256),np.uint16))
    tab,parent,dlg=_open_preview(tmp_path)
    monkeypatch.setattr('bactomate.gui.tabs._analyze_masks_filtering.show_file_selection_dialog',lambda parent,files,**kw:(list(files),''))
    monkeypatch.setattr(tab,'_show_finished_dialog_with_output_folder',lambda **kw:None)
    try:
        assert _wait_for_filter_apply(dlg);controller=dlg._curation_image_window;panel=controller.panel;canvas=dlg.canvas
        assert _wait_until(lambda:panel.isEnabled())
        original=panel.cur.mask_path
        # Explicit cells mode while viewing a fluorescence channel.
        panel.kind.setCurrentIndex(0)
        controller.create_at(point(canvas,180,180))
        for x,y in [(230,180),(230,190),(180,190)]:QTest.mouseClick(canvas,Qt.MouseButton.LeftButton,pos=point(canvas,x,y).toPoint())
        rid=dlg._preview_request_id
        QTest.keyClick(canvas,Qt.Key.Key_Return)
        assert _wait_for_apply_generation(dlg,rid_before=rid)
        assert 5 in dlg._last_preview['accepted']
        assert 5 not in np.unique(tifffile.imread(original))
        assert _wait_until(lambda:panel.isEnabled())
        panel.kind.setCurrentIndex(1);rid=dlg._preview_request_id
        controller.create_at(point(canvas,50,34))
        assert _wait_for_apply_generation(dlg,rid_before=rid)
        assert panel.cur.data['manual_foci']['GFP'][0]['x']==50
        assert panel.cur.data['manual_foci']['GFP'][0]['intensity']==1.
        tab.filter_masks();assert _wait_until(lambda:not tab._filtering_in_progress,timeout_s=20)
        assert 5 in np.unique(tifffile.imread(filtered_mask_path_for_mask(original)))
        csv=filtered_foci_csv_path(infer_pipeline_dir_from_mask(original),mask_path=original,foci_source_path=source)
        import pandas as pd
        rows=pd.read_csv(csv)
        assert ((rows.x==50)&(rows.y==34)).any()
        assert rows.loc[rows.x==50,'manual'].all()
    finally:_shutdown(tab,parent)


def test_saved_xy_calibration_is_not_overwritten_when_returning(tmp_path,qapp):
    _write_phase_tif(tmp_path,pixel_size_um=.108,nonzero=True)
    tab,parent,dlg=_open_preview(tmp_path)
    second=Path(tab._filter_preview_mask_path).with_name('sample_xy2_masks.tif');tifffile.imwrite(second,_make_mixed_mask())
    try:
        assert _wait_for_filter_apply(dlg)
        # Reopen once so the selector includes the new XY.
        from bactomate.gui.tabs._analyze_masks_preview_filtering import show_filter_preview
        first=Path(tab._filter_preview_mask_path)
        assert _wait_until(lambda:_preview_thread_idle(dlg))
        dlg.close();show_filter_preview(tab,str(first),mask_path=first)
        dlg=tab._filter_preview_dialog
        assert _wait_for_filter_apply(dlg);assert _wait_until(lambda:_preview_thread_idle(dlg))
        dlg._pf_spinboxes['pixel_size'].setValue(.2)
        dlg._mask_selector.setCurrentIndex(dlg._mask_selector.findData(str(second)))
        other=tab._filter_preview_dialog
        assert _wait_for_filter_apply(other);assert _wait_until(lambda:_preview_thread_idle(other))
        other._pf_spinboxes['pixel_size'].setValue(.3)
        other._mask_selector.setCurrentIndex(other._mask_selector.findData(str(first)))
        restored=tab._filter_preview_dialog
        assert _wait_for_filter_apply(restored)
        assert restored._pf_spinboxes['pixel_size'].value()==.2
    finally:_shutdown(tab,parent)


def test_shift_click_foci_and_delete_affect_only_the_clicked_peaks(tmp_path,qapp):
    from bactomate.gui.artifact_paths import foci_csv_path
    import pandas as pd
    source=tmp_path/'sample_foci_GFP.tif';tifffile.imwrite(source,np.ones((1,256,256),np.uint16))
    mask=tmp_path/'_segmentation'/'sample_masks.tif';mask.parent.mkdir()
    csv=foci_csv_path(mask.parent,mask_path=mask,foci_source_path=source)
    csv.parent.mkdir(parents=True,exist_ok=True)
    pd.DataFrame({'frame':[0]*3,'x':[40,70,100],'y':[34]*3,'intensity':[1.]*3,'probability':[1.]*3}).to_csv(csv,index=False)
    tab,parent,dlg=_open_preview(tmp_path)
    try:
        assert _wait_for_filter_apply(dlg)
        rid=dlg._preview_request_id;dlg._pf_spinboxes['max_aspect_ratio'].setValue(20);dlg._pf_apply_current()
        assert _wait_for_apply_generation(dlg,rid_before=rid)
        controller=dlg._curation_image_window;canvas=dlg.canvas;panel=controller.panel
        assert _wait_until(lambda:panel.isEnabled())
        QTest.mouseClick(canvas,Qt.MouseButton.LeftButton,pos=point(canvas,40,34).toPoint())
        QTest.mouseClick(canvas,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.ShiftModifier,pos=point(canvas,100,34).toPoint())
        selected={panel.foci_table.item(row.row(),2).data(Qt.ItemDataRole.UserRole) for row in panel.foci_table.selectionModel().selectedRows()}
        assert selected=={(34,40),(34,100)}
        rid=dlg._preview_request_id;QTest.keyClick(canvas,Qt.Key.Key_Delete)
        assert _wait_for_apply_generation(dlg,rid_before=rid)
        assert panel.cur.data['foci']['GFP']['0']=={'34,40':False,'34,100':False}
        assert any(int(row['x'])==70 for row in dlg._last_preview['pass_peaks'])
    finally:_shutdown(tab,parent)


def test_shell_file_list_keeps_sibling_masks_when_a_file_is_active(tmp_path,qapp):
    from types import SimpleNamespace
    from bactomate.gui.tabs.segmentation import SegmentationTab
    folder=tmp_path/'_segmentation';folder.mkdir()
    a,b=[folder/(name+'_masks.tif') for name in ('a','b')]
    for path in (a,b):tifffile.imwrite(path,_make_mixed_mask())
    tab,parent=_build_tab(tmp_path);tab.file_path.setText(str(b));tab._filter_batch_root=folder
    tab._filter_preview_mask_path=b;tab._filter_preview_dialog=object();seen=[]
    surface=SimpleNamespace(current_candidate_path=lambda:str(a),set_candidate_files=lambda paths,**kw:seen.append((paths,kw)))
    try:
        SegmentationTab.refresh_filtering_candidate_list(SimpleNamespace(_preview_surface=surface,filtering_tab=tab))
        assert set(seen[0][0])=={str(a),str(b)}
        assert seen[0][1]['selected']==str(b)
    finally:
        tab._filter_preview_dialog=None;_shutdown(tab,parent)
