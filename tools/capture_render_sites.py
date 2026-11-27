"""Capture sites verified in research/native-render-* and native-ui-* files."""
from pathlib import Path
from inspect_state_tables import read
sites=[('SetupCall',0x4da46b,5),('MarkerHandler',0x2b84e2,7),
       ('Setup',0x4da090,16),('Flush',0x2bf300,16),('Marker',0x2b8be0,16)]
lines=['#pragma once','#include <cstdint>','namespace NativeRenderSites {']
for name,rva,size in sites:
    lines += [f'inline constexpr uintptr_t {name}Rva=0x{rva:x};',
              f'inline constexpr unsigned char {name}Bytes[]={{'+','.join(f'0x{v:02x}' for v in read(0x140000000+rva,size))+'};']
lines+=['}']
(Path(__file__).resolve().parents[1]/'DivaRoom/NativeRenderSites.h').write_text('\n'.join(lines)+'\n')
