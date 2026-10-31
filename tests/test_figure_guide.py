"""Exercise the guide with real project artifacts and publication exports."""
import json
import os
import subprocess
import numpy as np
import pandas as pd
import pytest
import tifffile
from PIL import Image
from PyQt6.QtWidgets import QWizard,QFileDialog,QMessageBox
from tests.test_filtering_preview_apply_flow import _wait_until
from bactomate.modules.figure_analysis import extract_profiles,FigureSpec,prepare,draw,export_bundle
from matplotlib.figure import Figure


def spatial_project(root):
    from bactomate.gui.artifact_paths import filtered_foci_csv_path
    from bactomate.modules.analysis_catalog import save_assignments
    directory=root/'_segmentation';filtered=directory/'filtered_masks';filtered.mkdir(parents=True)
    mask=np.zeros((1,90,120),np.uint16)
    for i,y in enumerate((10,35,60),1):mask[0,y:y+9,10:100]=i
    tifffile.imwrite(directory/'sample_masks.tif',mask)
    # Saved Filtering excludes cell 3.
    kept=mask.copy();kept[kept==3]=0
    mask_path=filtered/'sample_mask_filtered.tif';tifffile.imwrite(mask_path,kept)
    yy,xx=np.indices(mask.shape[1:]);image=(100+3000*np.exp(-((xx-20)**2/25))).astype(np.uint16)[None]
    raw=root/'sample_fi_foci_GFP.tif'
    tifffile.imwrite(raw,image,imagej=True,metadata={'unit':'micron','frames':1},resolution=(10,10))
    csv=filtered_foci_csv_path(directory,mask_path=mask_path,foci_source_path=raw)
    csv.parent.mkdir(parents=True,exist_ok=True)
    pd.DataFrame({'frame':[0,0,0],'x':[20,22,20],'y':[14,39,64]}).to_csv(csv,index=False)
    output=root/'_analysis';output.mkdir()
    book=output/'sample_analysis.xlsx'
    with pd.ExcelWriter(book) as writer:
        pd.DataFrame({'cell_id':[1,2],'area_um2':[8.,9.],'num foci [GFP]':[0,1]}).to_excel(writer,sheet_name='Per-Cell Data',index=False)
    save_assignments(root,{'_analysis/sample_analysis.xlsx':{'condition':'X','replicate':'R1'}})
    return mask_path,raw


@pytest.fixture
def project_window(tmp_path,qapp,monkeypatch):
    from bactomate.gui.main_window import MainWindow
    monkeypatch.setattr(QMessageBox,'information',lambda *a,**kw:None)
    monkeypatch.setattr(QMessageBox,'warning',lambda *a,**kw:None)
    spatial_project(tmp_path)
    window=MainWindow();window._workspace_root=tmp_path
    tab=window.figure_analysis_tab;tab.refresh_catalog()
    assert _wait_until(lambda:'Cells' in tab.tables)
    monkeypatch.setattr(QFileDialog,'getOpenFileName',lambda *a,**kw:pytest.fail('Guide must not request file imports'))
    yield window
    if tab.worker is not None:tab.worker.wait()
    if tab.catalog_worker is not None:tab.catalog_worker.wait()
    window.close()


def test_guide_demograph_from_project_images(project_window,qapp,tmp_path):
    from bactomate.gui.figure_guide import FigureGuide
    tab=project_window.figure_analysis_tab
    guide=FigureGuide(tab)
    guide.goal.setCurrentIndex(guide.goal.findData('demograph'));guide.show();qapp.processEvents()
    guide.next()
    assert guide.currentId()==1 and len(guide.sources)==1
    assert guide.sources[0]['filtered']
    guide.condition.setCurrentIndex(guide.condition.findData('X'))
    guide.next();assert guide.currentId()==2
    guide.orientation.setCurrentIndex(guide.orientation.findData('bright pole'))
    guide.next();assert guide.currentId()==3
    assert 'XYs: 1' in guide.review.text()
    guide.button(QWizard.WizardButton.FinishButton).click()
    assert _wait_until(lambda:tab.snapshot is not None,timeout_s=15)
    used,plot,spec,labels,provenance=tab.snapshot
    assert spec.kind=='Demograph' and spec.normalization=='per-cell max'
    assert used.cell_id.nunique()==2 and set(used.profile)=={'longitudinal'}
    assert plot.shape[0]==2 and plot.columns.min()>0 and plot.columns.max()<1
    assert np.nanmax(plot.to_numpy())==pytest.approx(1)
    assert [t.get_text() for t in tab.figure.axes[0].get_xticklabels()]==['0','0.5','1']
    assert provenance['sources'][0]['orientation']=='bright pole'
    assert not tab.advanced.isChecked()
    export_bundle(tmp_path/'figure_demo',tab.figure,used,plot,spec,labels,provenance=provenance)
    assert Image.open(tmp_path/'figure_demo'/'figure.png').size==(1800,1800)
    assert 'Relative cell length' in (tmp_path/'figure_demo'/'axes.json').read_text()
    guide.close()


def test_guide_kept_foci_positions_and_square_reproduction(project_window,tmp_path):
    from bactomate.gui.figure_guide import FigurePlan
    from bactomate.gui.spatial_sources import project_spatial_sources
    tab=project_window.figure_analysis_tab
    plan=FigurePlan(goal='maxima',kind='Maxima map',dataset='',channel='GFP',frame='first',maxima_profile='focus',pixel_size=.1)
    tab.apply_figure_plan(plan,project_spatial_sources(tab))
    assert _wait_until(lambda:tab.snapshot is not None,timeout_s=15)
    used,plot,spec,labels,provenance=tab.snapshot
    assert len(plot)==2 and set(used.cell_id)=={1,2}
    assert set(used.profile)=={'focus'}
    assert set(used.x_px)=={20,22}
    assert used.relative_position.between(0,1).all()
    assert used.relative_width.between(-.5,.5).all()
    folder=tmp_path/'figure_maxima';export_bundle(folder,tab.figure,used,plot,spec,labels,provenance=provenance)
    result=subprocess.run([os.sys.executable,str(folder/'reproduce.py')],capture_output=True,text=True,env={**os.environ,'MPLBACKEND':'Agg'})
    assert result.returncode==0,result.stderr
    assert Image.open(folder/'figure.png').size==Image.open(folder/'reproduced.png').size==(1800,1800)
    meta=json.loads((folder/'axes.json').read_text())
    assert meta['ylim']==[1.05,-.05] and meta['box_aspect']==2
    assert meta['color_scale']['lo']==0 and meta['color_scale']['hi']==1
    assert len(pd.read_csv(folder/'plot_data.csv'))==2


def test_guide_counts_include_zero_and_group_button_stays_at_top(project_window,qapp):
    from bactomate.gui.figure_guide import FigurePlan
    from bactomate.gui.project_model import MODULE_ANALYSIS
    window=project_window;tab=window.figure_analysis_tab
    window.show();window._go_module_from_dashboard(MODULE_ANALYSIS);qapp.processEvents()
    for advanced in (False,True,False):
        tab.advanced.setChecked(advanced);qapp.processEvents()
        assert tab.groups_button.isVisible()
        assert not tab.control_stack.isAncestorOf(tab.groups_button)
    plan=FigurePlan(goal='counts',kind='Foci count',dataset='Cells',metric='num foci [GFP]')
    tab.minimum.setText('99')
    tab.apply_figure_plan(plan,[])
    assert not tab.minimum.text()
    _,plot,spec,*_=tab.snapshot
    assert list(plot.x)==[0,1] and list(plot.y)==[50,50]
    from bactomate.gui.figure_guide import FigureGuide
    plan.title='GFP foci counts'
    tab.apply_figure_plan(plan,[])
    guide=FigureGuide(tab);guide.show();qapp.processEvents()
    assert guide.goal.currentData()=='counts'
    guide.next();assert guide.metric.currentText()=='num foci [GFP]'
    guide.next();assert guide.style.currentText()=='Foci count'
    assert guide.title.text()=='GFP foci counts'
    guide.close()
    tab.square_canvas.resize(760,500);qapp.processEvents()
    assert tab.canvas.width()==tab.canvas.height()


def test_brightest_pixel_and_detected_foci_remain_distinct():
    mask=np.zeros((15,30),np.uint16);mask[4:11,3:27]=1
    image=np.zeros_like(mask,float);image[7,5]=100
    _,profiles=extract_profiles(mask,image,pixel_size=.1,source='XY',foci=pd.DataFrame({'frame':[0],'x':[20],'y':[7]}))
    maxima=profiles[profiles.profile=='maximum'];foci=profiles[profiles.profile=='focus']
    assert maxima.x_px.tolist()==[5] and foci.x_px.tolist()==[20]
    assert maxima.relative_position.iloc[0]<foci.relative_position.iloc[0]
    _,flipped=extract_profiles(mask,image,pixel_size=.1,source='XY',orientation='bright pole')
    assert flipped.loc[flipped.profile=='maximum','relative_position'].iloc[0]<.5


def test_guide_does_not_invent_kept_foci_or_replicates(project_window):
    from bactomate.gui.figure_guide import FigurePlan
    from bactomate.gui.spatial_sources import project_spatial_sources
    tab=project_window.figure_analysis_tab
    pairs=project_spatial_sources(tab);pairs[0]['foci_csv']=None
    with pytest.raises(ValueError,match='Saved filtered foci'):
        tab.apply_figure_plan(FigurePlan(goal='maxima',kind='Maxima map',dataset='',maxima_profile='focus'),pairs)
    tab.tables['Cells'].loc[:,'Replicate']=''
    with pytest.raises(ValueError,match='Conditions & replicates'):
        tab.apply_figure_plan(FigurePlan(goal='distribution',kind='Violin plot',dataset='Cells',metric='area_um2'),[])


def test_project_change_during_profile_calculation_does_not_mix_data(project_window,tmp_path,monkeypatch):
    import threading
    from bactomate.gui.figure_guide import FigurePlan
    from bactomate.gui import spatial_sources
    tab=project_window.figure_analysis_tab
    started=threading.Event();release=threading.Event()
    original=spatial_sources.extract_profiles
    def slow_profiles(*args,**kwargs):
        started.set()
        if not release.wait(10):raise RuntimeError('Test did not release worker')
        return original(*args,**kwargs)
    monkeypatch.setattr(spatial_sources,'extract_profiles',slow_profiles)
    tab.apply_figure_plan(FigurePlan(goal='demograph',kind='Demograph',dataset='',pixel_size=.1),spatial_sources.project_spatial_sources(tab))
    assert _wait_until(started.is_set)
    other=tmp_path/'other-project';other.mkdir()
    project_window._workspace_root=other;tab.refresh_catalog()
    release.set()
    assert _wait_until(lambda:not tab.worker.isRunning())
    assert tab.snapshot is None and 'Spatial profiles' not in tab.tables


def test_english_catalog_keeps_legacy_french_replicate_metadata(tmp_path):
    from bactomate.modules.analysis_catalog import read_catalog,assemble_catalog,save_assignments
    output=tmp_path/'_analysis';output.mkdir()
    pd.DataFrame({'cell_id':[1,2],'area_um2':[1.,2.], 'condition':['X','X'],'Réplicat':['R1','R1']}).to_csv(output/'sample_analysis.csv',index=False)
    entries,errors=read_catalog(tmp_path)
    save_assignments(tmp_path,{entries[0]['id']:{'condition':'Y','replicate':'R2'}})
    table=assemble_catalog(entries,{})['Cells']
    assert not errors and table['Replicate'].tolist()==['R1','R1']
    assert table['Source file'].nunique()==1
