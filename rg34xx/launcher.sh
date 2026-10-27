#!/bin/bash
# GoldenEye 007 (goldeneye-pc-port, aarch64 build for H700 handhelds on stock Anbernic firmware)
# Put your US ROM (.z64, SHA-1 abe01e4aeb033b6c0836819f549c791b26cfde83) at goldeneye/data/ge007.ntsc-final.z64.
# The first launch converts models from the ROM (black screen for up to a minute).
PORTS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

if [ -d "/opt/system/Tools/PortMaster/" ]; then
  controlfolder="/opt/system/Tools/PortMaster"
elif [ -d "/opt/tools/PortMaster/" ]; then
  controlfolder="/opt/tools/PortMaster"
else
  controlfolder="/roms/ports/PortMaster"
fi

source $controlfolder/control.txt
get_controls

GAMEDIR="$PORTS_DIR/goldeneye"
cd "$GAMEDIR"
> "$GAMEDIR/log.txt" && exec > >(tee "$GAMEDIR/log.txt") 2>&1

$ESUDO chmod 666 /dev/uinput
chmod +x "$GAMEDIR/ge007.aarch64" "$GAMEDIR/prepare-assets/ge007-convert"

if [ ! -f "$GAMEDIR/data/ge007.ntsc-final.z64" ]; then
  echo "ROM missing: put your US GoldenEye 007 ROM at goldeneye/data/ge007.ntsc-final.z64"
  exit 1
fi

# The firmware's own SDL 2.0.12 (/usr/lib) is the one that can open the display.
export LD_LIBRARY_PATH="/usr/lib32:/usr/lib:/mnt/vendor/lib:$LD_LIBRARY_PATH"

# The game reads the pad natively; gptokeyb is only here for the Select+Start exit.
$GPTOKEYB "ge007.aarch64" -c "$GAMEDIR/rg34xx.gptk" &
./ge007.aarch64
echo "[rg34xx] exit status $?"

pkill -9 gptokeyb 2>/dev/null
sync
printf "\033c" > /dev/tty1
