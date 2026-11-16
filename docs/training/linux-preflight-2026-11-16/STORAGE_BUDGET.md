# Initial storage calculation — 16 November 2026

## Result

For a fresh, headless Linux GPU setup, request **about 25 GiB available initially**. A 50 GB allocation remains comfortable but is not a measured minimum. The currently reported 8.1 GiB free is below this planned starting budget. This is a reproducible package-payload calculation plus explicit allowances, not an exact installed/peak measurement or guarantee for indefinitely retained runs.

| Component | GiB | Basis |
| --- | ---: | --- |
| Python packages, GPU variant, unpacked payload | 6.159 | ZIP central-directory sums for 34 selected Linux wheels |
| Downloads for those packages | 3.421 | Actual archive lengths; allowance for staging while packages are installed |
| .NET SDK download, extraction and small builds | 1.000 | SDK archive 217,060,685 bytes; gzip tar size field 597,166,080 bytes; remainder is a build allowance |
| Fresh source and Git | 0.100 | Rounded allowance above measured tracked files 36.59 MiB plus existing Git directory about 24 MiB; clone history/branch selection may differ |
| Initial checkpoints, logs and replay storage | 5.000 | Engineering allocation, not measured usage or an adopted automatic deletion policy |
| Space left for normal system operation | 5.000 | Engineering reserve, not additional project files or a universal OS minimum |
| **Planning total** | **20.680** | Sum of the above |
| **Rounded initial free-space target** | **25** | Additional margin for installation/bytecode/filesystem overhead and variation |

If the workspace is on a separate drive, keep system partition headroom separately; free space on one filesystem cannot substitute for temporary files silently placed on another. Keep environment, download/temp paths and run output deliberately placed when implementing setup.

## What was measured

Own script `measure_package_storage.py` reads public Python metadata, selects Linux x86_64 / CPython 3.12 wheels, and reads ZIP central directories with bounded HTTP Range. No full wheels or libraries were downloaded, installed or executed. CUDA 12.6 and CPU distributions of torch 2.14.1 were evaluated with the four existing requirements pins (Gymnasium 1.4.0, SB3 2.9.2, SB3-Contrib 2.9.2, NumPy 2.5.4) and their applicable dependencies, without extras. These are sizing scenarios, not new user-approved dependency or device choices.

- CPU scenario: 16 packages; 224,261,094 compressed bytes (0.209 GiB); 816,214,890 unpacked payload bytes (0.760 GiB).
- CUDA 12.6 scenario: 34 packages; 3,673,396,185 compressed bytes (3.421 GiB); 6,613,296,347 unpacked payload bytes (6.159 GiB).
- Central-directory data fetched per profile is only about 1.6 MiB; metadata requests are additional small transfers. No GPU benchmark or target installation was performed.
- SDK 8.0.427 Linux x64 distribution inspected via a four-byte HTTP range and Content-Range size. Gzip ISIZE is a modulo-2^32 tar-stream size, not extracted filesystem allocation. SDK/build allowance is not presented as an exact installed measurement.

Candidate package size is not runtime validation for the RTX2080Ti. Confirm selected binary architecture support, dependency resolution through pip, and operation on the actual machine before installation/training claims. Do not choose CUDA solely from nvidia-smi's driver label. The SDK remains the earlier source-baseline version for this calculation; Microsoft's current .NET8 page says the release is now out of support. Dependency/support policy reconciliation is a separate implementation task, not silently changed by this storage estimate.

## Relation to the 7.37 GB Windows folder

The local folder screenshot is accurate: 7,819,448,923 logical bytes, 7,923,859,456 allocated bytes. Direct scan matches the logical size. Roughly 5 GiB is scratch (`tmp`) and 1 GiB old output (`output`); Windows `.venv` is about 0.66 GiB. A fresh Linux setup does not require copying that whole accumulated folder or its Windows environment. Nor is a 36.59 MiB source measurement a complete training installation estimate.

## Checks, limits and reproduction

Package counts, positive sizes and aggregate sums checked from `package-storage-calculation.json`; final version constraints checked by the fixed-point metadata resolver. It is a deliberately small custom resolver, not pip's backtracking solver or an installation test. Selected-version snapshots are `sizing-cpu-versions.txt` and `sizing-cu126-versions.txt`. These snapshots do not adopt new training settings. Actual installed usage includes bytecode, filesystem allocation and possible setup caches; peak use depends on install flags/temp/cache placement. Saving many runs, raw video or Unity Editor assets can exceed the allowance; neither Unity Editor nor a full CUDA development toolkit is included in this headless, prebuilt-wheel calculation.

Run with an existing Python that has `packaging`, or pip's vendored packaging:

```text
python measure_package_storage.py
```

This refreshes current dependency metadata, so later results can differ as unpinned transitive versions change. Preserve the current JSON/version snapshot as dated evidence. Original attempt required using pip's vendored packaging and ignoring historical invalid version strings before the final successful run; no package installation was used to resolve those script issues.

Primary sources: [PyTorch distribution choices](https://pytorch.org/get-started/previous-versions/), public wheel/index URLs recorded per package in the JSON, [SDK release metadata](https://builds.dotnet.microsoft.com/dotnet/release-metadata/8.0/releases.json), [current .NET8 status](https://dotnet.microsoft.com/en-us/download/dotnet/8.0).

Outcome: recommend 25 GiB initial available capacity under these allowances. No cleanup, package installation, simulator/trainer implementation, training, commit or push. Exact future installed and run-retention sizes remain to be measured.
