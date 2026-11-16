## Updated storage calculation

[Calculated initial budget](STORAGE_BUDGET.md): GPU wheel payload6.159GiB, downloads3.421GiB; explicit SDK/source/run/system allowances bring the total to20.680GiB. Recommend25GiB available initially;50GB remains comfortable, not a minimum. Package sizing is not a target installation test.

# Linux inventory commands — 16 November 2026

User requests commands to run manually on the Alienware Linux training computer. check.sh is a read-only inventory of OS, CPU, memory, filesystem capacity, GPU/driver, available tools and packages in the current python3 environment. No package installation, repository mutation, learner step or benchmark. Results are not yet available; reported Ryzen 9 3950X/32GiB/3TB remain user-reported, GPU/VRAM unknown. A missing package here does not establish it is absent from all virtual environments. Actual task throughput measurement requires the implemented workload later. No hostname, environment-variable dump or repository credentials requested.

Paste the script into a terminal; return its output in chat. No new trainer command exists yet. This is not training authorization or a runtime estimate.


## Storage follow-up

User supplies lsblk/df: 1.8T /dev/sda2 NTFS is unmounted, with free space unknown; NVMe 953.9G includes unmounted 469.8G NTFS and mounted 483.9G ext4 root. This accounts for roughly nominal 3TB overall, but root remains 99% used. Parsed source: storage.json. Proposed next step is mount /dev/sda2 read-only via udisksctl, then inspect df. No repair/force/format/delete or package installation suggested. Source consulted: Ubuntu Noble udisksctl manual, https://manpages.ubuntu.com/manpages/noble/man1/udisksctl.1.html . No command result or mount success claimed yet.


## IT authentication and home usage

User reports sda2 read-only mount requests the IT user's password; mount success is not reported. Subsequent home du reports total389M (snap311M, Desktop51M, cache27M). This does not explain root filesystem443Gused; remaining usage source/ownership is unknown. No useful space recovery is apparent from this account. Suggested next step: IT-provided writable project storage or adequate Linux space. Agent sends no message to IT, requests no password and performs no deletion or escalation. Numeric source: home-storage-followup.json. Remote environment installation is waiting on usable storage; local design reconciliation/implementation preparation can continue.


## Initial workspace allowance

User asks whether disk is full and how much is needed. Root/home has8.1Gavailable of476G,99%used; free space on unmounted1.8T NTFS remains unknown. Engineering planning recommendation: request50GB of writable project space initially, covering isolated dependencies, project/build files and bounded checkpoint/log/replay retention. This is an allocation target, not a measured minimum or guarantee for unlimited runs; actual footprint requires implementation and retention measurements. Avoid interpreting3TBtotal as3TBfree. Remote setup remains pending usable storage; local preparation can proceed. No installation, cleanup or training performed.


## Disks screenshots clarified

Three supplied screenshots show DATA /dev/sda2 as2TB NTFS Not Mounted. The trailing1.1MB region is explicitly Unallocated Space; it is not the free file capacity inside DATA. DATA file usage remains unknown. Previous mount request required IT credentials; recommend IT make DATA available, then check its Properties in Files. No repeated command/credential request, partitioning or deletion. Small observation source: disks-ui-observations.json; screenshots remain local-only.


## User requests another terminal diagnostic

User has no external drive and requests another command. Propose `du -xhd1 / 2>/dev/null | sort -h` without sudo, to summarize readable directory allocation on the Linux root filesystem. Read-only; no cleanup, installation, mount, credential bypass or permissions change. May take time. Counts are incomplete when directories are inaccessible, so do not equate a low du total with df being wrong. Prior user home total389M means substantial recoverable user-owned data is not established. Need inspect output before any recommendation to remove files.50GB remains an initial allowance, not a measured minimum; compatibility and dependency footprint still unverified.


## Root du summary received

User's unprivileged root scan reports36Gtotal (/usr19G,/var13G,/opt2.8G,/home398M), versus earlier df443Gused and8.1Gavailable. The incomplete du view does not create extra free space. Suppressed permission errors may omit data; deleted-open files/other mount-accounting differences are also possible but unmeasured. No safe recoverable capacity identified. Recommend IT inspect accounting or provide writable secondary storage; do not delete system directories or infer a filesystem defect. Parsed source: root-usage-followup.json.


## Actual existing Windows workspace measured

User screenshot reports7,819,448,923logical bytes and7,923,859,456allocated bytes (Windows UI7.28GB/7.37GB). Direct unprivileged recursive logical-size scan exactly matches7,819,448,923bytes with0stat errors, excluding junction traversal. Main components: tmp5,369,442,705bytes; output1,115,363,950; .venv706,034,824; simulation423,070,617; docs154,915,021. Source: local-workspace-size.json. Correct distinction: prior36.59MiB tracked baseline is neither this full workspace nor a complete training installation. Most current folder size is accumulated scratch/output, which is not automatically transferred to the fresh Linux setup. Windows .venv is local CPU environment and not the Linux/GPU footprint. No files deleted; no exact Linux storage requirement established.


## Setup step1 — obtain branch

After user reports30GBfree and asks what next, verified origin/Maskable-PPO remote still938b9f80e67ca5341920a10e9e671164a474fc38. Supply `git clone --branch Maskable-PPO --single-branch https://github.com/JoeJaffal/mini_motorways.git "$HOME/mini_motorways"`. Git clone stops if destination already exists nonempty; inspect errors rather than delete/overwrite. Linux setup uses a fresh clone, not Windows scratch/output/venv. Current locally authored restart documents are not pushed and will not yet appear on Linux; new hierarchy trainer is not implemented. Source acquisition is not training. No remote clone outcome claimed yet.
