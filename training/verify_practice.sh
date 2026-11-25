#!/usr/bin/env bash
# Explicitly selected non-training verification. No learner/updater is invoked.
set -euo pipefail
PREP_PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PREP_PROJECT_ROOT"
python -c 'import sys; assert sys.prefix != sys.base_prefix, "Activate the project Python virtual environment first"'
mkdir -p tmp
dotnet build simulation/Headless -c Release --nologo
dotnet build simulation/Headless -c Debug --nologo
dotnet simulation/Headless/bin/Release/net8.0/TrafficHost.dll --self-test
dotnet simulation/Headless/bin/Release/net8.0/TrafficHost.dll --practice-self-test
PYTHONPATH="$PREP_PROJECT_ROOT/training${PYTHONPATH:+:$PYTHONPATH}" python -m unittest test_visible_observation test_hierarchy_policy test_hierarchy_credit test_hierarchy_objective test_hierarchy_integration test_hierarchy_updater test_inference_collector test_practice_protocol test_practice_replay test_evaluate_practice test_connection_practice test_environment -v
