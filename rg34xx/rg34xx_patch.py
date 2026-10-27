#!/usr/bin/env python3
"""Apply the RG34XX / aarch64 Linux changes to a goldeneye-pc-port checkout.

Idempotent; run from the repo root. Changes:
 1. 64-bit layout fixes guarded by __x86_64__ also apply to __aarch64__
 2. SDL 2.0.12 headers (stock Anbernic firmware): define the few newer names
 3. game-thread stacks below 2 GiB without MAP_32BIT (aarch64 has none)
 4. bg.c special-portal walk bounded by its own array (level-start hang)
 5. GLES shaders use highp floats (mediump = fp16 on Mali: sky/texture errors)
"""
import re, sys
from pathlib import Path

root = Path('.')
changed = []

def edit(path, fn):
    p = root / path
    old = p.read_text()
    new = fn(old)
    if new != old:
        p.write_text(new)
        changed.append(path)

# 1. "64-bit PC" guards ------------------------------------------------------
X64_FILES = [
    'src/audi.c', 'src/music.c', 'src/memp.c', 'assets/animationtable_data.h',
    'src/libultra/audio/synthesizer.c', 'src/libultra/audio/synsetvol.c',
    'src/libultra/audio/synsetpan.c', 'src/libultra/audio/synsetfxmix.c',
    'src/libultra/audio/save.c', 'src/libultra/audio/load.c',
    'src/game/image_bank.c', 'src/game/initunk_005450.c',
    'src/game/objecthandler.c', 'src/game/rsp.c',
]
for f in X64_FILES:
    edit(f, lambda s: re.sub(r'^#if defined\(__x86_64__\)[ \t]*$',
                             '#if defined(__x86_64__) || defined(__aarch64__)',
                             s, flags=re.M))
edit('port/include/pc_protos.h', lambda s: s.replace(
    '#if defined(PORT) && defined(__x86_64__) && !defined(__cplusplus)',
    '#if defined(PORT) && (defined(__x86_64__) || defined(__aarch64__)) && !defined(__cplusplus)'))

# 2. SDL 2.0.12 header compatibility ------------------------------------------
COMPAT = 'port/include/sdl_compat.h'
compat_text = '''#ifndef _SDL_COMPAT_H_
#define _SDL_COMPAT_H_
/* Names newer than SDL 2.0.12 (the stock Anbernic H700 firmware SDL). The
 * hints are plain strings SDL ignores when unknown; the enum value is the
 * one SDL 2.0.14 assigned. */
#include <SDL.h>

#ifndef SDL_HINT_JOYSTICK_HIDAPI_PS5_RUMBLE
#define SDL_HINT_JOYSTICK_HIDAPI_PS5_RUMBLE "SDL_JOYSTICK_HIDAPI_PS5_RUMBLE"
#endif
#ifndef SDL_HINT_MOUSE_RELATIVE_SYSTEM_SCALE
#define SDL_HINT_MOUSE_RELATIVE_SYSTEM_SCALE "SDL_MOUSE_RELATIVE_SYSTEM_SCALE"
#endif
#if !SDL_VERSION_ATLEAST(2, 0, 14)
#define SDL_CONTROLLER_TYPE_VIRTUAL ((SDL_GameControllerType)6)
/* weak: NULL at runtime on an SDL that predates it */
extern DECLSPEC int SDLCALL SDL_OpenURL(const char *url) __attribute__((weak));
#define SDL_COMPAT_HAVE_OPENURL() (SDL_OpenURL != NULL)
#else
#define SDL_COMPAT_HAVE_OPENURL() 1
#endif

#endif
'''
p = root / COMPAT
if not p.exists() or p.read_text() != compat_text:
    p.write_text(compat_text)
    changed.append(COMPAT)

def add_compat_include(s):
    if '#include "sdl_compat.h"' in s:
        return s
    m = re.search(r'^#include <SDL[^>]*>\s*$', s, flags=re.M)
    assert m, 'no SDL include'
    return s[:m.end()] + '#include "sdl_compat.h"\n' + s[m.end():]
edit('port/src/input.c', add_compat_include)
edit('port/src/updatecheck.c', add_compat_include)
edit('port/src/updatecheck.c', lambda s: s.replace(
    '    if (SDL_OpenURL(UC_RELEASES) != 0)',
    '    if (!SDL_COMPAT_HAVE_OPENURL() || SDL_OpenURL(UC_RELEASES) != 0)'))
assert 'SDL_COMPAT_HAVE_OPENURL()' in (root / 'port/src/updatecheck.c').read_text()

# 3. low game-thread stacks without MAP_32BIT --------------------------------
LOWSTACK_OLD = '''    if (p != MAP_FAILED)
        return p;
#endif
    return NULL;
}'''
LOWSTACK_NEW = '''    if (p != MAP_FAILED)
        return p;
#else
    /* No MAP_32BIT (aarch64): ask for an address hint in [0x30000000,
     * 0x40000000), which sits between the image (0x20000000) and the D131
     * module range (0x40000000), and keep it only if the kernel honoured it. */
    static uintptr_t hint = 0x30000000u;
    while (hint + sz <= 0x40000000u) {
        void *p = mmap((void *)hint, sz, PROT_READ | PROT_WRITE,
                       MAP_PRIVATE | MAP_ANONYMOUS
#if defined(MAP_FIXED_NOREPLACE)
                       | MAP_FIXED_NOREPLACE
#endif
#if defined(MAP_STACK)
                       | MAP_STACK
#endif
                       , -1, 0);
        hint += (sz + 0xffffu) & ~(uintptr_t)0xffffu;
        if (p == MAP_FAILED)
            continue;
        if ((uintptr_t)p + sz <= 0x80000000u)
            return p;
        munmap(p, sz);
    }
#endif
    return NULL;
}'''
edit('port/src/libultra.c', lambda s: s if 'No MAP_32BIT (aarch64)' in s else s.replace(LOWSTACK_OLD, LOWSTACK_NEW, 1))
assert 'No MAP_32BIT (aarch64)' in (root / 'port/src/libultra.c').read_text()

# 4. bg.c: the special-portal walk ends at &g_BgCurrentRoom, i.e. it assumes
# that variable follows specialportalarray in memory (true on N64, and by luck
# on the x86-64 builds). The aarch64 layout differs, so the walk ran into
# unrelated bytes and a 0xff wrapped the u8 portal counter forever: the game
# hung at the start of a level with music still playing. Bound it by the array.
BG_OLD = '''    ptr = (u8 *)specialportalarray;
    end = (u8 *)&g_BgCurrentRoom;
'''
BG_NEW = '''    ptr = (u8 *)specialportalarray;
#ifdef PORT
    end = (u8 *)specialportalarray + sizeof(specialportalarray);
#else
    end = (u8 *)&g_BgCurrentRoom;
#endif
'''
edit('src/game/bg.c', lambda s: s if BG_NEW in s else s.replace(BG_OLD, BG_NEW, 1))
edit('src/game/bg.c', lambda s: s.replace(
    '    } while ((u32)ptr < (u32)end);\n}',
    '    } while ((uintptr_t)ptr < (uintptr_t)end);\n}', 1))
assert BG_NEW in (root / 'src/game/bg.c').read_text()

# 5. GLES shaders asked for mediump floats, which Mali implements as fp16:
# texture coordinates on big/repeating textures and the horizon-scale sky
# (CPU-built float vertices) lost precision -> wrong textures, black sky at
# some view angles. Desktop GL ignores precision qualifiers, so upstream never
# saw it. Use highp (vertex shaders always have it; fragment where offered).
GLSL = 'port/fast3d/gfx_opengl.cpp'
VS_OLD = '        append_line(vs_buf, &vs_len, "precision mediump float;");\n'
VS_NEW = '        append_line(vs_buf, &vs_len, "precision highp float;");\n'
FS_OLD = '        append_line(fs_buf, &fs_len, "precision mediump float;");\n'
FS_NEW = ('        append_line(fs_buf, &fs_len, "#ifdef GL_FRAGMENT_PRECISION_HIGH");\n'
          '        append_line(fs_buf, &fs_len, "precision highp float;");\n'
          '        append_line(fs_buf, &fs_len, "#else");\n'
          '        append_line(fs_buf, &fs_len, "precision mediump float;");\n'
          '        append_line(fs_buf, &fs_len, "#endif");\n')
edit(GLSL, lambda s: s.replace(VS_OLD, VS_NEW, 1))
edit(GLSL, lambda s: s if FS_NEW in s else s.replace(FS_OLD, FS_NEW, 1))
assert VS_NEW in (root / GLSL).read_text() and FS_NEW in (root / GLSL).read_text()

print('changed:', *changed, sep='\n  ') if changed else print('nothing to change')
