#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
out="${TMPDIR:-/tmp}/aquasafe_core_tests"

g++ -std=c++17 -Wall -Wextra -Werror \
    -I"$root/lib/aquasafe_core" \
    "$root/lib/aquasafe_core/safety.cpp" \
    "$root/lib/aquasafe_core/hmac.cpp" \
    "$root/test/test_core.cpp" \
    -lcrypto -o "$out"

"$out"
