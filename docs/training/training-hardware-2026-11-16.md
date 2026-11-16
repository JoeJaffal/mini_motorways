# Corrected training machine — 16 November 2026

User chooses Alienware Aurora Ryzen Edition, AMD Ryzen9 3950X displayed x32,32GiB RAM,3TB storage. These are user-supplied facts,not a remote inspection. [AMD's CPU specification](https://ir.amd.com/news-events/press-releases/detail/914/amd-introduces-worlds-most-powerful-16-core-consumer-desktop-processor-the-amd-ryzen-9-3950x) identifies16physical cores/32threads: x32 refers to logical processors,not32physical cores. [Structured source record](training-hardware-2026-11-16.json).

This replaces the tentative Intel AuroraR11/i7-10700KF/16GB description. **Do not assume the RTX2080Super or Windows10 from that older tentative machine description.** GPU/VRAM,OS,storage type,driver/software environment and actual throughput on this Ryzen machine are unknown. Current laptop versions/CUDAfalse describe only the local laptop,not the training desktop.

User decision: this Ryzen Alienware is the training target. More CPU cores offer potential for additional independent simulator hosts; no linear scaling or specific speedup claimed. Reopen D40worker/thread/device allocation and D38target environment compatibility. Keep initial CPU bring-up as a possible benchmark baseline,not a finalized optimal device. Proposed later measurement compares2/4/8hosts under the same total2048-token rollout so n_steps/env would be1024/512/256;learning implications of per-env trace lengths must also be tracked,not declare settings interchangeable. No worker count adopted now. Avoid32hosts by default merely because32threads are displayed.

GPU and OS clarification should precede CUDA installation/device advice. No packages installed,hardware connection performed,desktopbenchmark or training launched. Historical hardware reports/workbooks remain historical; current decision JSON and status cross-link this correction.

## User-confirmed execution workflow

Training PC OS is Linux (distribution/GPU still unknown). User elects to keep chat on current computer and manually run supplied commands on Linux; abandons chat transfer/SSH setup for now. Future instructions must label machine and use Linux paths. Windows-laptop dependency verification does not establish the Linux target environment. Project/decision-document transfer and setup remain execution prerequisites; no commands launched there yet.
