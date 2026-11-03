"""
Exit 0 when the pinned torch/vision/audio releases and build tags are compatible.
Exit 1 when a reinstall is needed (mixed CUDA builds, or torchvision ops fail to load).

Used by setup/windows/install.bat step 7; --require-cuda also checks GPU availability.
"""
from __future__ import annotations

import sys


def _cuda_tag(version: str) -> str:
    if "+" in version:
        return version.split("+", 1)[1]
    return "cpu"


def bundle_ok() -> bool:
    try:
        import torch
        import torchvision
        import torchaudio  # noqa: F401
    except (ImportError, RuntimeError, OSError):
        return False

    from importlib.metadata import version
    expected = {"torch": "2.11.0", "torchvision": "0.26.0", "torchaudio": "2.11.0"}
    if any(version(name).split("+", 1)[0] != wanted for name, wanted in expected.items()):
        return False

    tags = [
        _cuda_tag(torch.__version__),
        _cuda_tag(torchvision.__version__),
        _cuda_tag(torchaudio.__version__),
    ]
    cu_tags = [t for t in tags if t.startswith("cu")]
    if cu_tags and len(set(cu_tags)) != 1:
        return False
    if cu_tags and any(not t.startswith("cu") for t in tags):
        return False

    try:
        from torchvision.ops import nms  # noqa: F401
    except Exception:
        return False

    return True


def main() -> int:
    ready = bundle_ok()
    if ready and "--require-cuda" in sys.argv:
        import torch
        ready = torch.cuda.is_available()
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())
