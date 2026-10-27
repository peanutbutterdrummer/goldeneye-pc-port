#ifndef _SDL_COMPAT_H_
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
