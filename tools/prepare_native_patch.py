"""Capture exact bytes for reviewed sites in the supported executable."""
import hashlib, struct, json, zipfile
from pathlib import Path
from audit_menu import GAME, ROOT, DOWNLOADS, u, s
b=(GAME/'DivaMegaMix.exe').read_bytes()
assert hashlib.sha256(b).hexdigest()=='6f4df714c28515c93b3023e7d6dafa9095dd8835f762d54db1726fb8bc04504d'
pe=u(b,60); sections=[]
for i in range(struct.unpack_from('<H',b,pe+6)[0]):
    p=pe+24+struct.unpack_from('<H',b,pe+20)[0]+40*i
    size,rva,rawsize,raw=struct.unpack_from('<IIII',b,p+8)
    sections.append((rva,rawsize,raw))
def read(rva,n):
    for va,size,raw in sections:
        if va<=rva and rva+n<=va+size:return b[raw+rva-va:raw+rva-va+n]
    raise ValueError(hex(rva))
sites={'Count':(0x6bf1fd,7),'NormalNames':(0x6bf556,21),
       'SelectedNames':(0x6bf3ee,21),'DialogName':(0x6bea77,21),
       'InitialSelection':(0x6bf204,5),'Confirm':(0x6be847,5),
       'Dispatch':(0x6be858,5),'Background':(0x6beafa,5),
       'ListInitialize':(0x6bf319,5),
       'Footer':(0x21a31718,5),'FooterText':(0x6c160b,5)}
header=['#pragma once','#include <cstdint>','namespace NativeMenuSites {']
for name,(rva,n) in sites.items():
    value=read(rva,n)
    header += [f'inline constexpr uintptr_t {name}Rva = 0x{rva:x};',
               f'inline constexpr unsigned char {name}Bytes[] = {{'+','.join(f'0x{x:02x}' for x in value)+'};']
    print(name,hex(rva),value.hex())
header+=['}']
(ROOT/'DivaRoom/NativeMenuSites.h').write_text('\n'.join(header)+'\n')
with zipfile.ZipFile(DOWNLOADS/'DivaRoom_Menu_7Estados_TRABAJO.zip') as z:
    aet=z.read(next(n for n in z.namelist() if n.endswith('.bin')))
ct=u(aet,16+36)
for i in range(u(aet,16+32)):
    for j in range(u(aet,ct+i*8)):
        p=u(aet,ct+i*8+4)+j*48
        name=s(aet,u(aet,p))
        if name.startswith('nsw_menu_selector_'):
            print('AET',i,j,name)
