#!/usr/bin/env bash
# Convenience entry point for the legacy C++ playground, not the Unity apps.
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cmake -S "$repo_dir" -B "$repo_dir/build" -DCMAKE_BUILD_TYPE=Release "$@"
cmake --build "$repo_dir/build" --config Release --parallel
ctest --test-dir "$repo_dir/build" -C Release --output-on-failure
