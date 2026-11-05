"""Analysis uses the page for settings, with source values in an opt-in window."""
import pandas as pd
import pytest
from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtWidgets import QComboBox, QDoubleSpinBox, QLineEdit, QSpinBox


def _settle(qapp):
    for _ in range(20):qapp.processEvents()


@pytest.mark.parametrize('width,columns', [(1280,3),(900,2),(600,1)])
def test_advanced_settings_use_full_width_and_reflow(qapp, monkeypatch, width, columns):
    from bactomate.gui.tabs.guided_analysis import GuidedAnalysisTab
    from bactomate.gui.styles import get_modern_stylesheet
    old=qapp.styleSheet();qapp.setStyleSheet(get_modern_stylesheet())
    tab=GuidedAnalysisTab()
    monkeypatch.setattr(tab,'refresh_catalog',lambda:None)
    try:
        tab.resize(width,900);tab.show();tab.advanced.setChecked(True)
        _settle(qapp)
        assert tab.controls_scroll.width() >= tab.width()-40
        assert tab.advanced_controls.columns == columns
        assert tab.groups_button.isVisible()
        assert not tab.show_data_table.isChecked() and not tab.data_table_window.isVisible()
        assert tab.data_table_window.isWindow()
        rects=[card.geometry() for card in tab.advanced_controls.cards]
        assert all(not a.intersects(b) for i,a in enumerate(rects) for b in rects[i+1:])
        if columns>1:assert len({rect.x() for rect in rects})==columns
        for card in tab.advanced_controls.cards:
            assert card.isVisible()
            for control in card.findChildren((QComboBox,QDoubleSpinBox,QSpinBox,QLineEdit)):
                pos=control.mapTo(card,QPoint())
                assert control.height()>=control.minimumSizeHint().height()
                assert pos.x()>=0 and pos.x()+control.width()<=card.width()
                assert pos.y()>=0 and pos.y()+control.height()<=card.height()
    finally:
        tab.close();tab.deleteLater();qapp.setStyleSheet(old)


def test_data_window_is_optional_complete_read_only_and_tracks_close(qapp,monkeypatch):
    from bactomate.gui.tabs.guided_analysis import GuidedAnalysisTab
    tab=GuidedAnalysisTab();monkeypatch.setattr(tab,'refresh_catalog',lambda:None)
    cells=pd.DataFrame({'area_um2':range(250),'Condition':['WT']*250,'Replicate':['R1']*250})
    foci=pd.DataFrame({'intensity':[101.,202.]})
    original=cells.copy(deep=True)
    try:
        tab.resize(1200,850);tab.show();_settle(qapp)
        tab.set_tables({'Cells':cells,'Foci':foci},{})
        window=tab.data_table_window
        assert not window.isVisible()
        for advanced in (True,False,True):
            tab.advanced.setChecked(advanced);_settle(qapp)
            assert not window.isVisible()
            assert tab.groups_button.isVisible()
            if not advanced:assert tab.controls_scroll.verticalScrollBar().maximum()==0
        tab.show_data_table.setChecked(True);_settle(qapp)
        model=window.model
        assert window.isVisible() and tab.preview.window() is window
        assert model.rowCount()==250 and model.columnCount()==3
        index=model.index(249,0)
        assert model.data(index)=='249'
        assert not model.flags(index)&Qt.ItemFlag.ItemIsEditable
        assert not model.setData(index,'999')
        # Looking at another source table must not alter plotting choices.
        sheet=tab.sheet.currentText();metric=tab.fields['x'].currentText()
        window.dataset.setCurrentText('Foci')
        assert model.rowCount()==2 and model.data(model.index(1,0))=='202.0'
        assert model.data(index) is None  # A queued view lookup from the previous table.
        assert tab.sheet.currentText()==sheet and tab.fields['x'].currentText()==metric
        window.close();_settle(qapp)
        assert not tab.show_data_table.isChecked()
        tab.show_data_table.setChecked(True);_settle(qapp)
        assert tab.data_table_window is window and model.rowCount()==250
        tab.sheet.setCurrentText('Foci');_settle(qapp)
        assert model.rowCount()==2
        tab.clear_session();_settle(qapp)
        assert model.rowCount()==0 and not window.isVisible()
        assert not tab.show_data_table.isChecked()
        pd.testing.assert_frame_equal(cells,original)
    finally:tab.close();tab.deleteLater()
