"""Shared Omnipose inference and provenance for previews and saved results."""
from __future__ import annotations

from functools import lru_cache
from importlib import metadata
import hashlib
import json
import logging
from pathlib import Path
import platform
import sys

import numpy as np


PROTOCOL = 'omnipose-native-tiled-v1'
EXPECTED = {'omnipose': '1.1.4', 'cellpose-omni': '0.9.1', 'dbscan': '0.0.12',
            'torch': '2.11.0', 'torchvision': '0.26.0', 'numpy': '1.26.4',
            'scipy': '1.17.1', 'scikit-image': '0.24.0', 'scikit-learn': '1.9.1',
            'numba': '0.68.0', 'edt': '3.1.2', 'fastremap': '1.21.0',
            'opencv-python-headless': '4.11.0.86', 'ncolor': '1.5.3',
            'tifffile': '2026.3.3', 'nd2': '0.12.0'}
PACKAGES = ('omnipose', 'cellpose-omni', 'dbscan', 'torch', 'torchvision',
            'numpy', 'scipy', 'scikit-image', 'scikit-learn', 'tifffile', 'nd2',
            'numba', 'edt', 'fastremap', 'opencv-python-headless', 'ncolor')
LOG = logging.getLogger('bactomate')
_LAST_RESULT = None


def baseline_issues():
    installed = environment_snapshot()['packages']
    return [f'{name}: installed {installed.get(name)}, expected {wanted}'
            for name, wanted in EXPECTED.items()
            if (installed.get(name) or '').split('+', 1)[0] != wanted]


def last_segmentation_result():
    return _LAST_RESULT


def clear_last_segmentation_result():
    global _LAST_RESULT
    _LAST_RESULT = None


@lru_cache(maxsize=32)
def _file_hash(path, size, modified):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def file_fingerprint(path):
    """Content hash, cached only while file size and modification time match."""
    path = Path(path).resolve()
    stat = path.stat()
    return {'path': str(path), 'sha256': _file_hash(str(path), stat.st_size, stat.st_mtime_ns)}


def pixel_fingerprint(image):
    image = np.ascontiguousarray(image, dtype=np.float32)
    digest = hashlib.sha256(str(image.shape).encode())
    digest.update(image.tobytes())
    return digest.hexdigest()


@lru_cache(maxsize=1)
def environment_snapshot():
    versions = {}
    for name in PACKAGES:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = None
    sources = {}
    for package, relative in [('cellpose-omni', 'cellpose_omni/models.py'),
                              ('cellpose-omni', 'cellpose_omni/core.py'),
                              ('omnipose', 'omnipose/core.py')]:
        try:
            sources[relative] = file_fingerprint(metadata.distribution(package).locate_file(relative))['sha256']
        except (OSError, metadata.PackageNotFoundError):
            sources[relative] = None
    try:
        engine_hash = file_fingerprint(__file__)['sha256']
    except OSError:
        engine_hash = None  # Frozen bundles may not retain a source .py file.
    return {'protocol': PROTOCOL, 'python': platform.python_version(),
            'platform': platform.platform(), 'executable': sys.executable,
            'engine_sha256': engine_hash,
            'packages': versions, 'backend_sources_sha256': sources}


def checkpoint_for_model(model):
    core = getattr(model, 'cp', model)
    paths = getattr(core, 'pretrained_model', None)
    if isinstance(paths, (list, tuple)):
        paths = paths[0] if paths else None
    if isinstance(paths, (str, Path)) and Path(paths).is_file():
        return file_fingerprint(paths)
    return None


def model_device(model):
    return str(getattr(getattr(model, 'cp', model), 'device', 'unknown'))


def configure_inference(model):
    """Request stable kernels; CPU is the reference for cross-device comparisons."""
    import torch
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    if hasattr(torch.backends.cudnn, 'allow_tf32'):
        torch.backends.cudnn.allow_tf32 = False
    if hasattr(torch.backends.cuda.matmul, 'allow_tf32'):
        torch.backends.cuda.matmul.allow_tf32 = False
    if model_device(model).split(':')[0] == 'cpu':
        core = getattr(model, 'cp', model)
        if hasattr(core, 'mkldnn'):
            core.mkldnn = False
        torch.set_num_threads(1)


def preview_signature(image, checkpoint=None):
    """Invalidate previews after pixel, model, implementation or package changes."""
    payload = {'environment': environment_snapshot(), 'pixels': pixel_fingerprint(image),
               'checkpoint': file_fingerprint(checkpoint) if checkpoint and Path(checkpoint).is_file() else None}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def evaluate_omnipose_plane(model, image, *, diameter=30., flow_threshold=.4,
                            mask_threshold=0., cluster=False, affinity_seg=False,
                            channels=(0, 0), omni=True, verbose=False):
    """One native-resolution plane, identical kwargs for every application entry.

    Cellpose-Omni 0.9.x can round its scaled/padded output one pixel differently when
    resample=False. Retry only that shape error with native-grid resampling.
    Never crop pixels, change the requested diameter, or fabricate empty masks.
    """
    image = np.ascontiguousarray(image, dtype=np.float32)
    if image.ndim not in (2, 3) or image.size == 0 or not np.isfinite(image).all():
        raise ValueError('Segmentation needs a finite, nonempty YX or YXC image.')
    configure_inference(model)
    diameter = float(diameter) if diameter is not None else 0.
    if not np.isfinite(diameter) or diameter < 0:
        raise ValueError('Diameter must be nonnegative and finite (0 = automatic).')
    kwargs = dict(channels=list(channels), diameter=diameter,
                  flow_threshold=float(flow_threshold), mask_threshold=float(mask_threshold),
                  cellprob_threshold=0., do_3D=False, omni=bool(omni),
                  affinity_seg=bool(affinity_seg), cluster=bool(cluster),
                  net_avg=False, normalize=True, resample=False, tile=True,
                  augment=False, batch_size=1, verbose=bool(verbose))
    run = {'environment': environment_snapshot(), 'checkpoint': checkpoint_for_model(model),
           'pixels_sha256': pixel_fingerprint(image), 'shape': list(image.shape),
           'device': model_device(model), 'parameters': dict(kwargs)}
    LOG.info('[segmentation input] ' + json.dumps(run, sort_keys=True))
    try:
        result = model.eval(image, **kwargs)
    except ValueError as exc:
        message = str(exc)
        if 'broadcast' not in message or 'shape' not in message:
            raise
        LOG.warning(f'Omnipose shape recovery: native-grid resampling; diameter={diameter}; {message}')
        kwargs['resample'] = True
        result = model.eval(image, **kwargs)
    mask = result[0] if isinstance(result, tuple) else result
    mask = np.asarray(mask)
    if mask.shape != image.shape[:2] or not np.issubdtype(mask.dtype, np.integer) or (mask < 0).any():
        raise ValueError(f'Invalid segmentation mask {mask.shape}; expected integer labels at {image.shape[:2]}.')
    run['parameters'] = dict(kwargs)
    run['cells'] = int(np.count_nonzero(np.unique(mask)))
    run['mask_sha256'] = hashlib.sha256(np.ascontiguousarray(mask, dtype=np.int64).tobytes()).hexdigest()
    global _LAST_RESULT
    _LAST_RESULT = run
    LOG.info('[segmentation result] ' + json.dumps(run, sort_keys=True))
    return mask
