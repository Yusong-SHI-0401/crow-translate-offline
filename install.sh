#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec "${CROW_PYTHON:-/usr/bin/python3}" "$project_dir/scripts/install.py" "$@"
