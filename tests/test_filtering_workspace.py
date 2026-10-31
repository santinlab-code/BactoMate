import csv
import numpy as np
from PyQt6.QtCore import Qt,QPointF
from PyQt6.QtTest import QTest
from bactomate.gui.filtering_display import white_cell_contours,draw_detected_foci


def test_white_hairlines_preserve_cell_interior():
    image=np.full((20,24,3),81,np.uint8)
    labels=np.zeros((20,24),np.uint16);labels[3:15,4:19]=1
    result=white_cell_contours(image,labels)
    assert tuple(result[8,8])==(81,81,81)
    assert tuple(result[3,8])==(255,255,255)
    assert tuple(result[0,0])==(81,81,81)
    np.testing.assert_equal(image,np.full_like(image,81))


def test_only_detected_foci_have_status_colors():
    image=np.zeros((30,30,3),np.uint8)
    kept={'y':10,'x':10};failed={'y':20,'x':20}
    draw_detected_foci(image,[kept,failed],[kept,{'y':2,'x':2}],(30,30))
    assert tuple(image[10,10])==(0,255,0)
    assert tuple(image[20,20])==(255,0,0)
    assert tuple(image[2,2])==(0,0,0)


def test_channel_click_selects_focus_delete_keeps_cell(tmp_path,qapp):
    import tifffile
    from tests.test_filtering_preview_apply_flow import (_write_phase_tif,_write_mask_tif,
        _build_tab,_wait_for_filter_apply,_wait_until,_wait_for_apply_generation,_shutdown)
    from bactomate.gui.tabs._analyze_masks_preview_filtering import show_filter_preview
    from bactomate.gui.preview.navigation_controls import PreviewNavState
    from bactomate.gui.artifact_paths import foci_csv_path,filtered_foci_csv_path,infer_pipeline_dir_from_mask
    _write_phase_tif(tmp_path,pixel_size_um=.108,nonzero=True)
    source=tmp_path/'sample_foci_GFP.tif'
    pixels=np.zeros((1,256,256),np.uint16);pixels[0,34,40]=1000;pixels[0,34,90]=1000
    tifffile.imwrite(source,pixels)
    mask=_write_mask_tif(tmp_path);pipeline=infer_pipeline_dir_from_mask(mask)
    rows=[dict(frame=0,y=34,x=40,probability=.9,intensity=1000),dict(frame=0,y=34,x=90,probability=.1,intensity=1000)]
    def write(path,items):
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('w') as f:
            writer=csv.DictWriter(f,fieldnames=rows[0]);writer.writeheader();writer.writerows(items)
    write(foci_csv_path(pipeline,mask_path=mask,foci_source_path=source),rows)
    write(filtered_foci_csv_path(pipeline,mask_path=mask,foci_source_path=source),rows[:1])
    tab,parent=_build_tab(tmp_path)
    tab.set_filter_settings({'foci_prob_enabled':True,'foci_prob_thresh':.5,'max_aspect_ratio':100.0})
    show_filter_preview(tab,str(mask));dlg=tab._filter_preview_dialog
    try:
        assert _wait_for_filter_apply(dlg)
        controller=dlg._curation_image_window;panel=controller.panel
        source_index=next(i for i,p in enumerate(dlg._bg_paths) if '_foci' in p.name)
        dlg._nav_ctrl.set_state(PreviewNavState(source_key=('file',source_index),frame_idx=0),emit=True)
        assert _wait_until(lambda: panel.kind.currentIndex()==1 and panel.foci_table.rowCount()==2), (panel.kind.currentIndex(),panel.foci_table.rowCount(),dlg._bg_paths,dlg.state().source_key,getattr(dlg,'_foci_rows_cache',{}))
        assert dlg._filter_tables.currentIndex()==1
        assert panel.table.height()>=10*panel.table.verticalHeader().defaultSectionSize()
        assert panel.foci_table.height()>=10*panel.foci_table.verticalHeader().defaultSectionSize()
        from PyQt6.QtWidgets import QGroupBox,QScrollArea
        assert not isinstance(dlg._filter_settings_host,QScrollArea)
        assert dlg._filter_settings_host.findChild(QGroupBox,'FilterCellGroup').isVisible()
        assert dlg._filter_settings_host.findChild(QGroupBox,'FilterFociGroup').isVisible()
        dlg.refresh();qapp.processEvents()
        assert tuple(dlg._preview_overlay_base[34,40])==(0,255,0)
        assert tuple(dlg._preview_overlay_base[34,90])==(255,0,0)
        accepted=set(dlg._last_preview['accepted'])
        canvas=dlg.canvas;shape=controller.mask().shape;size=canvas._image_size
        dx,dy=40*size[0]/shape[1],34*size[1]/shape[0]
        canvas.center_on_image_point(dx,dy);qapp.processEvents()
        scale=canvas.view_scale();point=canvas._total_offset(scale)+QPointF(dx*scale,dy*scale)
        QTest.mouseClick(canvas,Qt.MouseButton.LeftButton,pos=point.toPoint())
        chosen=panel.foci_table.selectionModel().selectedRows()
        assert len(chosen)==1
        assert panel.foci_table.item(chosen[0].row(),2).data(Qt.ItemDataRole.UserRole)==(34,40)
        rid=dlg._preview_request_id
        QTest.keyClick(canvas,Qt.Key.Key_Delete)
        assert _wait_for_apply_generation(dlg,rid_before=rid)
        assert set(dlg._last_preview['accepted'])==accepted
        assert panel.cur.data['foci'][panel.channel()]['0']['34,40'] is False
        dlg.refresh();qapp.processEvents()
        result=dlg._preview_overlay_base
        assert tuple(result[34,40])==(255,0,0)
        assert tuple(result[34,90])==(255,0,0)
        # Even after selecting a cell-table row, right click in a foci View keeps a focus.
        panel.kind.setCurrentIndex(0)
        scale=canvas.view_scale();point=canvas._total_offset(scale)+QPointF(dx*scale,dy*scale)
        rid=dlg._preview_request_id
        QTest.mouseClick(canvas,Qt.MouseButton.RightButton,pos=point.toPoint())
        assert _wait_for_apply_generation(dlg,rid_before=rid)
        assert panel.kind.currentIndex()==1
        assert set(dlg._last_preview['accepted'])==accepted
        dlg.refresh();qapp.processEvents()
        assert tuple(dlg._preview_overlay_base[34,40])==(0,255,0)
        assert tuple(dlg._preview_overlay_base[34,90])==(255,0,0)
        from PyQt6.QtWidgets import QComboBox
        history=dlg.findChild(QComboBox,'FociHistory')
        assert history.currentData()['action']==panel.history.currentData()['action']=='Keep 1 foci'
    finally:_shutdown(tab,parent)


def test_rejected_and_empty_selection_have_no_contours():
    image=np.full((30,40,3),60,np.uint8)
    labels=np.zeros((30,40),np.uint16)
    labels[3:14,3:15]=1;labels[17:27,20:36]=2
    original=labels.copy()
    result=white_cell_contours(image,labels,accepted={1},color=(20,120,230))
    assert tuple(result[3,8])==(20,120,230)
    assert tuple(result[17,25])==(60,60,60)
    assert tuple(result[8,8])==(60,60,60)
    np.testing.assert_equal(white_cell_contours(image,labels,accepted=set()),image)
    np.testing.assert_equal(labels,original)


def test_filtering_color_picker_refreshes_only_kept_cells(tmp_path,qapp,monkeypatch):
    from PyQt6.QtCore import QSettings
    from PyQt6.QtGui import QColor
    from bactomate.gui import preferences
    from bactomate.gui.preview.navigation_controls import QColorDialog
    from tests.test_filtering_preview_apply_flow import (_open_preview,_wait_for_filter_apply,
        _wait_for_apply_generation,_wait_until,_shutdown)
    monkeypatch.setattr(preferences,'_settings',lambda:QSettings(str(tmp_path/'colors.ini'),QSettings.Format.IniFormat))
    tab,parent,dlg=_open_preview(tmp_path)
    try:
        assert _wait_for_filter_apply(dlg)
        panel=dlg._curation_image_window.panel
        panel.table.selectRow(0)
        rid=dlg._preview_request_id;panel.edit(True)
        assert _wait_for_apply_generation(dlg,rid_before=rid)
        assert _wait_until(lambda:panel.isEnabled())
        accepted=set(dlg._last_preview['accepted'])
        before=dlg._preview_request_id
        seg_color=preferences.get_segmentation_outline_color()
        monkeypatch.setattr(QColorDialog,'getColor',lambda *args:QColor('#1478e6'))
        dlg._curation_image_window.outline_color.click()
        assert preferences.get_filtering_outline_color()==(20,120,230)
        assert preferences.get_segmentation_outline_color()==seg_color
        assert dlg._preview_request_id==before # No segmentation or filtering recomputed.
        assert set(dlg._last_preview['accepted'])==accepted
        image=dlg._preview_overlay_base
        assert tuple(image[30,40])==(20,120,230) # Cell 1: explicitly kept.
        assert tuple(image[60,40])!=(20,120,230) # Cell 2: rejected by filters.
        monkeypatch.setattr(QColorDialog,'getColor',lambda *args:QColor())
        dlg._curation_image_window.outline_color.click()
        assert preferences.get_filtering_outline_color()==(20,120,230)
    finally:_shutdown(tab,parent)
