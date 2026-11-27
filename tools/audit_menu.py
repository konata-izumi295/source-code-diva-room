"""Read-only inspection of local DivaRoom assets and prior menu experiments."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from project_paths import GAME_DIR, MOD_DIR, MIKUMIKUMODEL_DIR, ROOM_SOURCE_DIR
import gzip
import hashlib
import json
import struct
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GAME = (GAME_DIR)
DOWNLOADS = Path.home() / 'Downloads'

def u(b, p): return struct.unpack_from('<I', b, p)[0]
def s(b, p): return b[p:b.index(b'\0', p)].decode('ascii', 'replace')
def digest(b): return hashlib.sha256(b).hexdigest()

def database(b):
    sets, sp, count, ep = struct.unpack_from('<4I', b)
    assert sets < 100000 and count < 1000000
    assert sp + sets * 16 <= len(b) and ep + count * 12 <= len(b)
    return {
        'sets': [dict(zip(('id', 'name', 'file', 'index'),
                        (u(b,p), s(b,u(b,p+4)), s(b,u(b,p+8)),u(b,p+12))))
                 for p in range(sp, sp+sets*16, 16)],
        'entries': [{'id':u(b,p),'name':s(b,u(b,p+4)), 'packed_index':u(b,p+8)}
                    for p in range(ep, ep+count*12, 12)]}

def audit():
    mod = GAME / 'mods' / 'Diva Room Prototype'
    db = database((mod/'rom/2d/mod_spr_db.bin').read_bytes())
    farc = (mod/'rom/2d/spr_divaroom.farc').read_bytes()
    assert farc[:4] == b'FArC'
    name_end = farc.index(b'\0',12)
    offset, compressed, size = struct.unpack_from('>3I',farc,name_end+1)
    header_error = None
    try:
        payload = gzip.decompress(farc[offset:offset+compressed])
        assert len(payload) == size
    except (OSError, AssertionError) as ex:
        header_error = {'error':str(ex),'entry_fields_offset':name_end+1,
                        'offset':offset,'compressed':compressed,'size':size}
        # Recovery for inspection ONLY: the previous generator wrote fields at
        # a fixed address suited to a longer filename, leaving a three-byte gap.
        recovery_offset, recovery_compressed, recovery_size=struct.unpack_from('>3I',farc,32)
        payload=gzip.decompress(farc[recovery_offset:recovery_offset+recovery_compressed])
        assert len(payload)==recovery_size
    sprites = []
    for i in range(u(payload,12)):
        pos=u(payload,16)+i*40
        sprites.append({'name':s(payload,u(payload,u(payload,24)+i*4)),
                        'texture_index':u(payload,pos),
                        'record_hex':payload[pos:pos+40].hex()})
    report={'farc_header_error':header_error,'installed_db':db,'sprite_count':len(sprites),'texture_count':u(payload,8),
            'sprites':sprites,'collisions':[], 'database_parse_errors':[], 'aet':{}}
    wanted={e['id'] for e in db['sets']+db['entries']}
    for path in (GAME/'mods').rglob('*spr_db.bin'):
        if path == mod/'rom/2d/mod_spr_db.bin': continue
        try:
            other=database(path.read_bytes())
            for entry in other['sets']+other['entries']:
                if entry['id'] in wanted:
                    report['collisions'].append({'file':str(path),'entry':entry})
        except Exception as ex:
            report['database_parse_errors'].append({'file':str(path),'error':str(ex)})
    with zipfile.ZipFile(DOWNLOADS/'DivaRoom_Menu_7Estados_TRABAJO.zip') as z:
        b=z.read(next(n for n in z.namelist() if n.endswith('.bin')))
    scene=16
    ct=u(b,scene+36); vt=u(b,scene+44)
    videos=[]
    for i in range(u(b,scene+40)):
        p=vt+i*20
        for j in range(u(b,p+12)):
            q=u(b,p+16)+j*8
            name=s(b,u(b,q))
            if 'DIVAROOM' in name.upper():
                videos.append({'video':i,'name':name,'id':u(b,q+4),
                    'registered_in_current_db':u(b,q+4) in wanted,
                    'dimensions':struct.unpack_from('<HH',b,p+4)})
    layers=[]
    for i in range(u(b,ct+44*8)):
        p=u(b,ct+44*8+4)+i*48
        layers.append({'name':s(b,u(b,p)), 'frames':struct.unpack_from('<ff',b,p+4)})
    report['aet']={'sha256':digest(b),'divaroom_video_sources':videos,'selector_layers':layers}
    report['installed_hashes']={p.name:digest(p.read_bytes()) for p in [mod/'DivaRoom.dll',mod/'rom/2d/mod_spr_db.bin',mod/'rom/2d/spr_divaroom.farc']}
    return report

if __name__ == '__main__':
    report=audit()
    out=ROOT/'research'
    out.mkdir(exist_ok=True)
    (out/'menu-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
