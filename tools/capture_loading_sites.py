"""Capture only routines reviewed in native-loading-*.txt, without modifying the EXE."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from project_paths import GAME_DIR, MOD_DIR, MIKUMIKUMODEL_DIR, ROOM_SOURCE_DIR
from pathlib import Path
import struct,hashlib
root=Path(__file__).resolve().parents[1]
game=(GAME_DIR)
b=(game/'DivaMegaMix.exe').read_bytes()
assert hashlib.sha256(b).hexdigest()=='6f4df714c28515c93b3023e7d6dafa9095dd8835f762d54db1726fb8bc04504d'
pe=struct.unpack_from('<I',b,60)[0]
sections=[]
for i in range(struct.unpack_from('<H',b,pe+6)[0]):
    p=pe+24+struct.unpack_from('<H',b,pe+20)[0]+40*i
    size,rva,rawsize,raw=struct.unpack_from('<IIII',b,p+8)
    sections.append((rva,rawsize,raw))
def read(rva,n):
    for va,size,raw in sections:
        if va<=rva and rva+n<=va+size:return b[raw+rva-va:raw+rva-va+n]
    raise ValueError(hex(rva))
out=['#pragma once','namespace NativeLoadingSites {']
for name,rva,n in [('Begin',0x653c30,12),('Finish',0x653c90,5),('Finished',0x653cc0,5),('Reset',0x653bd0,7),('Exists',0x2c9960,16),('ConfirmSound',0x1a7f00,16),('CancelSound',0x1a7f20,16),('SelectSound',0x1a7f60,16),('EnterSound',0x1a8680,16),('Sound',0x5aa540,16),('StopMusic',0x5ab1c0,16),('PlayMusic',0x5ab150,16),('MenuMusic',0x1ac090,16),('MenuAnimation',0x6bf1a0,16),('ListAnimation',0x6699e0,16),('MenuAnimationDone',0x1b3300,16)]:
    out += [f'inline constexpr uintptr_t {name}Rva=0x{rva:x};',f'inline constexpr unsigned char {name}Bytes[]={{'+','.join(f'0x{x:02x}' for x in read(rva,n))+'};']
out += [f'inline constexpr uintptr_t MusicActiveRva=0x5ab200;',
        'inline constexpr unsigned char MusicActiveBytes[]={'+','.join(f'0x{x:02x}' for x in read(0x5ab200,32))+'};']
out+=['}']
(root/'DivaRoom/NativeLoadingSites.h').write_text('\n'.join(out)+'\n')
