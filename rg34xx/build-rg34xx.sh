#!/usr/bin/env bash
#
# Build the PC port natively on an H700 handheld (stock Anbernic firmware,
# Ubuntu 22.04 aarch64: gcc 11, SDL 2.0.12 headers, python3). Run from the
# repo root. Needs CMake >= 3.16; the stock firmware has none, so set CMAKE
# to an unpacked one, e.g. from `apt-get download cmake cmake-data
# libjsoncpp25 librhash0 libuv1` + `dpkg-deb -x` (no system install needed).
#
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
CMAKE="${CMAKE:-cmake}"
python3 rg34xx/rg34xx_patch.py
"$CMAKE" -S . -B build-pc -DROMID=ntsc-final -DCMAKE_BUILD_TYPE=Release -DGL_LIBRARY=GLESv2
"$CMAKE" --build build-pc -j"${JOBS:-3}"
ls -la build-pc/ge007.aarch64
