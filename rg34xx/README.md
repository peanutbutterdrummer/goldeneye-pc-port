# GoldenEye 007 PC port for H700 handhelds (RG34XX / RG35XX family)

A native aarch64 build of [goldeneye-pc-port](https://github.com/jkdansereau/goldeneye-pc-port)
for Anbernic H700 handhelds on the **stock Anbernic firmware**. It runs the
full campaign. It is not an emulator. Rendering uses the port's existing
OpenGL ES 3 path on the Mali-G31, and the game reads the pad directly with
modern dual-analog controls.

Built and tested on an RG34XXSP (stock firmware 20250408). Other H700
devices on the same stock firmware should work too, but they are untested.

## Install

1. Copy `GoldenEye 007.sh` and the `goldeneye/` folder into `Roms/PORTS` on
   your SD card.
2. Put **your own** US ROM at `goldeneye/data/ge007.ntsc-final.z64`. It must
   be a big-endian `.z64` with SHA-1 `abe01e4aeb033b6c0836819f549c791b26cfde83`.
   Byte-swapped `.n64` / `.v64` dumps have to be converted to `.z64` first.
   No ROM or game data is included.
3. Launch **GoldenEye 007** from Ports. The first start converts the models
   from your ROM using the firmware's python3, and the screen stays black for
   up to a minute.

* **Exit:** Select+Start.
* **Options overlay:** Select. Use the D-pad to move, A/B to change values
  and Start to close.
* **Logs:** `goldeneye/log.txt`.
* **Settings:** `goldeneye/data/ge007.ini`. The defaults here are
  fullscreen with "Invert look" on.

## What is changed from upstream

`rg34xx/rg34xx_patch.py` applies the changes, and it is idempotent:

* **64-bit layout fixes.** The game and audio code guards its "64-bit PC"
  fixes (struct sizes, pool sizes, libaudio pointer layout) with
  `__x86_64__`. On aarch64 those blocks were skipped, so they now apply to
  `__aarch64__` too.
* **Thread stacks.** Game-thread stacks have to sit below 2 GiB, because
  the decomp truncates stack pointers to `u32`. aarch64 has no `MAP_32BIT`,
  so the stacks are mapped with an address hint in `[0x30000000,
  0x40000000)` instead.
* **SDL 2.0.12.** The firmware ships SDL 2.0.12, which is older than the
  port expects. `port/include/sdl_compat.h` defines the few newer hint and
  enum names, and makes `SDL_OpenURL` a weak symbol.
* **Level-start hang (`src/game/bg.c`).** The special-portal walk in
  `sub_GAME_7F0B37EC` stops at `&g_BgCurrentRoom`. That only works if the
  variable follows `specialportalarray` in memory, which is true on the N64
  and, by luck, in the x86-64 builds. On aarch64 the walk ran into unrelated
  bytes, and a `0xff` wrapped its `u8` counter forever. The game stopped
  rendering at the start of a level while the music kept playing. The walk
  is now bounded by the array itself.
* **GLES precision (`port/fast3d/gfx_opengl.cpp`).** The shaders asked for
  `mediump` floats, which Mali implements as fp16. The horizon-scale sky
  and texture coordinates on large textures lost precision, so the sky was
  black at some view angles and some textures were wrong. The shaders now
  use `highp`. Desktop GL ignores precision qualifiers, which is why
  upstream never saw this.

## Building (on the device)

The stock firmware has gcc 11, the SDL2/GLES headers and python3. It has no
CMake, so unpack the Ubuntu 22.04 `.deb`s without installing them:

```sh
apt-get download cmake cmake-data libjsoncpp25 librhash0 libuv1
for d in *.deb; do dpkg-deb -x "$d" ~/cmake-root; done
export LD_LIBRARY_PATH=~/cmake-root/usr/lib/aarch64-linux-gnu
export CMAKE_ROOT=~/cmake-root/usr/share/cmake-3.22
CMAKE=~/cmake-root/usr/bin/cmake rg34xx/build-rg34xx.sh   # ~3 min on 3 cores
rg34xx/bundle-rg34xx.sh                                   # -> dist/goldeneye-rg34xx-*.zip
```

## Credits

The port is jkdansereau/goldeneye-pc-port and its contributors (MIT), built
on the n64decomp/007 decompilation and the fast3d renderer. The packaging is
modelled on the R36S alpha build from handhelds.wtf. GoldenEye 007 belongs to
its rights holders. Use your own legally obtained ROM.
