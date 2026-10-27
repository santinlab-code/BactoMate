"""Exercise ND2 conversion through real TIFF writes with a synthetic ND2 reader."""
from contextlib import contextmanager
from itertools import product
from types import SimpleNamespace

import dask.array as da
import numpy as np
import pytest
import tifffile

from bactomate.scripts import convert_nd2_to_tif as converter
from bactomate.modules.tiff_metadata import _nd2_frame_interval_from_frame_metadata


def install_reader(monkeypatch, tmp_path, axes='TPCZYX', *, positions=3, times=2, channels=2, z=2):
    sizes = dict(T=times, P=positions, C=channels, Z=z, Y=24, X=25)
    canonical = np.zeros(tuple(sizes.values()), dtype=np.uint16)
    for t, p, c, zi in product(range(times), range(positions), range(channels), range(z)):
        canonical[t, p, c, zi] = 1000*p + 100*t + 10*c + zi
    base_axes = list(sizes)
    data = canonical
    for axis in list(base_axes):
        if axis not in axes:
            assert sizes[axis] == 1
            data = np.take(data, 0, axis=base_axes.index(axis))
            base_axes.remove(axis)
    data = data.transpose([base_axes.index(axis) for axis in axes])
    reader = SimpleNamespace(
        sizes={axis: sizes[axis] for axis in axes},
        metadata=SimpleNamespace(channels=[SimpleNamespace(channel=SimpleNamespace(name=name))
                                          for name in ['Phase', 'GFP'][:channels]]),
        to_dask=lambda: da.from_array(data, chunks=tuple(1 if a not in 'YX' else sizes[a] for a in axes)),
    )
    @contextmanager
    def open_reader(path):
        yield reader
    monkeypatch.setattr(converter.nd2, 'ND2File', open_reader)
    monkeypatch.setattr(converter, 'read_metadata_from_path', lambda path: {})
    monkeypatch.setattr(converter, 'read_calibration_from_path', lambda path: (0.108, 2.0))
    path = tmp_path / 'sample.nd2'
    path.touch()
    return path, canonical, reader


@pytest.mark.parametrize('axes', ['TPCZYX', 'PTZCYX', 'CPTZYX'])
@pytest.mark.parametrize('projection', [False, True])
def test_all_positions_and_channels_keep_time_and_calibration(monkeypatch, tmp_path, axes, projection):
    path, expected, _ = install_reader(monkeypatch, tmp_path, axes)
    converter.convert_nd2_to_tif(path, max_z_projection=projection, fi_channel_indices=[1])
    files = list((tmp_path / 'Tif_files').glob('*.tif'))
    assert len(files) == 6
    for p in range(3):
        for c, tag in enumerate(['phase', 'fi_GFP']):
            out = tmp_path / 'Tif_files' / f'sample_XY{p+1:03d}_{tag}.tif'
            np.testing.assert_array_equal(tifffile.imread(out), expected[:, p, c, int(projection)])
            with tifffile.TiffFile(out) as tif:
                assert tif.series[0].axes == 'TYX'
                assert tif.imagej_metadata['finterval'] == 120.0
                assert f'XY position: {p+1} of 3' in tif.imagej_metadata['Info']
                resolution = tif.pages[0].tags['XResolution'].value
                assert tif.pages[0].tags['ResolutionUnit'].value == 3  # centimetres
                assert 10000 * resolution[1] / resolution[0] == pytest.approx(0.108)


@pytest.mark.parametrize('axes,positions,times,channels,z', [
    ('PCYX', 3, 1, 2, 1), ('PYX', 3, 1, 1, 1),
    ('TPYX', 3, 2, 1, 1), ('TCYX', 1, 2, 2, 1),
    ('YX', 1, 1, 1, 1), ('TPZCYX', 1, 2, 2, 1),
])
def test_singleton_and_missing_axes(monkeypatch, tmp_path, axes, positions, times, channels, z):
    path, expected, _ = install_reader(monkeypatch, tmp_path, axes, positions=positions,
                                       times=times, channels=channels, z=z)
    converter.convert_nd2_to_tif(path, max_frames=1, fi_channel_indices=[1])
    files = list((tmp_path / 'Tif_files').glob('*.tif'))
    assert len(files) == positions * channels
    for p in range(positions):
        stem = 'sample' + (f'_XY{p+1:03d}' if positions > 1 else '')
        for c in range(channels):
            tag = ['_phase', '_fi_GFP'][c] if channels > 1 else ''
            np.testing.assert_array_equal(tifffile.imread(tmp_path/'Tif_files'/f'{stem}{tag}.tif'),
                                          expected[0, p, c, 0])


def test_combined_channels_selected_frame_z_and_crop(monkeypatch, tmp_path):
    path, expected, _ = install_reader(monkeypatch, tmp_path)
    converter.convert_nd2_to_tif(path, separate_channels=False, single_frame=2,
                                 z_slice=2, crop_roi=(1, 2, 20, 22))
    for p in range(3):
        out = tmp_path/'Tif_files'/f'sample_XY{p+1:03d}_f2.tif'
        np.testing.assert_array_equal(tifffile.imread(out), expected[1, p, :, 1, 2:22, 1:20])


def test_corrections_run_separately_for_each_position(monkeypatch, tmp_path):
    path, expected, _ = install_reader(monkeypatch, tmp_path)
    drift_inputs, bleach_inputs = [], []
    def drift(data, **kwargs):
        drift_inputs.append(data.copy())
        return data
    def bleach(data, **kwargs):
        bleach_inputs.append((data.copy(), kwargs['channel_indices']))
        return data
    monkeypatch.setattr(converter, 'drift_correct_stack', drift)
    monkeypatch.setattr(converter, 'bleach_correct_stack', bleach)
    converter.convert_nd2_to_tif(path, channel_index=1, drift_correct=True,
                                 bleach_correct=True, bleach_channel_indices=[1])
    assert len(drift_inputs) == len(bleach_inputs) == 3
    for p in range(3):
        np.testing.assert_array_equal(drift_inputs[p], expected[:, p, 1:2, 0])
        assert bleach_inputs[p][1] == [0]
        np.testing.assert_array_equal(tifffile.imread(tmp_path/'Tif_files'/f'sample_XY{p+1:03d}_GFP.tif'),
                                      expected[:, p, 1, 0])


def test_bad_axis_fails_instead_of_reporting_success(monkeypatch, tmp_path):
    path, _, reader = install_reader(monkeypatch, tmp_path)
    reader.sizes['unknown'] = 2
    with pytest.raises(RuntimeError, match='sample.nd2'):
        converter.convert_nd2_to_tif(path)
    assert not list((tmp_path/'Tif_files').glob('*.tif'))


@pytest.mark.parametrize('axes', ['TPZ', 'PTZ', 'ZPT'])
def test_time_interval_compares_same_position_and_z(axes):
    sizes = dict(T=3, P=3, Z=2)
    loops = [dict(zip(axes, indices)) for indices in product(*(range(sizes[a]) for a in axes))]
    def frame_metadata(i):
        coords = loops[i]
        time = coords['T']*120000 + coords['P']*1000 + coords['Z']*50
        return SimpleNamespace(channels=[SimpleNamespace(time=SimpleNamespace(relativeTimeMs=time))])
    reader = SimpleNamespace(sizes=sizes, loop_indices=loops, frame_metadata=frame_metadata)
    assert _nd2_frame_interval_from_frame_metadata(reader) == 2.0


def test_metadata_reports_xy_count(monkeypatch, tmp_path):
    from bactomate.modules.tiff_metadata import read_metadata_from_path
    path, _, reader = install_reader(monkeypatch, tmp_path)
    reader.shape = tuple(reader.sizes.values())
    assert read_metadata_from_path(path)['position_count'] == 3


def test_preview_loads_only_first_position_with_correct_axes(monkeypatch, tmp_path):
    from unittest.mock import Mock
    from bactomate.gui.tabs.file_conversion import ND2ConversionTab
    path, expected, reader = install_reader(monkeypatch, tmp_path)
    reader.shape = tuple(reader.sizes.values())
    reader.asarray = Mock(side_effect=lambda position: expected[:, position:position+1])
    tab = SimpleNamespace(_show_file_conversion_preview=Mock())
    ND2ConversionTab._preview_nd2(tab, file_path=path)
    reader.asarray.assert_called_once_with(position=0)
    args = tab._show_file_conversion_preview.call_args.kwargs
    assert args['nd2_axis_keys'] == ('T', 'C', 'Z', 'Y', 'X')
    np.testing.assert_array_equal(args['all_frames'], expected[:, 0])
