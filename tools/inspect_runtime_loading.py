"""Read-only verification of reviewed game routines; never modifies the process."""
import ctypes as c
from ctypes import wintypes as w
import re
import sys
from pathlib import Path

k = c.WinDLL('kernel32', use_last_error=True)
k.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
k.OpenProcess.restype = w.HANDLE
k.ReadProcessMemory.argtypes = [w.HANDLE, c.c_void_p, c.c_void_p, c.c_size_t, c.POINTER(c.c_size_t)]
k.ReadProcessMemory.restype = w.BOOL
k.CloseHandle.argtypes = [w.HANDLE]
pid, base = int(sys.argv[1]), int(sys.argv[2], 0)
h = k.OpenProcess(0x1010, False, pid)
if not h:
    raise c.WinError(c.get_last_error())
try:
    root = Path(__file__).resolve().parents[1]
    text = '\n'.join((root / ('DivaRoom/' + name)).read_text() for name in ['NativeLoadingSites.h','NativeSceneSites.h','NativeRenderSites.h'])
    for name, rva, values in re.findall(r'(\w+)Rva=(0x[0-9a-f]+);\s*inline constexpr unsigned char \w+Bytes\[\]=\{([^}]+)\}', text):
        expected = bytes(int(v, 0) for v in values.split(','))
        data = c.create_string_buffer(len(expected))
        count = c.c_size_t()
        if not k.ReadProcessMemory(h, base + int(rva, 0), data, len(data), c.byref(count)):
            raise c.WinError(c.get_last_error())
        actual = data.raw
        print(name, 'MATCH' if actual == expected else 'MISMATCH', actual.hex())
    for label,rva,size in [('scene_state',0xcc61078,52),('main_menu_task',0xcc5eef8,8),('menu_substate',0xbf6ee0+42*32,32)]:
        data = c.create_string_buffer(size)
        count=c.c_size_t()
        if k.ReadProcessMemory(h,base+rva,data,size,c.byref(count)):
            print(label,data.raw.hex())
finally:
    k.CloseHandle(h)
