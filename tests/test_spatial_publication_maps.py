"""Length-envelope demographs and shape-aware normalized fluorescence/foci maps."""
import json
import os
import subprocess
import numpy as np
import pandas as pd
import pytest
from matplotlib.figure import Figure
from skimage.draw import disk

from bactomate.modules.figure_analysis import FigureSpec,extract_profiles,prepare,draw,export_bundle
from bactomate.modules.cell_coordinates import capsule_radius
from tests.test_figure_guide import project_window
from tests.test_filtering_preview_apply_flow import _wait_until


def curved_cell():
    mask=np.zeros((160,180),np.uint16)
    angle=np.linspace(.1,2.4,250)
    centers=np.c_[70+38*np.sin(angle),80+38*np.cos(angle)]
    for point in centers:
        rr,cc=disk(point,5,shape=mask.shape);mask[rr,cc]=1
    tip=centers[[5,245]]
    t=angle[125]
    side=centers[125]+2.5*np.array([np.sin(t),np.cos(t)])
    points=np.vstack([tip,centers[125],side])
    foci=pd.DataFrame({'y':points[:,0],'x':points[:,1]})
    return mask,centers,foci


def test_vibrio_pole_foci_are_centered_without_centering_real_lateral_foci():
    mask,_,foci=curved_cell();original=mask.copy();raw=foci.copy(deep=True)
    image=np.ones(mask.shape)
    _,old=extract_profiles(mask,image,pixel_size=.1,source='V',method='principal axis',foci=foci)
    cells,profiles=extract_profiles(mask,image,pixel_size=.1,source='V',foci=foci)
    old=old[old.profile=='focus'];points=profiles[profiles.profile=='focus']
    assert np.abs(old.relative_width.iloc[:2]).min()>.3
    assert np.abs(points.relative_width.iloc[:2]).max()<.06
    assert np.abs(points.relative_width.iloc[2])<.06
    assert np.abs(points.relative_width.iloc[3])>.15
    assert np.abs(points.normal_distance_um.iloc[3])>.2
    assert cells.profile_method.iloc[0]=='medial axis'
    expected_length=(38*(2.4-.1)+10)*.1
    assert cells.axis_length_um.iloc[0]==pytest.approx(expected_length,rel=.04)
    assert cells.axis_length_um.iloc[0]>cells.length_um.iloc[0]
    assert np.all(np.abs(points.relative_width)<=capsule_radius(points.relative_position)+1e-6)
    np.testing.assert_array_equal(mask,original)
    pd.testing.assert_frame_equal(foci,raw)
    np.testing.assert_allclose(points.x_px,foci.x)
    np.testing.assert_allclose(points.y_px,foci.y)


def test_curved_coordinates_are_invariant_to_quarter_rotation_and_preserve_polarity_choice():
    mask,_,foci=curved_cell();image=np.ones(mask.shape)
    _,first=extract_profiles(mask,image,pixel_size=.1,source='V',foci=foci)
    rotated=foci.copy();rotated['y']=mask.shape[1]-1-foci.x;rotated['x']=foci.y
    _,second=extract_profiles(np.rot90(mask),np.rot90(image),pixel_size=.1,source='R',foci=rotated)
    a,b=(p[p.profile=='focus'] for p in (first,second))
    np.testing.assert_allclose(np.abs(a.relative_width),np.abs(b.relative_width),atol=.025)
    np.testing.assert_allclose(np.minimum(a.relative_position,1-a.relative_position),
                               np.minimum(b.relative_position,1-b.relative_position),atol=.02)
    # Bright-pole orientation rotates the reference instead of sliding points sideways.
    image=np.indices(mask.shape)[1].astype(float)
    _,geometric=extract_profiles(mask,image,pixel_size=.1,source='V',foci=foci)
    _,bright=extract_profiles(mask,image,pixel_size=.1,source='V',foci=foci,orientation='bright pole')
    g,h=(p[p.profile=='focus'] for p in (geometric,bright))
    np.testing.assert_allclose(np.abs(g.relative_width),np.abs(h.relative_width),atol=1e-12)


def test_ambiguous_branched_cell_is_refused_instead_of_straightened_arbitrarily():
    mask=np.zeros((80,80),np.uint16)
    mask[10:70,35:45]=1;mask[35:45,10:70]=1
    with pytest.raises(ValueError,match='branched'):
        extract_profiles(mask,np.ones_like(mask),pixel_size=.1,source='branch',method='auto')


def longitudinal_rows():
    rows=[]
    for key,length,offset in [('long',4.,100),('short',2.,0)]:
        for i in range(24):
            if key=='short' and i==12:continue  # A missing measured bin must stay missing.
            rows.append(dict(object_key=key,axis_length_um=length,relative_position=(i+.5)/24,
                             intensity=offset+i,local_width_um=.5+i/100,profile='longitudinal',longitudinal_bins=24))
    return pd.DataFrame(rows)


def test_length_demograph_sorts_cells_and_keeps_their_length_envelope_and_missing_bins():
    data=longitudinal_rows()
    spec=FigureSpec(kind='Demograph',x='relative_position',y='object_key',value='intensity',
                    sort='axis_length_um',demograph_layout='length-scaled columns')
    used,matrix,labels=prepare(data,spec)
    assert list(matrix.columns)==['short','long']
    assert matrix.loc[np.abs(matrix.index)>.5,'short'].isna().all()
    assert matrix.loc[np.abs(matrix.index)<=1,'long'].notna().all()
    assert np.isnan(matrix.loc[0.,'short'])  # The absent bin at relative position just above .5.
    assert used.groupby('object_key').demograph_order.first().to_dict()=={'long':2,'short':1}
    fig=Figure();ax=draw(fig,matrix,spec,labels)
    assert ax.images[0].get_extent()==[0,2,-1,1]
    assert 'ordered by length' in ax.get_xlabel()
    legacy=FigureSpec(kind='Demograph',x='relative_position',y='object_key',value='intensity',sort='axis_length_um')
    _,old,_=prepare(data,legacy)
    assert old.shape==(2,24)


def test_local_width_demograph_keeps_micrometre_units_and_order_export(tmp_path):
    spec=FigureSpec(kind='Demograph',x='relative_position',y='object_key',value='local_width_um',
                    sort='axis_length_um',demograph_layout='length-scaled columns')
    used,plot,labels=prepare(longitudinal_rows(),spec);fig=Figure();draw(fig,plot,spec,labels)
    assert 'µm' in labels['colorlabel']
    export_bundle(tmp_path,fig,used,plot,spec,labels)
    order=pd.read_csv(tmp_path/'cell_order.csv')
    assert order.demograph_length_um.tolist()==[2.,4.]
    spec.normalization='per-cell max'
    with pytest.raises(ValueError,match='raw micrometres'):prepare(longitudinal_rows(),spec)


def two_cell_map():
    mask=np.zeros((55,85),np.uint16)
    mask[5:15,5:70]=1;mask[30:45,10:55]=2
    image=np.zeros(mask.shape);image[mask==1]=1.;image[mask==2]=3.
    return extract_profiles(mask,image,pixel_size=.1,source='cells',map_sampling='interpolated',map_bins=64,map_across=32)


@pytest.mark.parametrize('background',['white','black'])
def test_normalized_cell_heatmap_averages_cells_equally_and_exports_background(tmp_path,background):
    _,data=two_cell_map()
    spec=FigureSpec(kind='Normalized cell heatmap',x='relative_width',y='relative_position',value='intensity',
                    cell_map_shape='capsule',map_background=background,cmap='turbo')
    used,plot,labels=prepare(data,spec)
    assert plot.shape==(64,32)
    assert plot.iloc[32,16]==pytest.approx(2.)
    assert np.isnan(plot.iloc[0,0])
    fig=Figure();ax=draw(fig,plot,spec,labels)
    assert ax.get_facecolor()[:3]==((1.,1.,1.) if background=='white' else (0.,0.,0.))
    assert ax.get_ylim()==(1.05,-.05) and ax.get_box_aspect()==2
    assert 'n = 2 cells' in ax.get_xlabel()
    assert np.all(ax.lines[0].get_xdata()<=.5)
    export_bundle(tmp_path,fig,used,plot,spec,labels)
    assert (tmp_path/'cell_coverage.csv').is_file()
    meta=json.loads((tmp_path/'axes.json').read_text())
    assert meta['axes_facecolor'][:3]==list(ax.get_facecolor()[:3])
    result=subprocess.run([os.sys.executable,str(tmp_path/'reproduce.py')],capture_output=True,text=True,env={**os.environ,'MPLBACKEND':'Agg'})
    assert result.returncode==0,result.stderr
    assert (tmp_path/'reproduced.pdf').is_file()
    assert 'axes_facecolor' in (tmp_path/'reproduce.R').read_text()
    assert 'axes_facecolor' in (tmp_path/'reproduce.m').read_text()


def test_maxima_density_stays_inside_reference_without_moving_source_points():
    mask,_,foci=curved_cell()
    _,profiles=extract_profiles(mask,np.ones(mask.shape),pixel_size=.1,source='V',foci=foci)
    spec=FigureSpec(kind='Maxima map',x='relative_width',y='relative_position',maxima_profile='focus',map_background='black')
    used,plot,labels=prepare(profiles,spec);before=plot.copy(deep=True)
    fig=Figure();ax=draw(fig,plot,spec,labels)
    im=ax.images[0];values=np.ma.filled(im.get_array(),np.nan)
    xe=np.linspace(-.55,.55,values.shape[1]+1);ye=np.linspace(-.05,1.05,values.shape[0]+1)
    xx,yy=np.meshgrid((xe[:-1]+xe[1:])/2,(ye[:-1]+ye[1:])/2)
    assert not np.isfinite(values[np.abs(xx)>capsule_radius(yy)]).any()
    assert np.nanmax(values)==pytest.approx(1.)
    pd.testing.assert_frame_equal(plot,before)
    assert len(used)==len(foci)


def test_interpolated_map_does_not_bridge_a_missing_signal_stripe():
    mask=np.zeros((20,50),np.uint16);mask[5:15,5:45]=1
    image=np.ones(mask.shape);image[:,23:27]=np.nan
    _,profiles=extract_profiles(mask,image,pixel_size=.1,source='missing',
        map_sampling='interpolated',map_bins=64,map_across=32)
    maps=profiles[profiles.profile=='cell map']
    assert not maps.relative_position.between(.47,.53).any()
    assert maps.relative_position.lt(.4).any() and maps.relative_position.gt(.6).any()


def test_large_source_export_splits_excel_sheets_without_dropping_rows(tmp_path,monkeypatch):
    from bactomate.modules import figure_analysis
    monkeypatch.setattr(figure_analysis,'EXCEL_DATA_ROWS',10)
    data=longitudinal_rows()
    spec=FigureSpec(kind='Demograph',x='relative_position',y='object_key',value='intensity',sort='axis_length_um',
                    demograph_layout='length-scaled columns')
    used,plot,labels=prepare(data,spec);fig=Figure();draw(fig,plot,spec,labels)
    export_bundle(tmp_path,fig,used,plot,spec,labels)
    sheets=pd.read_excel(tmp_path/'figure_data.xlsx',sheet_name=None)
    restored=pd.concat([v for k,v in sheets.items() if k.startswith('Source rows')],ignore_index=True)
    pd.testing.assert_frame_equal(restored,used.reset_index(drop=True),check_dtype=False)
    assert len(pd.read_csv(tmp_path/'source_rows.csv'))==len(used)


def test_new_guide_layout_and_heatmap_from_project_images(project_window,qapp):
    from bactomate.gui.figure_guide import FigureGuide
    tab=project_window.figure_analysis_tab
    demo=FigureGuide(tab);demo.goal.setCurrentIndex(demo.goal.findData('demograph'))
    demo.show();qapp.processEvents();demo.next();demo.next()
    assert demo.demograph_layout.currentData()=='length-scaled columns'
    assert demo.normalization.currentData()=='raw'
    demo_plan=demo.plan();demo_pairs=demo.selected_pairs();demo.close()
    tab.apply_figure_plan(demo_plan,demo_pairs)
    assert _wait_until(lambda:tab.snapshot is not None and not tab.worker.isRunning(),timeout_s=20)
    assert tab.snapshot[2].demograph_layout=='length-scaled columns'
    assert tab.snapshot[1].shape[1]==2
    guide=FigureGuide(tab);guide.goal.setCurrentIndex(guide.goal.findData('cell_heatmap'))
    guide.show();qapp.processEvents();guide.next();guide.next()
    assert guide.style.currentText()=='Normalized cell heatmap'
    assert guide.method.currentData()=='auto' and guide.background.currentText()=='black'
    plan=guide.plan();pairs=guide.selected_pairs();guide.close()
    tab.apply_figure_plan(plan,pairs)
    assert _wait_until(lambda:tab.snapshot[2].kind=='Normalized cell heatmap' and not tab.worker.isRunning(),timeout_s=20)
    used,plot,spec,*_=tab.snapshot
    assert spec.cell_map_shape=='capsule' and spec.map_background=='black'
    assert plot.shape==(64,32) and used.object_key.nunique()==2
    assert set(used.map_sampling)=={'linear within measured support'}
    assert not tab.advanced.isChecked()
    edited=FigureGuide(tab);edited.show();qapp.processEvents();edited.next();edited.next()
    assert edited.background.currentText()=='black' and edited.method.currentData()=='auto'
    edited.close()
