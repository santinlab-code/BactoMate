#!/bin/bash
# Install PyTorch with CUDA support for NVIDIA GPUs
# This script detects your CUDA version and installs the appropriate PyTorch build

set -e

echo "=========================================="
echo "Installing PyTorch with CUDA Support"
echo "=========================================="
echo ""

# PyTorch 2.11's shared CUDA baseline uses cu128, not older toolkit indexes.
# Driver capability matters; an installed nvcc toolkit does not choose the wheel.
CUDA_VERSION="cu128"
if ! command -v nvidia-smi &> /dev/null; then
    echo "No NVIDIA driver found. Keeping the installed CPU/MPS stack."
    exit 0
fi
DRIVER_CUDA=$(nvidia-smi | sed -n 's/.*CUDA Version: *\([0-9][0-9]*\.[0-9][0-9]*\).*/\1/p' | head -1)
if ! python3 -c 'import sys; v=tuple(map(int,sys.argv[1].split("."))); sys.exit(0 if v >= (12,8) else 1)' "$DRIVER_CUDA"; then
    echo "CUDA 12.8 or newer driver capability is required by this helper."
    echo "Keeping the installed stack; update the NVIDIA driver to enable this CUDA build."
    exit 0
fi

echo ""
echo "Installing PyTorch with CUDA ${CUDA_VERSION}..."
echo ""

# Install CUDA-enabled PyTorch
python3 -m pip install --upgrade --force-reinstall --no-deps "torch==2.11.0" "torchvision==0.26.0" "torchaudio==2.11.0" --index-url https://download.pytorch.org/whl/${CUDA_VERSION}

echo ""
echo "Verifying CUDA installation..."
python3 -c "
import torch
print(f'PyTorch version: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'CUDA version: {torch.version.cuda}')
    print(f'GPU: {torch.cuda.get_device_name(0)}')
    print('✓ CUDA installation successful!')
else:
    print('✗ CUDA is not available')
    print('  This might mean:')
    print('  - PyTorch was installed without CUDA support')
    print('  - CUDA drivers are not properly installed')
    print('  - GPU is not detected')
"

echo ""
echo "=========================================="
echo "Installation complete!"
echo "=========================================="
echo ""
