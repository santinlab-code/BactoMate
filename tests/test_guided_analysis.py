import json
import subprocess
import os
import pandas as pd
import numpy as np
from matplotlib.figure import Figure
from bactomate.modules.analysis_catalog import discover_results,read_catalog,assemble_catalog,save_assignments,read_assignments
from bactomate.modules.figure_analysis import FigureSpec,prepare,draw,export_bundle


def make_results(root):
    directory=root/'_analysis';directory.mkdir(parents=True)
    for filename,area in [('x_xy1',[1.,2.,3.]),('x_xy2',[2.,3.,4.]),('y_xy1',[4.,5.,6.])]:
        with pd.ExcelWriter(directory/(filename+'_analysis.xlsx')) as writer:
            pd.DataFrame({'cell_id':[1,2,3],'area_um2':area}).to_excel(writer,sheet_name='Per-Cell Data',index=False)
    pd.DataFrame({'cell_id':[1,2,3],'area_um2':[1.,2.,3.]}).to_csv(directory/'x_xy1_per_cell.csv',index=False)
    (directory/'figure_export').mkdir()
    pd.DataFrame({'fake':[1]}).to_csv(directory/'figure_export'/'source_rows.csv',index=False)
    pd.DataFrame({'area_um2':[10000]}).to_excel(directory/'master_per_cell_summary.xlsx',index=False)
    return directory


def test_auto_catalog_deduplicates_and_persists_groups(tmp_path):
    directory=make_results(tmp_path)
    assert len(discover_results(tmp_path))==3
    entries,errors=read_catalog(tmp_path)
    assert not errors
    choices={e['id']:dict(condition='Y' if 'y_xy' in e['id'] else 'X',replicate='R1') for e in entries}
    save_assignments(tmp_path,choices)
    table=assemble_catalog(entries,read_assignments(tmp_path))['Cellules']
    assert len(table)==9
    assert table.groupby('Condition')['Réplicat'].nunique().to_dict()=={'X':1,'Y':1}
    assert set(table['Fichier source'])==set(choices)
    # New analyses are discovered on the next scan without manual loading.
    pd.DataFrame({'cell_id':[8],'area_um2':[8.]}).to_csv(directory/'new_analysis.csv',index=False)
    assert len(discover_results(tmp_path))==4


def test_replicate_points_and_export_use_replicate_means(tmp_path):
    table=pd.DataFrame({'area':[1.,2.,3.,4.,5.,6.], 'Condition':['X']*3+['Y']*3,'Réplicat':['R1','R1','R2']*2})
    spec=FigureSpec(kind='Violin plot',x='area',group='Condition',replicate='Réplicat')
    used,plot,labels=prepare(table,spec);fig=Figure();ax=draw(fig,plot,spec,labels)
    assert [t.get_text() for t in ax.legend_.texts]==['R1','R2']
    export_bundle(tmp_path,fig,used,plot,spec,labels)
    summary=pd.read_excel(tmp_path/'figure_data.xlsx',sheet_name='Replicates')
    assert summary['count'].sum()==6
    assert summary['mean'].tolist()==[1.5,3.,4.5,6.]
    result=subprocess.run([os.sys.executable,str(tmp_path/'reproduce.py')],capture_output=True,text=True,env={**os.environ,'MPLBACKEND':'Agg'})
    assert result.returncode==0,result.stderr


def test_guided_view_uses_workspace_without_file_dialog(tmp_path,qapp,monkeypatch):
    from PyQt6.QtWidgets import QWidget,QFileDialog
    from bactomate.gui.tabs.guided_analysis import GuidedAnalysisTab
    from tests.test_filtering_preview_apply_flow import _wait_until
    make_results(tmp_path)
    parent=QWidget();parent._workspace_root=tmp_path
    tab=GuidedAnalysisTab(parent)
    monkeypatch.setattr(QFileDialog,'getOpenFileNames',lambda *args: (_ for _ in ()).throw(AssertionError('No manual loading')))
    try:
        tab.refresh_catalog()
        assert _wait_until(lambda:'Cellules' in tab.tables,timeout_s=10)
        assert not tab.advanced.isChecked()
        assert tab.control_stack.currentIndex()==0
        assert tab.metric.currentData()=='area_um2'
        choices={e['id']:dict(condition='Y' if 'y_xy' in e['id'] else 'X',replicate='R1') for e in tab.entries}
        save_assignments(tmp_path,choices);tab.assignments=choices;tab.rebuild_catalog()
        tab.render()
        assert tab.export.isEnabled()
        assert tab.snapshot[2].kind=='Violin plot'
        assert tab.snapshot[2].replicate=='Réplicat'
        assert len(tab.snapshot[0])==9
        tab.advanced.setChecked(True)
        assert tab.kind.count()==11
        assert not tab.export.isHidden()
        tab.render()
        assert tab.export.isEnabled()
    finally:
        if tab.catalog_worker is not None:tab.catalog_worker.wait()
        tab.close();parent.close()


def test_summary_sheet_is_not_pooled_with_cells(tmp_path):
    directory=tmp_path/'_analysis';directory.mkdir()
    with pd.ExcelWriter(directory/'sample_analysis.xlsx') as writer:
        pd.DataFrame({'cell_count':[1000],'area_um2':[5000]}).to_excel(writer,sheet_name='Summary',index=False)
        pd.DataFrame({'cell_id':[1,2],'area_um2':[1.,2.]}).to_excel(writer,sheet_name='Per-Cell Data',index=False)
    entries,_=read_catalog(tmp_path);tables=assemble_catalog(entries,{})
    assert next(iter(tables))=='Cellules'
    assert len(tables['Cellules'])==2
    assert len(tables['Résumé · Summary'])==1


def test_existing_metadata_and_missing_assignments_are_explicit(tmp_path):
    directory=tmp_path/'analyses';directory.mkdir()
    pd.DataFrame({'cell_id':[1,2],'area_um2':[1.,2.], 'condition':['X','Y'],'replicate':['R1','R2']}).to_csv(directory/'cells.csv',index=False)
    entries,_=read_catalog(tmp_path);table=assemble_catalog(entries,{})['Cellules']
    assert table.Condition.tolist()==['X','Y']
    assert table['Réplicat'].tolist()==['R1','R2']
    table=assemble_catalog(entries,{entries[0]['id']:dict(condition='Z',replicate='R3')})['Cellules']
    assert table.Condition.tolist()==['Z','Z']


def test_guided_frame_and_project_reset(tmp_path,qapp):
    from PyQt6.QtWidgets import QWidget
    from bactomate.gui.tabs.guided_analysis import GuidedAnalysisTab
    parent=QWidget();tab=GuidedAnalysisTab(parent)
    try:
        tab.set_tables({'Cellules':pd.DataFrame({'area_um2':[1.,2.,5.,8.],'frame':[0,0,1,1],
            'Condition':['X']*4,'Réplicat':['R1']*4})},{})
        assert tab.frame_choice.currentData()=='0'
        tab.render();assert tab.export.isEnabled()
        assert len(tab.snapshot[0])==2
        tab.refresh_catalog() # No workspace or upstream path: old data cannot survive.
        assert tab.tables=={} and tab.snapshot is None
        assert not tab.simple_export.isEnabled()
    finally:tab.close();parent.close()
