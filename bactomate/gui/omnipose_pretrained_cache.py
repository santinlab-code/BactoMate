"""
BactoMate-managed cache for built-in Omnipose checkpoints (Option A).

Upstream cellpose_omni downloads to ~/.cellpose/models by default. We mirror each
built-in model into get_omnipose_pretrained_cache_dir() after first resolution so
all BactoMate-owned weights live under one app tree (alongside omnipose_user_models).

Flow: if file exists in BactoMate cache → use it; else call cellpose_omni.model_path
(which may download to ~/.cellpose) → copy into BactoMate cache → return BactoMate path.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError

from bactomate.gui.paths import get_omnipose_pretrained_cache_dir

# Checkpoints shipped with this custom branch. Never silently accept another
# file under the same built-in name, or replace a user's different weights.
BUILTIN_SHA256 = {
    'bact_phase_omni': 'a34cf4b379f207b5f450377833ed8d95927a45ddcd436aabcb7189f2ef25d07c',
    'bact_fluor_omni': '49c849779b205c00193ab29905da8f2b999245467dbf174a9c9dcb5302188c6b',
}


def validate_builtin_checkpoint(path: Path, model_type: str, model_index: int = 0) -> Path:
    from bactomate.modules.segmentation_runtime import file_fingerprint
    expected = BUILTIN_SHA256.get(model_type) if model_index == 0 else None
    if expected and file_fingerprint(path)['sha256'] != expected:
        raise RuntimeError(
            f'{model_type}: checkpoint differs from the shared Mac/Windows baseline. '
            f'Keep a copy of {path} and restore the checkpoint shipped with this branch. '
            'Different weights must be loaded explicitly as a user model.')
    return path.resolve()


def builtin_checkpoint_basename(model_type: str, model_index: int = 0, use_torch: bool = True) -> str:
    """Same naming convention as cellpose_omni (e.g. bact_phase_omnitorch_0)."""
    torch_str = "torch" if use_torch else ""
    return f"{model_type}{torch_str}_{model_index}"


def bactomate_builtin_checkpoint_path(model_type: str, model_index: int = 0, use_torch: bool = True) -> Path:
    """Path where we store the mirrored built-in checkpoint."""
    name = builtin_checkpoint_basename(model_type, model_index, use_torch)
    return get_omnipose_pretrained_cache_dir() / name


def _upstream_builtin_path_after_download(model_type: str, model_index: int = 0) -> Path:
    """
    Resolve built-in weights via cellpose_omni (may download to ~/.cellpose/models).
    Handles HTTP 404 by trying cellpose.org model URL (same as batch_process_tiff_sequence).
    """
    from cellpose_omni.models import MODEL_DIR, model_path

    torch_str = "torch"
    basename = f"{model_type}{torch_str}_{model_index}"
    cache_model_file = Path(MODEL_DIR) / basename

    try:
        upstream_str = model_path(model_type, model_index, True)
    except HTTPError as e:
        if e.code != 404:
            raise
        if cache_model_file.is_file() and cache_model_file.stat().st_size > 0:
            return cache_model_file.resolve()
        import cellpose_omni.models as models_module
        original_url = getattr(models_module, "_MODEL_URL", None)
        if original_url and "github" in str(original_url):
            models_module._MODEL_URL = "https://www.cellpose.org/models"
            try:
                upstream_str = model_path(model_type, model_index, True)
            finally:
                if original_url:
                    models_module._MODEL_URL = original_url
        else:
            raise FileNotFoundError(
                f"Model {model_type!r} not available (404) and no cellpose.org fallback URL configured."
            ) from e
    if not upstream_str:
        raise FileNotFoundError(f"model_path returned empty path for {model_type!r}")
    upstream = Path(upstream_str).resolve()
    if not upstream.is_file() or upstream.stat().st_size == 0:
        raise FileNotFoundError(f"Built-in model not available after download: {upstream}")
    return upstream


def ensure_builtin_in_bactomate_cache(model_type: str, model_index: int = 0, use_torch: bool = True) -> Path:
    """
    Return path to the built-in model in BactoMate's pretrained cache, populating it if needed.

    Raises:
        FileNotFoundError: if upstream download did not produce a file.
        RuntimeError: on other fatal errors from upstream.
    """
    if not model_type or not str(model_type).strip():
        raise ValueError("model_type is required")

    dest = bactomate_builtin_checkpoint_path(model_type, model_index, use_torch)
    if dest.is_file() and dest.stat().st_size > 0:
        return validate_builtin_checkpoint(dest, model_type, model_index)

    upstream = _upstream_builtin_path_after_download(model_type, model_index)
    validate_builtin_checkpoint(upstream, model_type, model_index)

    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        if upstream.resolve() != dest.resolve():
            shutil.copy2(upstream, dest)
    except OSError:
        # If copy fails (e.g. disk full), still allow using upstream this session
        return upstream

    if not dest.is_file() or dest.stat().st_size == 0:
        return upstream
    return validate_builtin_checkpoint(dest, model_type, model_index)


def clear_bactomate_builtin_cache_entry(model_type: str, model_index: int = 0, use_torch: bool = True) -> None:
    """Remove one mirrored file so the next run re-copies from upstream."""
    p = bactomate_builtin_checkpoint_path(model_type, model_index, use_torch)
    try:
        if p.is_file():
            p.unlink()
    except OSError:
        pass


def try_get_bactomate_cached_builtin(model_type: str, model_index: int = 0, use_torch: bool = True) -> Optional[Path]:
    """Return BactoMate cache path if it exists and is non-empty; else None."""
    p = bactomate_builtin_checkpoint_path(model_type, model_index, use_torch)
    if p.is_file() and p.stat().st_size > 0:
        return p.resolve()
    return None
