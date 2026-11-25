#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
mkdir -p output
build_dir="$(mktemp -d "$repo_root/output/city-road-preflight.XXXXXX")"
dotnet build simulation/Headless/TrafficHost.csproj -c Release --nologo --artifacts-path "$build_dir"
exec .venv/bin/python -u training/city_road_pilot.py --dll "$build_dir/bin/TrafficHost/release/TrafficHost.dll"
