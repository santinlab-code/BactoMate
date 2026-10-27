#!/usr/bin/env python3
"""
Script to convert ND2 microscopy files to multi-page TIFF files.
Extracts frames 1-150 from each ND2 file and saves them as TIFF files.
"""

import argparse
from pathlib import Path
from typing import Optional, Tuple, List

import numpy as np
import nd2
import tifffile
from scipy.ndimage import shift
from skimage.registration import phase_cross_correlation
from skimage.exposure import match_histograms

try:
    from bactomate.modules.conversion_crop import apply_yx_crop, parse_crop_cli_args
    from bactomate.modules.tiff_metadata import (
        read_calibration_from_path,
        read_metadata_from_path,
        build_acquisition_info_string,
    )
except ImportError:
    apply_yx_crop = None
    parse_crop_cli_args = None
    read_calibration_from_path = None
    read_metadata_from_path = None
    build_acquisition_info_string = None


def drift_correct_stack(frames: np.ndarray, reference_frame: int = 0, method: str = 'frame_by_frame') -> np.ndarray:
    """
    Correct for X,Y drift in a time series using phase cross-correlation.
    
    Args:
        frames: Array of shape (T, Y, X) or (T, C, Y, X)
        reference_frame: Index of reference frame (for 'all_to_first' method, default: 0)
        method: 'frame_by_frame' (recommended, more robust) or 'all_to_first' (no error accumulation)
        
    Returns:
        Drift-corrected frames
    """
    if method == 'all_to_first':
        # Original method: align all frames to first frame
        if len(frames.shape) == 3:
            # Single channel: TYX
            corrected = np.zeros_like(frames)
            reference = frames[reference_frame]
            
            for t in range(frames.shape[0]):
                if t == reference_frame:
                    corrected[t] = frames[t]
                else:
                    # Calculate shift using phase cross-correlation
                    shift_result = phase_cross_correlation(
                        reference,
                        frames[t],
                        upsample_factor=10
                    )
                    # shift_result is a tuple: (shift, error, phasediff)
                    shift_y, shift_x = shift_result[0]
                    
                    # Apply shift
                    corrected[t] = shift(frames[t], shift=(shift_y, shift_x), mode='constant', cval=0)
            
            return corrected
        
        elif len(frames.shape) == 4:
            # Multi-channel: TCYX
            corrected = np.zeros_like(frames)
            reference = frames[reference_frame]
            
            for t in range(frames.shape[0]):
                if t == reference_frame:
                    corrected[t] = frames[t]
                else:
                    # Correct each channel independently
                    for c in range(frames.shape[1]):
                        # Use first channel as reference for shift calculation
                        if c == 0:
                            shift_result = phase_cross_correlation(
                                reference[0],
                                frames[t, 0],
                                upsample_factor=10
                            )
                            # shift_result is a tuple: (shift, error, phasediff)
                            shift_y, shift_x = shift_result[0]
                        
                        # Apply same shift to all channels
                        corrected[t, c] = shift(
                            frames[t, c],
                            shift=(shift_y, shift_x),
                            mode='constant',
                            cval=0
                        )
            
            return corrected
    
    elif method == 'frame_by_frame':
        # Frame-by-frame: align each frame to previous frame (more robust for large drifts)
        if len(frames.shape) == 3:
            # Single channel: TYX
            corrected = np.zeros_like(frames)
            corrected[0] = frames[0]  # First frame unchanged
            
            # Track cumulative shifts for potential smoothing (not used yet, but could be added)
            cumulative_shift_y = 0.0
            cumulative_shift_x = 0.0
            
            for t in range(1, frames.shape[0]):
                # Align to previous corrected frame
                shift_result = phase_cross_correlation(
                    corrected[t - 1],
                    frames[t],
                    upsample_factor=10
                )
                # shift_result is a tuple: (shift, error, phasediff)
                shift_y, shift_x = shift_result[0]
                
                # Update cumulative shifts
                cumulative_shift_y += shift_y
                cumulative_shift_x += shift_x
                
                # Apply shift
                corrected[t] = shift(frames[t], shift=(shift_y, shift_x), mode='constant', cval=0)
            
            return corrected
        
        elif len(frames.shape) == 4:
            # Multi-channel: TCYX
            corrected = np.zeros_like(frames)
            corrected[0] = frames[0]  # First frame unchanged
            
            for t in range(1, frames.shape[0]):
                # Use first channel for shift calculation
                shift_result = phase_cross_correlation(
                    corrected[t - 1, 0],
                    frames[t, 0],
                    upsample_factor=10
                )
                # shift_result is a tuple: (shift, error, phasediff)
                shift_y, shift_x = shift_result[0]
                
                # Apply same shift to all channels
                for c in range(frames.shape[1]):
                    corrected[t, c] = shift(
                        frames[t, c],
                        shift=(shift_y, shift_x),
                        mode='constant',
                        cval=0
                    )
            
            return corrected
    
    else:
        raise ValueError(f"Unknown drift correction method: {method}. Use 'frame_by_frame' or 'all_to_first'")
    
    raise ValueError(f"Unexpected frame shape: {frames.shape}")


def bleach_correct_stack(
    frames: np.ndarray,
    method: str = 'exponential',
    channel_indices: Optional[List[int]] = None,
) -> np.ndarray:
    """
    Correct for photobleaching in fluorescence time series.
    Inspired by Fiji CorrectBleach plugin (https://github.com/fiji/CorrectBleach).

    Which channels: For multi-channel (T, C, Y, X), if channel_indices is given then
    only those channel indices are corrected; others are left unchanged. If None,
    all channels are corrected.

    Args:
        frames: Array of shape (T, Y, X) or (T, C, Y, X)
        method: One of:
            - 'exponential': Intensity preservation. I(t) = I0*exp(-t/τ), scale so
              mean intensity matches first frame (like Fiji "Exponential with offset").
            - 'linear': Linear decay fit, then scale to first frame.
            - 'histogram_matching': Match each frame's histogram to frame 0 (like
              Fiji "Histogram Matching"). Good for segmentation; not for quantification.
            - 'per_frame_minmax': Per-frame min-max stretch. Each frame is scaled so
              its minimum maps to 0 and maximum to the max of the input dtype (e.g.
              255 for uint8, 65535 for uint16). Bit depth and dtype are unchanged;
              output is still grayscale (no RGB). Good for visualization only.

    Returns:
        Bleach-corrected frames (same shape and dtype as input where possible).
    """
    if len(frames.shape) == 3:
        # Single channel: TYX
        if method == 'per_frame_minmax':
            corrected = np.zeros_like(frames, dtype=np.float64)
            out_max = (np.iinfo(frames.dtype).max if np.issubdtype(frames.dtype, np.integer) else 1.0)
            for t in range(frames.shape[0]):
                fm = frames[t].astype(np.float64)
                lo, hi = fm.min(), fm.max()
                if hi > lo:
                    corrected[t] = (fm - lo) / (hi - lo) * out_max
                else:
                    corrected[t] = fm
            return np.clip(corrected, 0, out_max).astype(frames.dtype)
        if method == 'histogram_matching':
            corrected = frames.copy()
            ref = frames[0]
            for t in range(1, frames.shape[0]):
                corrected[t] = match_histograms(frames[t], ref, channel_axis=None).astype(frames.dtype)
            return corrected
        # exponential or linear
        mean_intensities = np.mean(frames, axis=(1, 2))
        if method == 'exponential':
            I0 = mean_intensities[0]
            I_final = mean_intensities[-1]
            if I_final > 0 and I0 > I_final:
                tau = -len(mean_intensities) / np.log(I_final / I0)
            else:
                tau = len(mean_intensities) * 10
            t = np.arange(len(mean_intensities))
            expected = I0 * np.exp(-t / tau)
            correction_factors = I0 / np.maximum(expected, 1e-10)
        else:
            I0 = mean_intensities[0]
            I_final = mean_intensities[-1]
            if I_final < I0:
                slope = (I0 - I_final) / len(mean_intensities)
                expected = I0 - slope * np.arange(len(mean_intensities))
                correction_factors = I0 / np.maximum(expected, 1e-10)
            else:
                correction_factors = np.ones(len(mean_intensities))
        corrected = frames.copy()
        for t in range(frames.shape[0]):
            corrected[t] = (frames[t].astype(np.float64) * correction_factors[t]).astype(frames.dtype)
        return corrected

    if len(frames.shape) == 4:
        # Multi-channel: TCYX - correct only channels in channel_indices (or all if None)
        corrected = frames.copy()
        channels_to_correct = range(frames.shape[1]) if channel_indices is None else channel_indices
        for c in channels_to_correct:
            if c < 0 or c >= frames.shape[1]:
                continue
            channel_frames = frames[:, c, :, :]
            corrected[:, c, :, :] = bleach_correct_stack(channel_frames, method)
        return corrected

    raise ValueError(f"Unexpected frame shape: {frames.shape}")


def _sanitize_channel_name_for_filename(name: str) -> str:
    """Replace characters unsuitable for filenames with underscore."""
    from bactomate.modules.conversion_channel_names import sanitize_channel_name_for_filename

    return sanitize_channel_name_for_filename(name)


def _nd2_channel_output_filename(
    stem: str,
    channel_name: str,
    *,
    ch_idx: int,
    fi_set: set,
    foci_set: set,
    phase_used: bool,
) -> tuple[str, bool]:
    """Role-tagged TIFF name for one ND2 channel (no bare ``{stem}_{name}.tif``)."""
    from bactomate.modules.conversion_channel_names import split_channel_output_name

    return split_channel_output_name(
        stem,
        channel_name,
        in_fi=ch_idx in fi_set,
        in_foci=ch_idx in foci_set,
        phase_used=phase_used,
    )


def _nd2_position_tcyx(source, sizes, position, frame_start, frame_count,
                       *, max_z_projection=False, z_slice=None):
    """Load one XY position/range as TCYX using ND2's authoritative axis names."""
    if tuple(source.shape) != tuple(sizes.values()):
        raise ValueError(f"ND2 shape {source.shape} does not match axes {sizes}")
    index = []
    remaining = []
    for axis, size in sizes.items():
        if axis == 'P':
            index.append(position)
        elif axis == 'Z' and not max_z_projection:
            z = int(z_slice or 1) - 1
            if not 0 <= z < size:
                print(f"  Warning: Z-slice {z + 1} out of range; using Z=1")
                z = 0
            index.append(z)
        elif axis not in ('T', 'C', 'Z', 'Y', 'X'):
            if size != 1:
                raise ValueError(f"Unsupported ND2 axis {axis} with size {size}")
            index.append(0)
        else:
            index.append(slice(frame_start, frame_start + frame_count) if axis == 'T' else slice(None))
            remaining.append(axis)
    selected = source[tuple(index)]
    if 'Z' in remaining:
        selected = selected.max(axis=remaining.index('Z'))
        remaining.remove('Z')
    data = np.asarray(selected)
    for axis in 'TC':
        if axis not in remaining:
            data = np.expand_dims(data, axis=0)
            remaining.insert(0, axis)
    if set(remaining) != set('TCYX') or not data.size:
        raise ValueError(f"Invalid ND2 image axes/shape: {remaining}, {data.shape}")
    return data.transpose([remaining.index(axis) for axis in 'TCYX'])


def convert_nd2_to_tif(
    input_path: Path,
    output_dir: Optional[Path] = None,
    max_frames: int = 150,
    single_frame: Optional[int] = None,  # If set, extract only this time point (1-based); overrides max_frames
    separate_channels: bool = True,  # Default to True for multi-channel compatibility
    channel_index: Optional[int] = None,
    drift_correct: bool = False,
    bleach_correct: bool = False,
    bleach_method: str = 'exponential',  # exponential | linear | histogram_matching | per_frame_minmax
    bleach_channel_indices: Optional[List[int]] = None,  # If set, only these channel indices get correction; else all
    pixel_size: Optional[float] = None,  # Pixel size in µm to save in metadata
    time_per_frame_min: Optional[float] = None,  # Time per frame in minutes (for speed calibration); saved as finterval
    channel_names_override: Optional[List[str]] = None,  # Optional user-edited channel names for output TIFFs
    max_z_projection: bool = False,  # Max intensity projection across Z-slices
    z_slice: Optional[int] = None,  # If max_z_projection is False and Z>1, pick this 1-based slice; default is Z=1
    fi_channel_indices: Optional[List[int]] = None,  # Channel indices (0-based) to save with _fi in filename for Analyze FI batch
    foci_channel_indices: Optional[List[int]] = None,  # Channel indices to save with _foci in filename for Analyze Masks foci analysis
    crop_roi: Optional[Tuple[int, int, int, int]] = None,  # Optional native Y/X crop (x0, y0, x1, y1)
) -> None:
    """
    Convert every XY position to TIFF, with _XY001 etc. for multiposition files.
    
    Args:
        input_path: Path to directory containing ND2 files or a single ND2 file
        output_dir: Optional output directory. If None, uses 'Tif_files' in input directory (reused if it exists)
        max_frames: Maximum number of frames to extract (default: 150)
        fi_channel_indices: If set, channels at these indices get '_fi' in filename (e.g. stem_fi.tif) for batch FI pairing
        foci_channel_indices: If set, channels at these indices get '_foci' in filename for Analyze Masks foci analysis
    """
    input_path = Path(input_path)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Path does not exist: {input_path}")
    
    # Determine ND2 files to process
    if input_path.is_file() and input_path.suffix.lower() == '.nd2':
        nd2_files = [input_path]
        base_dir = input_path.parent
    elif input_path.is_dir():
        nd2_files = list(input_path.glob('*.nd2')) + list(input_path.glob('*.ND2'))
        base_dir = input_path
    else:
        raise ValueError(f"Path must be a directory or an ND2 file: {input_path}")
    
    if not nd2_files:
        print(f"No ND2 files found in {input_path}")
        return
    
    # Create output directory: always use single folder "Tif_files" if not specified
    if output_dir is None:
        output_dir = base_dir / "Tif_files"
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Found {len(nd2_files)} ND2 file(s) to process")
    print(f"Output directory: {output_dir}")
    
    failed_files = []
    # Process each ND2 file
    for nd2_file in nd2_files:
        print(f"\nProcessing: {nd2_file.name}")
        acquisition_meta = read_metadata_from_path(nd2_file) if read_metadata_from_path else {}

        # Use same calibration extraction as GUI (tiff_metadata) so pixel size and time per frame match the log
        extracted_pixel_size = pixel_size
        extracted_time_per_frame = time_per_frame_min
        if read_calibration_from_path is not None:
            file_ps, file_tp = read_calibration_from_path(nd2_file)
            if extracted_pixel_size is None and file_ps > 0:
                extracted_pixel_size = float(file_ps)
                print(f"  Calibration (from file): pixel size {extracted_pixel_size:.4f} µm")
            if extracted_time_per_frame is None and file_tp > 0:
                extracted_time_per_frame = float(file_tp)
                print(f"  Calibration (from file): time per frame {extracted_time_per_frame:.4f} min")
        
        try:
            # Open ND2 file
            with nd2.ND2File(nd2_file) as nd2_reader:
                # Get dimension information
                sizes = nd2_reader.sizes
                dims = nd2_reader.sizes.keys() if hasattr(nd2_reader.sizes, 'keys') else []
                
                # Get dimensions
                num_time = sizes.get('T', 1)
                num_channels = sizes.get('C', 1)
                num_z = sizes.get('Z', 1)
                
                # Get channel names if available
                channel_names = []
                if hasattr(nd2_reader, 'metadata') and nd2_reader.metadata:
                    # Try to get channel names from metadata
                    try:
                        meta = nd2_reader.metadata
                        # Metadata is an object, not a dict - access channels attribute
                        if hasattr(meta, 'channels') and meta.channels:
                            channel_names = [ch.channel.name if hasattr(ch, 'channel') and hasattr(ch.channel, 'name') 
                                           else f'Channel_{i+1}' 
                                           for i, ch in enumerate(meta.channels)]
                    except Exception:
                        pass
                
                # If channel names not found, create default names
                if not channel_names or len(channel_names) != num_channels:
                    channel_names = [f'Channel_{i+1}' for i in range(num_channels)]
                if channel_names_override:
                    cleaned_names = [str(name).strip() for name in channel_names_override if str(name).strip()]
                    if len(cleaned_names) == num_channels:
                        channel_names = cleaned_names
                        print(f"  Using edited channel names: {', '.join(channel_names)}")
                    else:
                        print(
                            f"  Warning: Ignoring edited channel names "
                            f"({len(cleaned_names)} names for {num_channels} channels)"
                        )
                
                print(f"  Dimensions: T={num_time}, C={num_channels}, Z={num_z}")
                if num_channels > 1:
                    print(f"  Channels: {', '.join(channel_names)}")
                
                # Determine number of frames to extract: single frame (1-based) or first N
                from bactomate.modules.conversion_channel_names import conversion_frame_stem_suffix

                if single_frame is not None:
                    frame_idx_0 = max(0, min(single_frame - 1, num_time - 1))
                    frames_to_extract = 1
                    # Keep suffix based on requested 1-based frame (same as historical ND2 naming).
                    frame_suffix = conversion_frame_stem_suffix(
                        frame_start_0based=max(0, int(single_frame) - 1),
                        explicit_single_frame=True,
                    )
                    print(f"  Extracting single frame only: {single_frame} (1-based)")
                else:
                    frame_idx_0 = 0
                    frames_to_extract = min(max_frames, num_time)
                    frame_suffix = conversion_frame_stem_suffix(
                        frame_start_0based=0,
                        explicit_single_frame=False,
                    )
                    print(f"  Extracting frames 1-{frames_to_extract}")
                
                # Fallback: extract pixel size from ND2 metadata if still not set
                if extracted_pixel_size is None:
                    try:
                        if hasattr(nd2_reader, 'metadata') and nd2_reader.metadata:
                            meta = nd2_reader.metadata
                            if hasattr(meta, 'channels') and meta.channels:
                                first_channel = meta.channels[0]
                                if hasattr(first_channel, 'volume') and first_channel.volume:
                                    vol = first_channel.volume
                                    if hasattr(vol, 'axesCalibration') and vol.axesCalibration and len(vol.axesCalibration) >= 2:
                                        extracted_pixel_size = float(vol.axesCalibration[0])
                                        print(f"  Extracted pixel size: {extracted_pixel_size:.4f} µm")
                    except Exception as e:
                        print(f"  Warning: Could not extract pixel size: {e}")

                # Fallback: extract time per frame from ND2 (TimeLoopParams.periodMs or NETimeLoopParams.periods[].periodMs)
                if extracted_time_per_frame is None:
                    try:
                        if hasattr(nd2_reader, 'experiment') and nd2_reader.experiment and hasattr(nd2_reader.experiment, 'loops'):
                            for loop in nd2_reader.experiment.loops:
                                params = getattr(loop, 'parameters', None)
                                if params is None:
                                    continue
                                period_ms = getattr(params, 'periodMs', None)
                                if period_ms is not None and float(period_ms) > 0:
                                    extracted_time_per_frame = float(period_ms) / 60000.0  # ms -> min
                                    print(f"  Extracted time per frame: {extracted_time_per_frame:.6f} min ({float(period_ms)/1000:.4f} s)")
                                    break
                                periods = getattr(params, 'periods', None)
                                if periods and len(periods) > 0:
                                    p0 = periods[0]
                                    period_ms = getattr(p0, 'periodMs', None)
                                    if period_ms is not None and float(period_ms) > 0:
                                        extracted_time_per_frame = float(period_ms) / 60000.0
                                        print(f"  Extracted time per frame: {extracted_time_per_frame:.6f} min ({float(period_ms)/1000:.4f} s)")
                                        break
                                period_sec = getattr(params, 'period', None)
                                if period_sec is not None and float(period_sec) > 0:
                                    extracted_time_per_frame = float(period_sec) / 60.0
                                    print(f"  Extracted time per frame: {extracted_time_per_frame:.4f} min")
                                    break
                        # Fallback: compute from frame_metadata() timestamps (relativeTimeMs)
                        if (extracted_time_per_frame is None or extracted_time_per_frame <= 0) and num_time >= 2 and hasattr(nd2_reader, 'frame_metadata'):
                            from bactomate.modules.tiff_metadata import _nd2_frame_interval_from_frame_metadata
                            extracted_time_per_frame = _nd2_frame_interval_from_frame_metadata(nd2_reader)
                    except Exception:
                        pass
                
                # Slice by named axes before loading: positions must never become
                # timepoints or channels, even when dimensions have equal lengths.
                source = nd2_reader.to_dask()
                num_positions = int(sizes.get('P', 1))
                for position in range(num_positions):
                    print(f"  Position XY {position + 1}/{num_positions}")
                    all_frames = _nd2_position_tcyx(
                        source, sizes, position, frame_idx_0, frames_to_extract,
                        max_z_projection=max_z_projection, z_slice=z_slice,
                    )
                    position_suffix = f"_XY{position + 1:03d}" if num_positions > 1 else ""
                    output_stem = nd2_file.stem + position_suffix + frame_suffix
                    selected_channels = list(range(num_channels))
                    if channel_index is not None:
                        selected = channel_index if 0 <= channel_index < num_channels else 0
                        selected_channels = [selected]
                        all_frames = all_frames[:, selected:selected + 1]

                    # Corrections and crop apply independently to each XY position.
                    if drift_correct:
                        print("  Applying drift correction...")
                        all_frames = drift_correct_stack(all_frames, method='frame_by_frame')
                    if crop_roi is not None:
                        if apply_yx_crop is None:
                            raise RuntimeError("Crop support is unavailable")
                        all_frames = apply_yx_crop(all_frames, crop_roi)
                    if bleach_correct:
                        correction_channels = bleach_channel_indices
                        if correction_channels is not None:
                            correction_channels = [
                                i for i, ch in enumerate(selected_channels)
                                if ch in correction_channels
                            ]
                        all_frames = bleach_correct_stack(
                            all_frames, method=bleach_method,
                            channel_indices=correction_channels,
                        )

                    def acquisition_info(channel_name=None):
                        info = (build_acquisition_info_string(
                            acquisition_meta, channel_name=channel_name, source_name=nd2_file.name,
                        ) if build_acquisition_info_string and acquisition_meta else "")
                        if num_positions > 1:
                            info = (info or "") + f"\nXY position: {position + 1} of {num_positions}"
                        return info or None

                    if len(selected_channels) > 1 and not separate_channels:
                        _save_multichannel_tiff_with_metadata(
                            output_dir / (output_stem + '.tif'), all_frames,
                            frames_to_extract, num_channels, channel_names,
                            pixel_size=extracted_pixel_size,
                            time_per_frame_min=extracted_time_per_frame,
                            acquisition_info=acquisition_info(),
                        )
                    else:
                        phase_used = False
                        for local_channel, ch_idx in enumerate(selected_channels):
                            channel_name = channel_names[ch_idx]
                            if channel_index is not None:
                                from bactomate.modules.conversion_channel_names import sanitize_channel_name_for_filename
                                filename = output_stem + '_' + sanitize_channel_name_for_filename(channel_name) + '.tif'
                            elif num_channels > 1:
                                filename, phase_used = _nd2_channel_output_filename(
                                    output_stem, channel_name, ch_idx=ch_idx,
                                    fi_set=set(fi_channel_indices or []),
                                    foci_set=set(foci_channel_indices or []),
                                    phase_used=phase_used,
                                )
                            else:
                                filename = output_stem + '.tif'
                            print(f"    Saving channel {ch_idx + 1}: {channel_name} -> {filename}")
                            _save_tiff_with_metadata(
                                output_dir / filename, all_frames[:, local_channel],
                                frames_to_extract, pixel_size=extracted_pixel_size,
                                time_per_frame_min=extracted_time_per_frame,
                                acquisition_info=acquisition_info(channel_name),
                            )
            
        except Exception as e:
            print(f"  ✗ Error processing {nd2_file.name}: {e}")
            import traceback
            traceback.print_exc()
            failed_files.append(nd2_file.name)
            continue
    
    if failed_files:
        raise RuntimeError("ND2 conversion failed for: " + ", ".join(failed_files))
    print(f"\n✓ Conversion complete!")


def _save_multichannel_tiff_with_metadata(
    output_path: Path,
    frames: np.ndarray,
    num_frames: int,
    num_channels: int,
    channel_names: list,
    pixel_size: Optional[float] = None,
    time_per_frame_min: Optional[float] = None,
    acquisition_info: Optional[str] = None,
) -> None:
    """
    Save multi-channel time series as TIFF with proper metadata.
    Uses OME-TIFF format to properly handle multi-channel time series.
    
    Args:
        output_path: Path to output file
        frames: Array of shape (T, C, Y, X)
        num_frames: Number of time frames
        num_channels: Number of channels
        channel_names: List of channel names
    """
    print(f"    Saving {num_frames} timepoints with {num_channels} channels each")
    
    # Use OME-TIFF format for proper multi-channel time series support
    # OME-TIFF properly handles TCYX dimensions where each timepoint has all channels
    # The format stores it in a way that software can interpret as multi-channel time series
    
    # For multi-channel time series, standard TIFF format limitation:
    # TIFF doesn't support multiple grayscale channels per page (only RGB with 3 channels)
    # So we need to save channels separately but in a way that software can group them
    
    # Option: Save as OME-TIFF which properly handles multi-channel time series
    # However, it still stores as separate pages but with proper metadata
    
    # Better approach: Since TIFF can't have multiple grayscale channels per page,
    # we'll save each channel as a separate file with a naming convention that indicates
    # they belong together. This is the most compatible approach.
    
    # Actually, let's try saving as ImageJ hyperstack format which can handle this
    # by using proper metadata to indicate channels and timepoints
    
    # Save with ImageJ hyperstack metadata
    # Format: We'll save it as a hyperstack where pages are organized as timepoints
    # But since TIFF doesn't support multi-channel grayscale, we need to interleave
    # and use metadata to indicate the structure
    
    # Actually, the best solution for true multi-channel is to save channels separately
    # But since user wants one file, let's use OME-TIFF with proper structure
    # Software like ImageJ/Fiji and ilastik can read OME-TIFF and interpret it correctly
    
    # Save as OME-TIFF with TCYX structure
    # Note: This will create T*C pages, but OME metadata tells software how to interpret it
    metadata = {'axes': 'TCYX'}  # Time, Channel, Y, X
    if pixel_size is not None and float(pixel_size) > 0:
        ps = float(pixel_size)
        metadata['pixelSize'] = ps
        metadata['unit'] = 'um'  # Use 'um' instead of 'µm' for ASCII compatibility
        print(f"    Saving pixel size: {ps:.4f} µm")
    if time_per_frame_min is not None and float(time_per_frame_min) > 0:
        tp_min = float(time_per_frame_min)
        metadata['finterval'] = tp_min * 60.0  # seconds for ImageJ
        print(f"    Saving time per frame: {tp_min:.4f} min ({tp_min * 60:.1f} s)")
    if acquisition_info:
        metadata["Info"] = acquisition_info

    tifffile.imwrite(
        str(output_path),
        frames,
        photometric='minisblack',
        metadata=metadata,
        ome=True,  # Use OME-TIFF format
    )
    
    print(f"    ✓ Saved as OME-TIFF: {num_frames} timepoints × {num_channels} channels")
    print(f"      Note: OME-TIFF stores {num_frames * num_channels} pages but metadata groups them correctly")
    print(f"      Software like ImageJ/Fiji and ilastik will interpret this as {num_frames} timepoints with {num_channels} channels each")


def _save_tiff_with_metadata(
    output_path: Path,
    frames: np.ndarray,
    num_frames: int,
    pixel_size: Optional[float] = None,
    time_per_frame_min: Optional[float] = None,
    acquisition_info: Optional[str] = None,
) -> None:
    """
    Save frames as TIFF with proper time dimension metadata, pixel size, and time per frame.
    
    Args:
        output_path: Path to output file
        frames: Array of frames (should be TYX or YX)
        num_frames: Number of time frames
        pixel_size: Pixel size in µm (optional, will be saved in metadata)
        time_per_frame_min: Time per frame in minutes (optional, saved as finterval for tracking/speed)
        acquisition_info: Optional string (objective, channel, etc.) written to TIFF Info for future reference
    """
    # Check if frames array is empty
    if frames.size == 0:
        raise ValueError(f"Cannot save empty frames array! Shape: {frames.shape}")
    
    # Ensure frames are in correct shape (T, Y, X); accept 4D/5D with singleton C/Z and squeeze
    if len(frames.shape) == 2:
        # Single frame - add time dimension
        frames = frames[np.newaxis, :, :]
    elif len(frames.shape) == 3:
        # Already TYX
        pass
    elif len(frames.shape) == 4:
        # (T, C, Y, X) – take first channel to get TYX
        if frames.shape[1] == 1:
            frames = frames[:, 0, :, :]
        else:
            raise ValueError(f"Unexpected frame shape: {frames.shape}, expected (T, Y, X) or (Y, X) or (T, 1, Y, X)")
    elif len(frames.shape) == 5:
        # (T, C, Z, Y, X) – take first C and Z to get TYX
        if frames.shape[1] == 1 and frames.shape[2] == 1:
            frames = frames[:, 0, 0, :, :]
        else:
            raise ValueError(f"Unexpected frame shape: {frames.shape}, expected (T, Y, X) or (Y, X) or (T, 1, 1, Y, X)")
    else:
        raise ValueError(f"Unexpected frame shape: {frames.shape}, expected (T, Y, X) or (Y, X)")
    
    # Get frame dimensions
    actual_frames, height, width = frames.shape
    
    # Verify we have valid dimensions
    if actual_frames == 0 or height == 0 or width == 0:
        raise ValueError(f"Invalid frame dimensions: {frames.shape}")
    
    print(f"    Debug: Saving frames with shape {frames.shape}, dtype {frames.dtype}, size {frames.size}")
    
    # Save with ImageJ metadata to properly indicate time dimension
    metadata = {
        'axes': 'TYX',  # Time, Y, X (not ZYX)
        'ImageJ': '1.53c',
        'images': actual_frames,
        'slices': 1,  # Only 1 Z-slice
        'frames': actual_frames,  # Number of time frames
        'loop': False,
        'mode': 'grayscale',
    }
    
    # Add pixel size and time per frame to metadata if available (coerce to float for consistent TIFF tags)
    # Note: Use 'um' instead of 'µm' because ImageJ metadata requires ASCII encoding
    # ImageJ expects finterval in seconds (so "Frame interval: X sec" displays correctly)
    resolution = None
    if pixel_size is not None and float(pixel_size) > 0:
        ps = float(pixel_size)
        metadata['pixelSize'] = ps
        metadata['unit'] = 'um'  # Use 'um' instead of 'µm' for ASCII compatibility
        # TIFF Resolution tags (pixels per cm) so ImageJ/Fiji get scale even without parsing ImageDescription
        resolution = (1e4 / ps, 1e4 / ps)  # 1e4 µm = 1 cm
        print(f"    Saving pixel size: {ps:.4f} µm")
    if time_per_frame_min is not None and float(time_per_frame_min) > 0:
        tp_min = float(time_per_frame_min)
        metadata['finterval'] = tp_min * 60.0  # seconds for ImageJ
        print(f"    Saving time per frame: {tp_min:.4f} min ({tp_min * 60:.1f} s)")
    if acquisition_info:
        metadata["Info"] = acquisition_info

    try:
        imwrite_kw = dict(
            photometric='minisblack',
            metadata=metadata,
            imagej=True,
        )
        if resolution is not None:
            imwrite_kw['resolution'] = resolution
            imwrite_kw['resolutionunit'] = 3  # RESUNIT_CENTIMETER
        tifffile.imwrite(
            str(output_path),
            frames,
            **imwrite_kw,
        )
        
        # Verify the file was written correctly
        file_size = output_path.stat().st_size
        if file_size < 100:  # Very small file, likely empty or corrupted
            print(f"    ⚠ Warning: Saved file is very small ({file_size} bytes), may be empty!")
            print(f"    ⚠ Check if frames array was empty or write failed")
        else:
            print(f"    ✓ Saved {actual_frames} frames to {output_path.name} ({file_size:,} bytes)")
    except Exception as e:
        print(f"    ✗ Error writing TIFF file: {e}")
        import traceback
        traceback.print_exc()
        raise


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Convert ND2 microscopy files to multi-page TIFF files (frames 1-150)"
    )
    parser.add_argument(
        'path',
        type=str,
        help='Path to directory containing ND2 files or a single ND2 file'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        default=None,
        help='Output directory (default: "Tif_files" in input directory, reused if it exists)'
    )
    parser.add_argument(
        '-f', '--frames',
        type=int,
        default=150,
        help='Maximum number of frames to extract (default: 150). Ignored when --single-frame is set.'
    )
    parser.add_argument(
        '--single-frame',
        type=int,
        default=None,
        metavar='N',
        help='Extract only this time point (1-based, e.g. 50 = frame 50). All channels of that frame are included. Overrides --frames.'
    )
    parser.add_argument(
        '--separate-channels',
        action='store_true',
        default=True,
        help='Save each channel as a separate file (default: True). Each file will have T pages (timepoints). Note: Standard TIFF cannot store multiple grayscale channels per page, so this is the recommended approach for multi-channel data.'
    )
    parser.add_argument(
        '--combine-channels',
        action='store_true',
        help='Save all channels in one OME-TIFF file (overrides --separate-channels). Note: This will create T*C pages but OME metadata allows software to interpret it as T timepoints with C channels each.'
    )
    parser.add_argument(
        '--channel',
        type=int,
        default=None,
        help='Extract only a specific channel (0-indexed). If not specified, all channels are processed'
    )
    parser.add_argument(
        '--drift-correct',
        action='store_true',
        help='Apply X,Y drift correction using phase cross-correlation (like Fiji Fast4DReg)'
    )
    parser.add_argument(
        '--bleach-correct',
        action='store_true',
        help='Apply photobleaching correction (Fiji CorrectBleach-style). Applied to all channels unless --channel is set.'
    )
    parser.add_argument(
        '--bleach-method',
        type=str,
        choices=['exponential', 'linear', 'histogram_matching', 'per_frame_minmax'],
        default='exponential',
        help='Bleach correction method: exponential (intensity preservation), linear, histogram_matching (Fiji-like), per_frame_minmax (per-frame min-max stretch, preserves bit depth, visualization only)'
    )
    parser.add_argument(
        '--bleach-channels',
        type=int,
        nargs='*',
        default=None,
        metavar='N',
        help='Channel indices (0-based) to apply bleach correction to. If omitted and --bleach-correct is set, all channels are corrected. Example: --bleach-channels 0 2'
    )
    parser.add_argument(
        '--fi-channels',
        type=int,
        nargs='*',
        default=None,
        metavar='N',
        help='Channel indices (0-based) to save with _fi in filename (e.g. stem_fi.tif) for Analyze Masks batch FI pairing. Example: --fi-channels 1'
    )
    parser.add_argument(
        '--foci-channels',
        type=int,
        nargs='*',
        default=None,
        metavar='N',
        help='Channel indices (0-based) to save with _foci in filename for Analyze Masks foci analysis. Example: --foci-channels 1'
    )
    parser.add_argument(
        '--pixel-size',
        type=float,
        default=None,
        help='Pixel size in µm to save in TIFF metadata (if not provided, will try to extract from ND2)'
    )
    parser.add_argument(
        '--time-per-frame',
        type=float,
        default=None,
        metavar='MIN',
        help='Time per frame in minutes to save in TIFF metadata (finterval). If not provided, will try to extract from ND2 experiment loops.'
    )
    parser.add_argument(
        '--channel-names',
        nargs='+',
        default=None,
        metavar='NAME',
        help='Optional edited channel names to use for output filenames and metadata. Count must match channel count.'
    )
    parser.add_argument(
        '--max-z-projection',
        action='store_true',
        help='Apply maximum intensity projection across Z-slices when Z > 1. If not set, only the first Z-slice (Z=1) is used.'
    )
    parser.add_argument(
        '--z-slice',
        type=int,
        default=None,
        metavar='N',
        help='When Z > 1 and --max-z-projection is not set, use this 1-based Z-slice index (e.g. 3). Default: 1.'
    )
    parser.add_argument(
        '--crop',
        type=int,
        nargs=4,
        metavar=('X0', 'Y0', 'X1', 'Y1'),
        default=None,
        help='Optional native-image crop region (x0 y0 x1 y1) applied to every output frame/channel.',
    )
    
    args = parser.parse_args()
    
    # Handle channel options
    separate_channels = args.separate_channels and not args.combine_channels
    crop_roi = None
    if args.crop is not None:
        if parse_crop_cli_args is None:
            print("Error: --crop requires bactomate.modules.conversion_crop")
            return 1
        crop_roi = parse_crop_cli_args(args.crop)
    
    try:
        convert_nd2_to_tif(
            input_path=Path(args.path),
            output_dir=Path(args.output) if args.output else None,
            max_frames=args.frames,
            single_frame=args.single_frame,
            separate_channels=separate_channels,
            channel_index=args.channel,
            drift_correct=args.drift_correct,
            bleach_correct=args.bleach_correct,
            bleach_method=args.bleach_method,
            bleach_channel_indices=args.bleach_channels,
            pixel_size=args.pixel_size,
            time_per_frame_min=args.time_per_frame,
            channel_names_override=args.channel_names,
            max_z_projection=args.max_z_projection,
            z_slice=args.z_slice,
            fi_channel_indices=args.fi_channels,
            foci_channel_indices=args.foci_channels,
            crop_roi=crop_roi,
        )
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())

