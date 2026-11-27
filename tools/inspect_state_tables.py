"""Decode the executable's reviewed native state tables without changing them."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from project_paths import GAME_DIR, MOD_DIR, MIKUMIKUMODEL_DIR, ROOM_SOURCE_DIR
from pathlib import Path
import struct
from hashlib import sha256

exe = (GAME_DIR / 'DivaMegaMix.exe').read_bytes()
assert sha256(exe).hexdigest() == '6f4df714c28515c93b3023e7d6dafa9095dd8835f762d54db1726fb8bc04504d'
pe = struct.unpack_from('<I', exe, 60)[0]
sections = [struct.unpack_from('<IIII', exe, pe+24+struct.unpack_from('<H',exe,pe+20)[0]+40*i+8) for i in range(struct.unpack_from('<H',exe,pe+6)[0])]
def read(va,n):
    rva=va-0x140000000
    for vs,sv,rs,raw in sections:
        if sv<=rva and rva+n<=sv+rs: return exe[raw+rva-sv:raw+rva-sv+n]
    raise ValueError(hex(va))
def string(va):
    return read(va,64).split(b'\0')[0].decode('ascii',errors='replace')
if __name__ == '__main__':
    for i in range(12):
        name=struct.unpack('<Q',read(0x140bf6e70+i*8,8))[0]
        d=read(0x140bf74c0+i*0x88,0x88)
        print(i,string(name), 'id',struct.unpack_from('<I',d)[0], 'callbacks',[hex(x) for x in struct.unpack_from('<3Q',d,8)],'substates',struct.unpack_from('<24I',d,0x20),'next',struct.unpack_from('<I',d,0x80)[0])
