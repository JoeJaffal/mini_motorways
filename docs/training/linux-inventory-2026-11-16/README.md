# Linux training computer inventory — 16 November 2026

User supplied terminal output from the proposed read-only inventory. Parsed numeric source: [inventory.json](inventory.json). The original attachment remains local-only; its SHA-256 is retained without publishing username/hostname or process listing. This is user-provided measurement evidence, not a direct remote inspection.

Confirmed from output: Ubuntu 24.04.4 LTS, Ryzen 9 3950X (16 cores/32 logical processors), nominal 32GiB RAM (free reports 31GiB), RTX 2080 Ti with 11264MiB VRAM, Python 3.12.3 and Git 2.43.0. Supersedes GPU-unknown assumptions and the earlier tentative RTX 2080 Super description. The active interpreter has NumPy 1.26.4 but no torch/gymnasium/SB3/contrib. dotnet is not on PATH; other environments are unknown. The NVIDIA driver CUDA label is not a toolkit or torch verification.

Immediate engineering finding: both / and home are on /dev/nvme0n1p4, reported 476G total, 443G used, 8.1G available and 99% full. Do not proceed with sizeable dependency installation on this filesystem before checking storage. This is an observed capacity issue, not a benchmark. The reported overall 3TB capacity is not resolved: only the root/home filesystem has been measured.

Next read-only commands: `lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINTS` and `df -h -x tmpfs -x devtmpfs`. Use results to locate an already suitable filesystem or propose a user-reviewed storage action. No deletion, mounting, repartitioning or installation is authorized by this inventory. No GPU/CPU throughput or training-duration conclusion can be drawn yet. Existing driver need not be changed based on this output alone.
