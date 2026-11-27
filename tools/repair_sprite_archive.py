"""Repair the known malformed prototype into research/, without installing it."""
import gzip
import hashlib
import json
import struct
from pathlib import Path
from audit_menu import GAME, ROOT

src=GAME/'mods/Diva Room Prototype/rom/2d/spr_divaroom.farc'
b=src.read_bytes()
assert hashlib.sha256(b).hexdigest()=='7f13592dc765ed6e574c377704d42327ab1fff9148e2279731fcb2f82b53dd6c'
name=b'spr_divaroom.bin\0'
offset, compressed, size=struct.unpack_from('>3I',b,32)
stream=b[offset:offset+compressed]
payload=gzip.decompress(stream)
assert len(payload)==size
# FArC has no alignment between filename and its three big-endian fields.
header_size=12+len(name)+12
data_offset=(header_size+15)//16*16
fixed=b'FArC'+struct.pack('>II',header_size-8,16)+name+struct.pack('>III',data_offset,compressed,size)
fixed+=b'x'*(data_offset-len(fixed))+stream
fixed+=b'x'*((-len(fixed))%16)
# Re-read the standard variable-length directory rather than fixed addresses.
cursor=12
end=fixed.index(b'\0',cursor)
actual_offset, actual_compressed, actual_size=struct.unpack_from('>III',fixed,end+1)
assert end+1+12==struct.unpack_from('>I',fixed,4)[0]+8
assert gzip.decompress(fixed[actual_offset:actual_offset+actual_compressed])==payload
assert actual_size==len(payload)
out=ROOT/'research/repaired-assets'
out.mkdir(parents=True,exist_ok=True)
(out/'spr_divaroom.farc').write_bytes(fixed)
report={'original':str(src),'original_sha256':hashlib.sha256(b).hexdigest(),
        'repaired_sha256':hashlib.sha256(fixed).hexdigest(),
        'payload_unchanged':True,'payload_sha256':hashlib.sha256(payload).hexdigest(),
        'old_fields_offset':32,'correct_fields_offset':12+len(name),
        'status':'offline repair; not installed; does not add menu entry'}
(out/'repair.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
