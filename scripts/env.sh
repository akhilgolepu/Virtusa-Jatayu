# Source before running anything that uses faster-whisper on GPU:
#   conda activate anpr && source scripts/env.sh
# CTranslate2 wheels need CUDA 12 cuBLAS (installed side-by-side as nvidia-cublas-cu12)
# and cuDNN 9 (reused from torch's nvidia-cudnn-cu13 install).
_SP=$(python -c "import site; print(site.getsitepackages()[0])")
export LD_LIBRARY_PATH="$_SP/nvidia/cublas/lib:$_SP/nvidia/cudnn/lib:$_SP/nvidia/cu13/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
unset _SP
