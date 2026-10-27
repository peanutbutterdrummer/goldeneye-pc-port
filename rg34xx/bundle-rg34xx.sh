#!/usr/bin/env bash
#
# Package an aarch64 build for H700 handhelds (RG34XX / RG35XX family) on the
# stock Anbernic firmware. Run on the device (or any aarch64 Linux) from the
# repo root AFTER rg34xx/build-rg34xx.sh:
#
#     rg34xx/bundle-rg34xx.sh [VERSION]
#
# Produces dist/goldeneye-rg34xx-<VERSION>/ (+ .zip) laid out for Roms/PORTS:
#     GoldenEye 007.sh
#     goldeneye/   engine, prepare-assets/, rg34xx.gptk, data/ge007.ini
# NO ROM and NO ROM-derived data: the user adds their own ROM, and the first
# launch generates data/pcmodels-* / data/pccg-* from it.
#
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

VERSION="${1:-$(git describe --tags --always --dirty 2>/dev/null || echo dev)}"
NAME="goldeneye-rg34xx-${VERSION}"
OUT="dist/${NAME}"
G="$OUT/goldeneye"
EXE=build-pc/ge007.aarch64
[ -x "$EXE" ] || { echo "error: $EXE not found, build first" >&2; exit 1; }

rm -rf "$OUT" "dist/${NAME}.zip"
mkdir -p "$G/data" "$G/licenses" "$G/tools"
cp "$EXE" "$G/" && strip "$G/ge007.aarch64"
cp rg34xx/launcher.sh "$OUT/GoldenEye 007.sh"
cp rg34xx/rg34xx.gptk "$G/"
cp rg34xx/ge007.ini "$G/data/"
printf 'Put your US GoldenEye 007 ROM here as ge007.ntsc-final.z64\n(big-endian .z64, SHA-1 abe01e4aeb033b6c0836819f549c791b26cfde83).\n' > "$G/data/PUT-ROM-HERE.txt"
cp rg34xx/README.md "$OUT/README.md"
cp NOTICE "$G/licenses/NOTICE"
cp LICENSE "$G/licenses/LICENSE-port-MIT.txt"
[ -f port/fast3d/LICENSE.txt ] && cp port/fast3d/LICENSE.txt "$G/licenses/LICENSE-fast3d.txt"
cp tools_pc/eep_convert.py "$G/tools/"

# asset-prep tool (same assembly as tools_pc/bundle-linux.sh, but run on the
# device's python3 instead of a frozen x86 binary)
PREP="$G/prepare-assets"
mkdir -p "$PREP/vendor/scripts" "$PREP/vendor/assets/obseg"
cp tools_pc/dist/prepare-assets/prepare-assets.py "$PREP/"
cp tools_pc/d43_emit.py tools_pc/d69_emit.py tools_pc/d88_emit.py tools_pc/d88_propdefs.py "$PREP/"
cp scripts/filelist.u.csv "$PREP/vendor/scripts/"
cp assets/obseg/file_resource_table.inc.c "$PREP/vendor/assets/obseg/"
find assets -iname 'modelfileheader.inc.c' -print0 | xargs -0 -I{} cp --parents {} "$PREP/vendor/"
nmh="$(find "$PREP/vendor/assets" -iname 'modelfileheader.inc.c' | wc -l)"
[ "$nmh" -gt 400 ] || { echo "error: only $nmh model headers vendored" >&2; exit 1; }
cp rg34xx/ge007-convert "$PREP/"
chmod 755 "$PREP/ge007-convert" "$G/ge007.aarch64" "$OUT/GoldenEye 007.sh"

if find "$OUT" -type f \( -iname '*.z64' -o -iname '*.n64' -o -iname '*.v64' \) | grep -q .; then
  echo "error: bundle contains a ROM image" >&2; exit 1
fi
( cd "$OUT" && zip -qr "../${NAME}.zip" . )
echo "==> dist/${NAME}.zip ($(du -h "dist/${NAME}.zip" | cut -f1))"
