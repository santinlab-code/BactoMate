import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from bactomate.gui.preview.preview_window import HistogramLUTWidget,PreviewDialogBase,RenderResult


def test_histogram_context_preserves_channel_lut(qapp):
    lut=HistogramLUTWidget()
    lut.set_context(('image','GFP'))
    lut.set_frame(np.arange(100).reshape(10,10))
    lut.set_lut(10,70)
    lut.set_context(('image','mCherry'))
    lut.set_frame(np.arange(1000,1100).reshape(10,10),preserve_user_lut=False)
    lut.set_lut(1005,1080)
    lut.set_context(('image','GFP'))
    lut.set_lut(None,None) # historical navigation reset must not erase the channel.
    lut.set_frame(np.arange(100).reshape(10,10),preserve_user_lut=False)
    assert lut.current_lut()==(10,70)
    lut.set_context(('image','mCherry'))
    assert lut.current_lut()==(1005,1080)
    lut.close()


def test_preview_source_and_channel_cache(qapp):
    from PyQt6.QtGui import QPixmap
    preview=PreviewDialogBase(title='Conversion')
    seen=[]
    def render(st):
        seen.append((st.source_key,st.channel_idx,st.vmin,st.vmax))
        return RenderResult(QPixmap(10,10),(10,10),lut_frame=np.arange(100).reshape(10,10))
    preview.set_render_callback(render)
    preview.set_source_key(('file',0));preview.refresh()
    preview.lut_widget.set_lut(12,42)
    preview.set_channel_idx(1);preview.refresh();preview.lut_widget.set_lut(20,90)
    preview.set_channel_idx(0)
    preview.state().vmin=None;preview.lut_widget.set_lut(None,None)
    preview.refresh()
    assert seen[-1][2:]==(12,42)
    preview.set_channel_idx(1);preview.refresh()
    assert seen[-1][2:]==(20,90)
    preview.close()


def test_escape_sidebar_center_and_scrollbars(qapp):
    from PyQt6.QtGui import QPixmap
    from bactomate.gui.preview.detachable_image import DetachablePreviewImage
    preview=PreviewDialogBase(title='Segmentation')
    controller=DetachablePreviewImage(preview)
    try:
        preview.show();controller.detach();qapp.processEvents()
        pixmap=QPixmap(800,600);pixmap.fill(Qt.GlobalColor.gray)
        preview.canvas.set_pixmap(pixmap,(800,600))
        qapp.processEvents()
        QTest.keyClick(preview.canvas,Qt.Key.Key_Escape)
        assert controller.window.isVisible() and controller.is_detached
        assert preview.lut_section.parentWidget() is controller.lut_sidebar
        assert controller.lut_sidebar.mapTo(controller.window,controller.lut_sidebar.rect().topLeft()).x() > controller.image_host.mapTo(controller.window,controller.image_host.rect().topLeft()).x()
        preview.canvas._zoom=2
        preview.canvas.center_on_image_point(600,450)
        controller._sync_scrollbars()
        assert controller.horizontal.value()==60000
        controller.horizontal.setValue(30000)
        scale=preview.canvas.view_scale();offset=preview.canvas._total_offset(scale)
        assert abs((preview.canvas.width()/2-offset.x())/scale-300)<.1
        controller.recenter.click()
        assert preview.canvas._zoom==1 and preview.canvas._pan_offset.isNull()
    finally:preview.close()


def test_filtering_view_roundtrip_keeps_lut(tmp_path,qapp):
    import tifffile
    from tests.test_filtering_preview_apply_flow import (_write_phase_tif,_open_preview,
        _wait_for_filter_apply,_wait_until,_shutdown)
    from bactomate.gui.preview.navigation_controls import PreviewNavState
    _write_phase_tif(tmp_path,pixel_size_um=.108,nonzero=True)
    tifffile.imwrite(tmp_path/'sample_foci_GFP.tif',np.arange(256*256,dtype=np.uint16).reshape(1,256,256))
    tab,parent,dlg=_open_preview(tmp_path)
    try:
        assert _wait_for_filter_apply(dlg)
        phase=next(i for i,p in enumerate(dlg._bg_paths) if '_foci' not in str(p))
        gfp=next(i for i,p in enumerate(dlg._bg_paths) if '_foci' in str(p))
        nav=dlg._nav_ctrl
        def switch(index):
            key=('file',index)
            nav.set_state(PreviewNavState(source_key=key,frame_idx=0),emit=True)
            assert _wait_until(lambda: dlg.state().source_key==key)
            dlg.refresh()
        switch(phase);dlg.lut_widget.set_lut(1400,3000)
        switch(gfp);dlg.lut_widget.set_lut(500,50000)
        switch(phase)
        assert dlg.lut_widget.current_lut()==(1400,3000)
        assert (dlg.state().vmin,dlg.state().vmax)==(1400,3000)
        switch(gfp)
        assert dlg.lut_widget.current_lut()==(500,50000)
    finally:_shutdown(tab,parent)
