import json
import os
import subprocess
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from matplotlib.figure import Figure
from bactomate.modules.figure_analysis import FigureSpec,prepare,draw,export_bundle,extract_profiles,KINDS


def test_profile_pixels_and_calibration():
    mask=np.zeros((30,50),np.uint16); mask[8:20,5:40]=7
    image=np.indices(mask.shape)[1].astype(float)
    cells,profiles=extract_profiles(mask,image,pixel_size=.2,source='XY1',bins=10,across=5)
    assert cells.area_um2.iloc[0]==pytest.approx(12*35*.2**2)
    long=profiles[profiles.profile=='longitudinal'].sort_values('position')
    assert long.intensity.is_monotonic_increasing
    assert long.pixel_count.sum()==420
    assert long.position.min()>-1 and long.position.max()<1
    assert 'track_id' not in profiles
    spec=FigureSpec(kind='Demograph',x='position',y='object_key',value='intensity',sort='length_um')
    used,plot,labels=prepare(profiles,spec)
    assert len(plot)==1 and not used.empty
    spec=FigureSpec(kind='Normalized cell heatmap',x='position',y='transverse',value='intensity')
    _,plot,_=prepare(profiles,spec)
    assert plot.shape==(5,10)


def test_kymograph_rejects_false_tracks():
    data=pd.DataFrame(dict(position=[0,1,0,1],frame=[0,0,1,1],intensity=[2,3,4,5],cell_id=[1]*4,source=['XY1']*4))
    spec=FigureSpec(kind='Kymograph',x='position',y='frame',value='intensity',group='cell_id')
    with pytest.raises(ValueError,match='verified'):prepare(data,spec)
    spec.track_confirmed=True
    _,matrix,_=prepare(data,spec)
    np.testing.assert_equal(matrix.to_numpy(),[[2,3],[4,5]])
    data.loc[3,'source']='XY2'
    with pytest.raises(ValueError,match='source'):prepare(data,spec)


@pytest.mark.parametrize('kind',KINDS)
def test_figure_export_all_kinds(kind,tmp_path):
    data=pd.DataFrame(dict(x=[0,1,2,0,1,2],y=[0,0,0,1,1,1],value=[1.,2,4,2,3,6],group=['A']*3+['B']*3))
    if kind=='Kymograph': data['group']='A'
    spec=FigureSpec(kind=kind,x='x',y='y',value='value',group='group',track_confirmed=True)
    used,plot,labels=prepare(data,spec)
    fig=Figure();draw(fig,plot,spec,labels)
    export_bundle(tmp_path,fig,used,plot,spec,labels)
    assert (tmp_path/'figure.svg').stat().st_size>100
    assert len(pd.read_excel(tmp_path/'figure_data.xlsx',sheet_name='Source rows'))==len(used)
    assert (tmp_path/'reproduce.R').exists() and (tmp_path/'reproduce.m').exists()
    result=subprocess.run([os.sys.executable,str(tmp_path/'reproduce.py')],capture_output=True,text=True,env={**os.environ,'MPLBACKEND':'Agg'})
    assert result.returncode==0,result.stderr
    assert (tmp_path/'reproduced.png').exists()


def test_ui_render_snapshot_invalidates(qapp):
    from bactomate.gui.tabs.figure_analysis import FigureAnalysisTab
    tab=FigureAnalysisTab()
    try:
        tab.set_tables({'Cells':pd.DataFrame({'area':[1,2,3],'length':[2,3,4]})},{'source':'test'})
        tab.render()
        assert tab.export.isEnabled() and tab.snapshot is not None
        tab.bins.setValue(10)
        assert not tab.export.isEnabled()
    finally:tab.close()


def test_medial_axis_follows_curved_rod():
    from scipy.ndimage import binary_dilation
    mask=np.zeros((60,80),bool)
    for x in range(15,65):mask[int(25+10*np.sin((x-15)/50*np.pi)),x]=True
    mask=binary_dilation(mask,iterations=4).astype(np.uint16)
    image=np.indices(mask.shape)[1].astype(float)
    cells,profiles=extract_profiles(mask,image,pixel_size=.1,source='curve',method='medial axis')
    long=profiles[profiles.profile=='longitudinal'].sort_values('position')
    assert long.pixel_count.sum()==mask.sum()
    assert long.intensity.iloc[-1]>long.intensity.iloc[0]
    assert cells.profile_method.iloc[0]=='medial axis'


def test_main_window_has_independent_analysis_module(qapp):
    from bactomate.gui.main_window import MainWindow
    from bactomate.gui.project_model import MODULE_ANALYSIS
    window=MainWindow()
    try:
        window._go_module_from_dashboard(MODULE_ANALYSIS)
        assert window._central_stack.currentWidget() is window._shell_analysis
        assert window.figure_analysis_tab is not window.analyze_tab
    finally:window.close()


def test_per_cell_normalization_keeps_raw_values():
    data=pd.DataFrame(dict(position=[-1,1,-1,1],intensity=[2.,4.,10.,20.],object_key=['a','a','b','b']))
    spec=FigureSpec(kind='Demograph',x='position',y='object_key',value='intensity',normalization='per-cell max')
    used,matrix,_=prepare(data,spec)
    np.testing.assert_allclose(matrix.to_numpy(),[[.5,1],[.5,1]])
    np.testing.assert_allclose(used['intensity (raw)'],[2,4,10,20])


def test_profile_shape_mismatch_is_refused():
    with pytest.raises(ValueError,match='matching TYX'):
        extract_profiles(np.ones((10,10),np.uint16),np.ones((12,10)),pixel_size=.1,source='test')
