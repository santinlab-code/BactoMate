"""Live canvas sizing, independent figure state, exports and verified time-lapse maps."""
from dataclasses import replace
import numpy as np
import pandas as pd
from PIL import Image
from bactomate.modules.figure_analysis import FigureSpec,export_bundle
from tests.test_filtering_preview_apply_flow import _wait_until


def test_independent_windows_redraw_and_export_do_not_shrink_live_canvas(qapp,tmp_path):
    from bactomate.gui.tabs.figure_analysis import FigureAnalysisTab
    from bactomate.gui.publication_figure_window import FigureOptions
    tab=FigureAnalysisTab()
    table=pd.DataFrame({'area':[1.,2.,3.,4.,5.,6.],'Condition':['WT']*3+['Mut']*3})
    spec=FigureSpec(kind='Box plot',x='area',group='Condition')
    try:
        tab.plot_table(table,spec,{});first=tab._figure_windows[-1]
        first.resize(1100,800);qapp.processEvents();first.canvas.draw()
        assert np.allclose(first.figure.bbox.size,[first.canvas.width(),first.canvas.height()])
        tab.plot_table(table.assign(area=table.area*2),spec,{})
        second=tab._figure_windows[-1]
        assert first is not second and first.figure is not second.figure
        assert first.used.area.max()==6 and second.used.area.max()==12
        options=FigureOptions(first);options.categories.selectRow(1);options.move(-1)
        options.values['category_spacing'].setValue(2);options.values['font_size'].setValue(14)
        options.values['title'].setText('Edited first figure');options.apply();qapp.processEvents()
        assert first.spec.title=='Edited first figure' and second.spec.title==''
        assert len(first.figure.axes)==1
        assert list(first.figure.axes[0].get_xticks())==[1,3]
        original_size=first.figure.get_size_inches().copy()
        export_bundle(tmp_path,first.figure,first.used,first.plot,first.spec,first.labels,formats=("png","pdf","svg"))
        assert np.allclose(first.figure.get_size_inches(),original_size)
        assert Image.open(tmp_path/'figure.png').size==(1800,1800)
        assert np.allclose(first.figure.bbox.size,[first.canvas.width(),first.canvas.height()])
        options.close()
    finally:tab.close_figure_windows();tab.close()


def test_guided_kymograph_uses_tracked_masks_and_real_time(tmp_path,qapp,monkeypatch):
    from tests.test_figure_guide import spatial_project
    from bactomate.gui.main_window import MainWindow
    from bactomate.gui.figure_guide import FigurePlan
    from bactomate.gui.spatial_sources import project_spatial_sources
    from PyQt6.QtWidgets import QMessageBox
    import tifffile
    mask_path,raw=spatial_project(tmp_path)
    masks=np.repeat(tifffile.imread(mask_path).reshape(1,90,120),3,axis=0)
    image=np.repeat(tifffile.imread(raw).reshape(1,90,120),3,axis=0)
    tifffile.imwrite(raw,image,imagej=True,metadata={'unit':'micron','frames':3},resolution=(10,10))
    tracked=tmp_path/'_tracking'/'sample_tracking'/'sample_masks_tracked.tif';tracked.parent.mkdir(parents=True)
    masks[masks==1]=101;masks[masks==2]=102;tifffile.imwrite(tracked,masks)
    window=MainWindow();window._workspace_root=tmp_path;tab=window.figure_analysis_tab
    errors=[];monkeypatch.setattr(QMessageBox,'warning',lambda *args:errors.append(args))
    try:
        pairs=project_spatial_sources(tab);assert str(tracked) in pairs[0]['tracked_masks']
        plan=FigurePlan(goal='kymograph',kind='Kymograph',dataset='',channel='GFP',track_id=101,
            tracked_mask=str(tracked),track_confirmed=True,time_interval=2.)
        tab.apply_figure_plan(plan,pairs)
        assert _wait_until(lambda:tab.snapshot is not None,timeout_s=15),errors
        used,matrix,spec,*_=tab.snapshot
        assert used.track_id.nunique()==1 and used.track_id.iloc[0]==101
        assert list(matrix.index)==[0.,2.,4.]
        assert 'Time (min)'==tab.figure.axes[0].get_ylabel()
        assert [tick.get_text() for tick in tab.figure.axes[0].get_xticklabels()]==['0','0.5','1']
        assert used.frame.nunique()==3
    finally:
        if tab.worker is not None:tab.worker.wait()
        window.close()


def test_edit_guide_restores_an_advanced_box_plot_in_its_own_window(qapp):
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QApplication,QWidget
    from bactomate.gui.tabs.guided_analysis import GuidedAnalysisTab
    parent=QWidget();tab=GuidedAnalysisTab(parent)
    source=pd.DataFrame({'area':[1.,2.,3.,4.],'Condition':['WT','WT','Mut','Mut']})
    tab.set_tables({'Cells':source},{})
    tab.advanced.setChecked(True);tab.kind.setCurrentText('Box plot');tab.fields['x'].setCurrentText('area');tab.fields['group'].setCurrentText('Condition')
    tab.render();window=tab._figure_windows[-1];seen=[]
    def inspect():
        guide=QApplication.activeModalWidget()
        seen.append((guide.goal.currentData(),guide.metric.currentText(),guide.parentWidget() is window))
        guide.next();guide.next();seen.append(guide.style.currentText());guide.reject()
    QTimer.singleShot(0,inspect)
    window.edit_guide()
    assert seen==[('distribution','area',True),'Box plot']
    tab.close_figure_windows();tab.close();parent.close()
