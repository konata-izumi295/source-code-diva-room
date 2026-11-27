"""Correct the sprite binary filename without relocating existing DB records."""
import struct
from pathlib import Path
from audit_menu import database, ROOT

def repair(data):
    parsed = database(data)
    assert len(parsed['sets']) == 1
    assert parsed['sets'][0]['name'] == 'SPR_DIVAROOM'
    if parsed['sets'][0]['file'] == 'spr_divaroom.bin':
        return data
    assert parsed['sets'][0]['file'] == 'spr_divaroom'
    result = bytearray(data)
    set_offset = struct.unpack_from('<I',result,4)[0]
    struct.pack_into('<I',result,set_offset+8,len(result))
    result += b'spr_divaroom.bin\0'
    assert database(result)['sets'][0]['file'] == 'spr_divaroom.bin'
    assert database(result)['entries'] == parsed['entries']
    return bytes(result)

if __name__ == '__main__':
    import sys
    source=Path(sys.argv[1])
    output=ROOT/'research/repaired-assets/mod_spr_db.bin'
    output.write_bytes(repair(source.read_bytes()))
    print(output)
