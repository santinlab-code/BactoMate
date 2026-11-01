import numpy as np
import pandas as pd
from dataclasses import replace
from matplotlib.figure import Figure
from PyQt6.QtWidgets import QMessageBox,QWidget
from bactomate.modules.figure_analysis import extract_profiles,FigureSpec,prepare,draw,export_bundle


def test_default_24_and_native_measurements_export(tmp_path):
    mask=np.zeros((20,40),np.uint16);mask[7:13,5:35]=1
    image=np.indices(mask.shape)[1].astype(float)
    _,direct=extract_profiles(mask,image,pixel_size=.1,source='XY')
    assert direct[direct.profile=='longitudinal'].position.nunique()<=24
    _,native=extract_profiles(mask,image,pixel_size=.1,source='XY',sampling='native')
    measured=native[native.profile=='native longitudinal'];resampled=native[native.profile=='longitudinal']
    assert len(resampled)==24 and measured.pixel_count.sum()==180
    assert np.isfinite(resampled.intensity).all()
    spec=FigureSpec(kind='Demograph',x='relative_position',y='object_key',value='intensity')
    used,plot,labels=prepare(native,spec);fig=Figure();draw(fig,plot,spec,labels)
    export_bundle(tmp_path,fig,used,plot,spec,labels,native_profiles=measured)
    assert (tmp_path/'native_profiles.csv').exists() and not list(tmp_path.glob('*.png'))


def test_pipeline_never_generates_png(tmp_path):
    import tifffile
    from bactomate.modules.pipeline_outputs import write_png_preview_from_tiff,write_png_previews_for_tiffs
    path=tmp_path/'mask.tif';tifffile.imwrite(path,np.ones((10,10),np.uint16))
    assert write_png_preview_from_tiff(path) is None
    assert write_png_previews_for_tiffs([path])==[]
    assert not list(tmp_path.glob('*.png'))


def test_figure_close_cancel_save_and_discard(qapp,monkeypatch):
    from bactomate.gui.tabs.figure_analysis import FigureAnalysisTab
    tab=FigureAnalysisTab();source=pd.DataFrame({'x':[1,2,3]})
    tab.plot_table(source,FigureSpec(x='x'),{});window=tab._figure_windows[-1]
    try:
        monkeypatch.setattr('bactomate.gui.image_close.close_choice',lambda *_:QMessageBox.StandardButton.Cancel)
        window.close();assert window.isVisible()
        called=[];monkeypatch.setattr(window,'export',lambda **kw:called.append(True) or True)
        monkeypatch.setattr('bactomate.gui.image_close.close_choice',lambda *_:QMessageBox.StandardButton.Save)
        window.close();assert called and not window.isVisible()
        window.show();monkeypatch.setattr('bactomate.gui.image_close.close_choice',lambda *_:QMessageBox.StandardButton.Discard)
        window.close();assert not window.isVisible()
    finally:tab.close_figure_windows();tab.close()


def test_units_and_changed_metric_do_not_keep_stale_ylabel(qapp):
    from bactomate.gui.tabs.guided_analysis import GuidedAnalysisTab
    from bactomate.gui.figure_guide import FigurePlan,FigureGuide
    from bactomate.gui.publication_figure_window import FigureOptions
    parent=QWidget();tab=GuidedAnalysisTab(parent)
    table=pd.DataFrame({'length_um':[2.,3.,4.],'width_um':[.5,.7,.8]})
    tab.set_tables({'Cells':table},{})
    plan=FigurePlan(goal='distribution',kind='Box plot',dataset='Cells',metric='length_um',compare=False,replicate=False,figure_options={'ylabel':'Old length'})
    tab.apply_figure_plan(plan,[])
    guide=FigureGuide(tab);guide.metric.setCurrentText('width_um')
    new=guide.plan();new.kind='Box plot'
    assert 'ylabel' not in new.figure_options
    tab.apply_figure_plan(new,[])
    assert 'width' in tab.figure.axes[0].get_ylabel().lower()
    dialog=FigureOptions(tab._figure_windows[-1]);dialog.export_unit.setCurrentText('pixels')
    assert dialog.values['figure_width'].value()==1800
    dialog.values['figure_width'].setValue(1200);dialog.apply()
    assert tab._figure_windows[-1].spec.figure_width==4
    dialog.close();guide.close();tab.close_figure_windows();tab.close();parent.close()


def test_detached_close_saves_actual_image(qapp,tmp_path,monkeypatch):
    from PyQt6.QtGui import QPixmap
    from PyQt6.QtCore import Qt
    from PIL import Image
    from bactomate.gui.preview.preview_window import PreviewDialogBase
    from bactomate.gui.preview.detachable_image import DetachablePreviewImage
    preview=PreviewDialogBase(title='Segmentation');controller=DetachablePreviewImage(preview)
    pixmap=QPixmap(20,20);pixmap.fill(Qt.GlobalColor.red);preview.canvas.set_pixmap(pixmap,(20,20))
    preview.show();controller.detach()
    path=tmp_path/'snapshot.tif'
    monkeypatch.setattr('bactomate.gui.image_close.close_choice',lambda *_:QMessageBox.StandardButton.Save)
    monkeypatch.setattr('bactomate.gui.image_close.QFileDialog.getSaveFileName',lambda *a,**kw:(str(path),'TIFF'))
    controller.window.close()
    assert Image.open(path).getpixel((0,0))==(255,0,0)
    assert not controller.window.isVisible() and not controller.is_detached
    preview.close()
