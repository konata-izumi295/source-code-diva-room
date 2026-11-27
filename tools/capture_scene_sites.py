"""Capture only integration sites reviewed in native-state-* research."""
from pathlib import Path
from inspect_state_tables import read

sites = [('MainLookup',0x2c49c0,16),('SubLookup',0x2c4a00,16),
         ('StateNames',0x127e4a27,7),('ChangeState',0x2c4bb0,16),
         ('MenuDone',0x6bfe70,5),('MenuBusy',0x1d93b0,16),
         ('FadeIn',0x43dce0,16),('InputState',0x2ac970,16),
         ('InputMappedPress',0x2ab260,12),('InputPress',0x2aaf80,16)]
lines=['#pragma once','#include <cstdint>','namespace NativeSceneSites {']
for name,rva,size in sites:
    lines += [f'inline constexpr uintptr_t {name}Rva=0x{rva:x};',
              f'inline constexpr unsigned char {name}Bytes[]={{'+','.join(f'0x{v:02x}' for v in read(0x140000000+rva,size))+'};']
lines+=['}']
(Path(__file__).resolve().parents[1]/'DivaRoom/NativeSceneSites.h').write_text('\n'.join(lines)+'\n')
