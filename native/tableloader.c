/* Makes the Mod Table UI independent of how Vortex deploys iphlpapi.dll.
 *
 * The UI mod only works if reg2k's Loose Files Loader (LFL) is active. LFL normally ships as
 * iphlpapi.dll in the game folder, a file several mods and Vortex's own loader mod all provide;
 * Vortex's conflict handling for it fails (EPERM) and silently leaves the folder without it.
 *
 * This plugin (loaded by the Control Plugin Loader from <game>\plugins\) loads our own copy of
 * LFL from plugins\ControlModTable\LooseFilesLoader.bin instead, unless the game folder already
 * has an iphlpapi.dll (then that one is active and loading a second copy would double-hook).
 *
 * Log: %LOCALAPPDATA%\Remedy\Control\ModTableLoader.log
 */
#include <windows.h>

#include "common.h"

#define WAIT_MS_MAX 60000

static void dir_of(WCHAR *path) {
    DWORD n = 0, last = 0;
    while (path[n]) { if (path[n] == L'\\') last = n; n++; }
    path[last + 1] = 0; /* keep trailing backslash */
}

static void append(WCHAR *dst, const WCHAR *src) {
    DWORD n = 0, i = 0;
    while (dst[n]) n++;
    while (src[i] && n + i < MAX_PATH - 1) { dst[n + i] = src[i]; i++; }
    dst[n + i] = 0;
}

static DWORD WINAPI worker(LPVOID param) {
    WCHAR exe_dir[MAX_PATH], probe[MAX_PATH], lib[MAX_PATH];
    HMODULE self = (HMODULE)param;
    DWORD waited = 0;
    HMODULE lfl;

    log_open(L"ModTableLoader.log");
    log_str("ControlModTableLoader 1.0\r\n");

    if (!GetModuleFileNameW(NULL, exe_dir, MAX_PATH)) { log_str("no exe path\r\n"); log_close(); return 0; }
    dir_of(exe_dir);
    probe[0] = 0;
    append(probe, exe_dir);
    append(probe, L"iphlpapi.dll");
    if (GetFileAttributesW(probe) != INVALID_FILE_ATTRIBUTES) {
        log_str("Game folder provides iphlpapi.dll; assuming the Loose Files Loader is active. Not loading our copy.\r\n");
        log_close();
        return 0;
    }

    if (!GetModuleFileNameW(self, lib, MAX_PATH)) { log_str("no plugin path\r\n"); log_close(); return 0; }
    dir_of(lib);
    append(lib, L"ControlModTable\\LooseFilesLoader.bin");
    if (GetFileAttributesW(lib) == INVALID_FILE_ATTRIBUTES) {
        log_str("Bundled loader missing: plugins\\ControlModTable\\LooseFilesLoader.bin\r\n");
        log_close();
        return 0;
    }

    /* the loader hooks the render library's file lookup, so that library must be loaded first */
    while (!GetModuleHandleW(L"rl_rmdwin10_f.dll") && !GetModuleHandleW(L"rl_rmdwin7_f.dll")) {
        if (waited >= WAIT_MS_MAX) { log_str("render library never appeared; loading anyway\r\n"); break; }
        Sleep(50);
        waited += 50;
    }
    log_str("waited ms: ");
    log_int((int)waited);
    log_str("\r\n");

    lfl = LoadLibraryW(lib);
    if (lfl) log_str("Loose Files Loader loaded. See LooseFilesLoader.log.\r\n");
    else { log_str("LoadLibrary failed, error "); log_int((int)GetLastError()); log_str("\r\n"); }
    log_close();
    return 0;
}

BOOL WINAPI DllMain(HINSTANCE inst, DWORD reason, LPVOID reserved) {
    (void)reserved;
    if (reason == DLL_PROCESS_ATTACH) {
        HANDLE t;
        DisableThreadLibraryCalls(inst);
        /* not in DllMain itself: loading another DLL under the loader lock can deadlock */
        t = CreateThread(NULL, 0, worker, inst, 0, NULL);
        if (t) CloseHandle(t);
    }
    return TRUE;
}
