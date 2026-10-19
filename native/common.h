/* Tiny shared helpers for the plugins: a log file in %LOCALAPPDATA%\Remedy\Control. No CRT. */
#ifndef COMMON_H
#define COMMON_H
#include <windows.h>

static HANDLE g_log = INVALID_HANDLE_VALUE;

static void log_open(const WCHAR *name) {
    WCHAR path[MAX_PATH + 40];
    DWORD n = GetEnvironmentVariableW(L"LOCALAPPDATA", path, MAX_PATH);
    if (n == 0 || n >= MAX_PATH) return;
    const WCHAR *mid = L"\\Remedy\\Control\\";
    DWORD i = 0, k = 0;
    while (mid[i]) { path[n + i] = mid[i]; i++; }
    while (name[k] && n + i + k < MAX_PATH + 39) { path[n + i + k] = name[k]; k++; }
    path[n + i + k] = 0;
    g_log = CreateFileW(path, GENERIC_WRITE, FILE_SHARE_READ, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
}

static void log_str(const char *s) {
    DWORD len = 0, w;
    if (g_log == INVALID_HANDLE_VALUE) return;
    while (s[len]) len++;
    WriteFile(g_log, s, len, &w, NULL);
}

static void log_int(int v) {
    char buf[16];
    int i = 15;
    unsigned u = v < 0 ? (unsigned)-v : (unsigned)v;
    buf[i] = 0;
    do { buf[--i] = (char)('0' + u % 10); u /= 10; } while (u);
    if (v < 0) buf[--i] = '-';
    log_str(buf + i);
}

static void log_close(void) {
    if (g_log != INVALID_HANDLE_VALUE) CloseHandle(g_log);
    g_log = INVALID_HANDLE_VALUE;
}

#endif
