"""Dataset changes must not retain the preceding session or require manual imports."""
from types import SimpleNamespace
import pandas as pd
import tifffile
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QPushButton, QWidget
from tests.test_filtering_preview_apply_flow import (
    _wait_until, _make_mixed_mask, _build_tab, _wait_for_filter_apply, _preview_thread_idle)


def test_finished_analysis_opens_loaded_analysis_and_clear_resets_session(tmp_path,qapp,monkeypatch):
    from bactomate.gui.main_window import MainWindow
    from bactomate.gui.tabs import _analyze_masks_analyze as module
    window=MainWindow()
    mask=tmp_path/'_segmentation'/'sample_masks.tif'
    mask.parent.mkdir();tifffile.imwrite(mask,_make_mixed_mask())
    output=tmp_path/'_analysis'/'sample_analysis.xlsx'
    output.parent.mkdir()
    completed=[]

    class FakeWorker(QObject):
        finished=pyqtSignal(bool,str)
        def __init__(self,*args,parent=None):super().__init__(parent)
        def start(self):QTimer.singleShot(0,lambda:self.finished.emit(True,'Done'))
        def isRunning(self):return False

    def finish_workbook(**kwargs):
        # The handoff must occur after the post-analysis workbook updates.
        with pd.ExcelWriter(output) as writer:
            pd.DataFrame({'cell_id':[1,2],'area_um2':[2.,3.]}).to_excel(writer,sheet_name='Per-Cell Data',index=False)
        completed.append(True)

    monkeypatch.setattr(module,'WorkerThread',FakeWorker)
    monkeypatch.setattr(window.analyze_tab,'_run_post_analysis_workbook_steps',finish_workbook)
    monkeypatch.setattr(window.analyze_tab,'_show_finished_dialog_with_output_folder',lambda **kw:None)
    try:
        # A successful worker must produce its output before its callback runs.
        output.touch()
        window.analyze_tab.file_path.setText(str(mask))
        window.analyze_tab._analysis_in_progress=True
        window.analyze_tab._run_one_analysis_task(mask,None,output)
        assert _wait_until(lambda:window._central_stack.currentWidget() is window._shell_analysis,timeout_s=15)
        analysis=window.figure_analysis_tab
        assert completed and len(analysis.tables['Cellules'])==2
        assert analysis.context_root()==tmp_path
        assert analysis.dataset.currentText()=='Cellules'
        assert _wait_until(lambda:not analysis.catalog_worker.isRunning())
        analysis.assignments={'sample':{'condition':'X','replicate':'R1'}}
        analysis.minimum.setText('99')
        window.analyze_tab._single_fi_path=mask
        window.filtering_tab.file_path.setText(str(mask))
        clear=next(b for b in window.dashboard_widget.findChildren(QPushButton) if b.text()=='Clear current session')
        notices=[]
        monkeypatch.setattr('bactomate.gui.main_window.show_message_dialog',lambda *a,**kw:notices.append(a))
        window.unet_segment_tab._embedded_unet_preview=SimpleNamespace(
            _worker_guard=SimpleNamespace(is_running=lambda:True))
        clear.click()
        assert notices and analysis.tables
        window.unet_segment_tab._embedded_unet_preview=None
        clear.click()
        assert window._central_stack.currentWidget() is window.dashboard_widget
        assert analysis.tables=={} and analysis.snapshot is None and analysis.assignments=={}
        assert analysis.catalog_root is None and analysis.context_root() is None
        assert analysis._catalog_cache=={} and not analysis.simple_export.isEnabled()
        assert not analysis.minimum.text() and analysis.metric.count()==0
        assert not window.analyze_tab.file_path.text() and not window.filtering_tab.file_path.text()
        assert window.analyze_tab._single_fi_path is None
        assert output.exists() and mask.exists()
    finally:
        if window.figure_analysis_tab.catalog_worker is not None:window.figure_analysis_tab.catalog_worker.wait()
        window.close()


def test_analysis_context_finds_results_beside_segmentation(tmp_path,qapp):
    from bactomate.gui.tabs.guided_analysis import GuidedAnalysisTab
    from PyQt6.QtWidgets import QLineEdit
    parent=QWidget();parent.analyze_tab=QWidget();parent.analyze_tab.file_path=QLineEdit()
    filtered=tmp_path/'_segmentation_cellpose'/'filtered_masks';filtered.mkdir(parents=True)
    mask=filtered/'xy1_mask_filtered.tif';mask.touch()
    output=tmp_path/'_analysis';output.mkdir()
    pd.DataFrame({'cell_id':[1],'area_um2':[2.]}).to_csv(output/'xy1_analysis.csv',index=False)
    tab=GuidedAnalysisTab(parent)
    try:
        for source in (mask,filtered,filtered.parent):
            parent.analyze_tab.file_path.setText(str(source))
            assert tab.context_root()==tmp_path
        tab.refresh_catalog()
        assert _wait_until(lambda:'Cellules' in tab.tables)
        assert len(tab.tables['Cellules'])==1
    finally:
        if tab.catalog_worker is not None:tab.catalog_worker.wait()
        tab.close();parent.close()


def test_filtering_xy_switch_changes_preview_and_filter_target(tmp_path,qapp):
    from bactomate.gui.tabs._analyze_masks_preview_filtering import show_filter_preview
    folder=tmp_path/'_segmentation';folder.mkdir()
    first=folder/'xy1_masks.tif';second=folder/'xy2_masks.tif'
    tifffile.imwrite(first,_make_mixed_mask())
    other=_make_mixed_mask()*10
    tifffile.imwrite(second,other)
    tab,parent=_build_tab(tmp_path)
    try:
        show_filter_preview(tab,str(first))
        old=tab._filter_preview_dialog
        assert _wait_for_filter_apply(old)
        assert _wait_until(lambda:_preview_thread_idle(old))
        combo=old._mask_selector
        assert combo.count()==2
        assert old._filter_settings_host.layout().itemAt(0).layout().indexOf(combo)>=0
        old._pf_spinboxes['min_area_um2'].setValue(1.25)
        combo.setCurrentIndex(combo.findData(str(second)))
        new=tab._filter_preview_dialog
        assert new is not old and new is not None
        assert tab.file_path.text()==str(second)
        assert tab._filter_preview_mask_path==second
        assert _wait_for_filter_apply(new)
        assert _wait_until(lambda:_preview_thread_idle(new))
        assert new._pf_spinboxes['min_area_um2'].value()==1.25
        assert int(new._last_preview['mask_2d'].max())==40
        assert new._mask_selector.count()==2
        assert new._curation_image_window.preview.lut_widget.isVisible()
        assert new.lut_section._header.isHidden()
    finally:
        dlg=tab._filter_preview_dialog
        if dlg is not None:
            _wait_until(lambda:_preview_thread_idle(dlg));dlg.close()
        tab.close();parent.close()


def test_batch_handoff_reads_final_merged_workbooks_across_samples(tmp_path,qapp,monkeypatch):
    from bactomate.gui.main_window import MainWindow
    window=MainWindow()
    window._workspace_root=tmp_path
    tab=window.analyze_tab
    tasks=[]
    for sample in ('a','b'):
        mask=tmp_path/sample/'_segmentation'/f'{sample}_masks.tif'
        mask.parent.mkdir(parents=True);mask.touch()
        directory=tmp_path/sample/'_analysis';directory.mkdir()
        # Task outputs can be removed when channels are merged.
        tasks.append((mask,None,directory/f'{sample}_analysis_GFP.xlsx'))

    def merge():
        for mask,_,output in tasks:
            final=output.parent/f'{mask.stem.removesuffix("_masks")}_analysis.xlsx'
            with pd.ExcelWriter(final) as writer:
                pd.DataFrame({'cell_id':[1],'area_um2':[4.]}).to_excel(writer,sheet_name='Per-Cell Data',index=False)

    monkeypatch.setattr(tab,'_merge_fi_channels_into_one_excel',merge)
    monkeypatch.setattr(tab,'_run_post_analysis_workbook_steps',lambda **kw:None)
    monkeypatch.setattr(tab,'_maybe_write_combined_summary',lambda:None)
    try:
        tab.file_path.setText(str(tmp_path))
        tab.folder_fi_tasks=tasks;tab.folder_results=[True,True]
        tab.current_task_index=2;tab._analysis_in_progress=True
        tab._process_next_folder_file()
        assert _wait_until(lambda:window._central_stack.currentWidget() is window._shell_analysis,timeout_s=15)
        assert len(window.figure_analysis_tab.tables['Cellules'])==2
        assert len(window.figure_analysis_tab.entries)==2
        assert all('GFP' not in e['path'] for e in window.figure_analysis_tab.entries)
    finally:
        if window.figure_analysis_tab.catalog_worker is not None:window.figure_analysis_tab.catalog_worker.wait()
        window.close()
