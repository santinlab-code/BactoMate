"""Mac/Windows regression cases from the November 2026 session logs."""
from pathlib import Path
from types import SimpleNamespace
import json
import logging

import numpy as np
import pytest
import tifffile

from bactomate.modules import segmentation_runtime as runtime


class Model:
    def __init__(self, checkpoint=None, error=None):
        self.cp = SimpleNamespace(nchan=2, nclasses=4, device='cpu', pretrained_model=checkpoint)
        self.calls = []
        self.error = error

    def eval(self, image, **kwargs):
        self.calls.append((image.copy(), kwargs.copy()))
        if self.error == 'shape' and not kwargs['resample']:
            raise ValueError('could not broadcast input array from shape (1461,1461) into shape (1462,1462)')
        if self.error == 'fatal':
            raise RuntimeError('network failure')
        mask = np.zeros(image.shape[:2], np.uint16)
        mask[image[..., 0] > 0 if image.ndim == 3 else image > 0] = 1
        return mask, [], [], None


def test_shape_recovery_preserves_pixels_diameter_and_provenance(tmp_path, caplog):
    checkpoint = tmp_path/'model'; checkpoint.write_bytes(b'weights')
    model = Model(str(checkpoint), 'shape')
    image = np.zeros((51, 53), np.uint16); image[-1, -1] = 123
    with caplog.at_level(logging.INFO, logger='bactomate'):
        mask = runtime.evaluate_omnipose_plane(model, image, diameter=33)
    assert mask.shape == image.shape and mask[-1, -1] == 1
    assert len(model.calls) == 2
    for value, params in model.calls:
        np.testing.assert_array_equal(value, image)
        assert params['diameter'] == 33 and params['tile'] and params['batch_size'] == 1
    assert not model.calls[0][1]['resample'] and model.calls[1][1]['resample']
    records = [r.getMessage().split('[segmentation result] ', 1)[1]
               for r in caplog.records if '[segmentation result] ' in r.getMessage()]
    # Some backend formatters prefix/suffix ANSI text on the same LogRecord.
    result = json.JSONDecoder().raw_decode(records[-1])[0]
    assert result['checkpoint']['sha256'] == runtime.file_fingerprint(checkpoint)['sha256']
    assert result['pixels_sha256'] == runtime.pixel_fingerprint(image)
    assert result['cells'] == 1 and result['parameters']['resample']


def test_unknown_error_stops_and_valid_empty_mask_remains_valid():
    image = np.zeros((40, 40), np.uint16)
    with pytest.raises(RuntimeError, match='network failure'):
        runtime.evaluate_omnipose_plane(Model(error='fatal'), image)
    result = runtime.evaluate_omnipose_plane(Model(), image)
    assert result.shape == image.shape and not result.any()


def test_cache_signature_changes_with_pixels_weights_and_protocol(tmp_path, monkeypatch):
    checkpoint = tmp_path/'model';checkpoint.write_bytes(b'first weights')
    image = np.zeros((40,40),np.float32)
    first = runtime.preview_signature(image, checkpoint)
    image[4,4] = 1
    assert runtime.preview_signature(image,checkpoint) != first
    image[4,4] = 0
    checkpoint.write_bytes(b'second weights with a new size')
    assert runtime.preview_signature(image,checkpoint) != first
    before = runtime.preview_signature(image,checkpoint)
    monkeypatch.setattr(runtime,'environment_snapshot',lambda:{'protocol':'changed'})
    assert runtime.preview_signature(image,checkpoint) != before


def _stub_loader(monkeypatch, tmp_path, model):
    checkpoint = tmp_path/'model';checkpoint.write_bytes(b'weights')
    monkeypatch.setattr('bactomate.gui.omnipose_pretrained_cache.ensure_builtin_in_bactomate_cache',lambda *_a,**_k:checkpoint)
    monkeypatch.setattr('bactomate.gui.omnipose_utils.load_cellpose_segmentation_model',lambda **_:model)


def test_folder_and_batch_use_identical_native_inference(tmp_path,monkeypatch):
    from bactomate.gui.folder_preview.seg_compute import segment_plane_with_model
    from bactomate.scripts.batch_process_tiff_sequence import process_frames_with_omnipose
    image = np.zeros((2050,40),np.uint16);image[-1,-1]=100
    path=tmp_path/'phase.tif';tifffile.imwrite(path,image)
    model = Model();_stub_loader(monkeypatch,tmp_path,model)
    preview=segment_plane_with_model(image,model,diameter=30,flow_threshold=.4,mask_threshold=0,cluster=False)
    exported=process_frames_with_omnipose([str(path)],model_type='bact_phase_omni',diameter=30,use_gpu=False)[0]
    np.testing.assert_array_equal(preview,exported)
    assert preview[-1,-1] == 1 and len(model.calls)==2
    assert model.calls[0][1] == model.calls[1][1]
    assert all(value.shape == image.shape for value,_ in model.calls)


def test_failed_file_never_calls_mask_writer(tmp_path,monkeypatch):
    import sys
    from bactomate.scripts import batch_process_tiff_sequence as script
    image=np.ones((40,40),np.uint16);path=tmp_path/'phase.tif';tifffile.imwrite(path,image)
    model=Model(error='fatal');_stub_loader(monkeypatch,tmp_path,model)
    written=[]
    monkeypatch.setattr(script,'concatenate_masks',lambda *a,**k:written.append(True))
    monkeypatch.setattr(sys,'argv',['batch_process_tiff_sequence',str(path),'--output',str(tmp_path/'output'),'--no-gpu'])
    with pytest.raises(RuntimeError,match='No new mask stack was written'):
        script.main()
    assert not written and not list((tmp_path/'output').rglob('*masks.tif'))


def test_deleted_preview_controls_disconnect_from_main(qapp):
    from PyQt6.QtWidgets import QDoubleSpinBox,QCheckBox
    from PyQt6.QtCore import QCoreApplication,QEvent
    from bactomate.gui.tabs.omnipose_seg import OmniposeSegTab
    main,pv=QDoubleSpinBox(),QDoubleSpinBox()
    before=main.receivers(main.valueChanged)
    OmniposeSegTab._link_spinboxes(pv,main)
    assert main.receivers(main.valueChanged)==before+1
    pv.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
    main.setValue(40)
    assert main.receivers(main.valueChanged)==before
    main_cb,pv_cb=QCheckBox(),QCheckBox()
    before=main_cb.receivers(main_cb.toggled)
    OmniposeSegTab._link_checkboxes(pv_cb,main_cb)
    pv_cb.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
    main_cb.setChecked(True)
    assert main_cb.receivers(main_cb.toggled)==before
    main.deleteLater();main_cb.deleteLater()


def test_gpu_checkbox_applies_to_preview_parameters(qapp):
    from bactomate.gui.tabs.omnipose_seg import OmniposeSegTab
    tab=OmniposeSegTab()
    try:
        tab.use_gpu.setChecked(False)
        assert tab._folder_preview_seg_params()['use_gpu'] is False
        tab.use_gpu.setChecked(True)
        assert tab._folder_preview_seg_params()['use_gpu'] is True
    finally:tab.close();tab.deleteLater()


def test_pinned_versions_match_installer_baseline():
    from packaging.requirements import Requirement
    root=Path(__file__).resolve().parents[1]
    pinned={}
    for line in (root/'requirements.txt').read_text().splitlines():
        line=line.split('#',1)[0].strip()
        if not line:continue
        requirement=Requirement(line)
        pinned[requirement.name]=str(requirement.specifier)
    assert all(pinned[name]=='=='+version for name,version in runtime.EXPECTED.items())
    assert not runtime.baseline_issues()


def test_cpu_smoke_failure_returns_nonzero(monkeypatch):
    import sys
    from bactomate.scripts import check_environment
    def fail():
        raise RuntimeError('cannot load model')
    monkeypatch.setattr(check_environment,'segmentation_smoke_test',fail)
    monkeypatch.setattr(sys,'argv',['check_environment','--segmentation-smoke-test'])
    assert check_environment.main() == 1


def test_cuda_checker_requires_pinned_releases_and_actual_cuda(monkeypatch):
    import sys,importlib.util,importlib.metadata
    root=Path(__file__).resolve().parents[1]
    spec=importlib.util.spec_from_file_location('cuda_stack_check',root/'setup/windows/check_torch_cuda_bundle.py')
    checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
    modules={name:SimpleNamespace(__version__=version) for name,version in
             [('torch','2.11.0+cu128'),('torchvision','0.26.0+cu128'),('torchaudio','2.11.0+cu128')]}
    modules['torch'].cuda=SimpleNamespace(is_available=lambda:False)
    modules['torchvision.ops']=SimpleNamespace(nms=lambda *a:None)
    for name,module in modules.items():monkeypatch.setitem(sys.modules,name,module)
    monkeypatch.setattr(importlib.metadata,'version',lambda name:modules[name].__version__)
    assert checker.bundle_ok()
    monkeypatch.setattr(sys,'argv',['check_torch_cuda_bundle','--require-cuda'])
    assert checker.main() == 1
    modules['torch'].__version__='2.12.0+cu128'
    assert not checker.bundle_ok()


def test_builtin_weights_cannot_silently_differ(tmp_path,monkeypatch):
    from bactomate.gui import omnipose_pretrained_cache as cache
    from hashlib import sha256
    path=tmp_path/'bact_phase_omnitorch_0';path.write_bytes(b'expected weights')
    monkeypatch.setitem(cache.BUILTIN_SHA256,'bact_phase_omni',sha256(path.read_bytes()).hexdigest())
    assert cache.validate_builtin_checkpoint(path,'bact_phase_omni')==path.resolve()
    path.write_bytes(b'a different model with the same filename')
    with pytest.raises(RuntimeError,match='checkpoint differs'):
        cache.validate_builtin_checkpoint(path,'bact_phase_omni')
    assert path.read_bytes()==b'a different model with the same filename'
