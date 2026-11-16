printf '\n--- Linux ---\n'
cat /etc/os-release
uname -sr
printf '\n--- CPU ---\n'
lscpu
printf '\n--- Memory ---\n'
free -h
printf '\n--- Disk ---\n'
df -h / "$HOME"
printf '\n--- GPU ---\n'
if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi
elif command -v lspci >/dev/null 2>&1; then
    lspci | rg -i 'vga|3d|display' 2>/dev/null || lspci
else
    printf 'GPU tools unavailable\n'
fi
printf '\n--- Tools ---\n'
for tool in python3 git dotnet; do
    if command -v "$tool" >/dev/null 2>&1; then
        "$tool" --version
    else
        printf '%s: not installed\n' "$tool"
    fi
done
printf '\n--- Python packages ---\n'
if command -v python3 >/dev/null 2>&1; then
python3 - <<'PY'
import sys
from importlib.metadata import version, PackageNotFoundError
print("Python:", sys.version.split()[0])
for name in ("torch", "numpy", "gymnasium", "stable-baselines3", "sb3-contrib"):
    try:
        print(name + ":", version(name))
    except PackageNotFoundError:
        print(name + ": not installed in this Python environment")
try:
    import torch
    print("PyTorch CUDA available:", torch.cuda.is_available())
    print("PyTorch CUDA build:", torch.version.cuda)
except Exception as exc:
    print("PyTorch check:", type(exc).__name__, str(exc))
PY
fi
