#!/usr/bin/env bash
# Seed this case's fixture from scripts/behavior_check.py, the fixture source shared with the Codex harness.
set -euo pipefail
case_dir=$(cd "$(dirname "$0")" && pwd)
python "$case_dir/../../scripts/behavior_check.py" seed . "$(basename "$case_dir")"
