"""Read exception and module metadata from local Windows minidumps, without uploads."""
import json
import struct
import sys
from pathlib import Path

def inspect(path):
    data = path.read_bytes()
    def unpack(fmt, offset):
        return struct.unpack_from('<' + fmt, data, offset)
    if data[:4] != b'MDMP':
        raise ValueError('Not a minidump')
    count, directory = unpack('II', 8)
    streams = {unpack('III', directory + i * 12)[0]: unpack('III', directory + i * 12)[1:] for i in range(count)}
    modules = []
    if 4 in streams:
        _, offset = streams[4]
        for i in range(unpack('I', offset)[0]):
            p = offset + 4 + i * 108
            base, size, _, _, name = unpack('QIIII', p)
            length = unpack('I', name)[0]
            modules.append((base, size, data[name+4:name+4+length].decode('utf-16-le')))
    result = {'dump': str(path)}
    memory = []
    if 5 in streams:
        _, offset = streams[5]
        for i in range(unpack('I', offset)[0]):
            va, size, raw = unpack('QII', offset+4+i*16)
            memory.append((va, size, raw))
    if 3 in streams:
        _, offset = streams[3]
        for i in range(unpack('I', offset)[0]):
            va, size, raw = unpack('QII', offset+4+i*48+24)
            memory.append((va, size, raw))
    def read(va, size):
        for start, length, raw in memory:
            if start <= va and va+size <= start+length:
                return data[raw+va-start:raw+va-start+size]
        return b''
    if 6 in streams:
        _, p = streams[6]
        code, flags, record, address, count = unpack('IIQQI', p+8)
        result.update(exception=hex(code), address=hex(address), parameters=[hex(x) for x in unpack('Q'*min(count,15),p+40)])
        result['fault_module'] = [{'name':name,'rva':hex(address-base)} for base,size,name in modules if base <= address < base+size]
        context_size, context = unpack('II', p+160)
        if context_size >= 256:
            result['registers'] = dict(zip(['rax','rcx','rdx','rbx','rsp','rbp','rsi','rdi','r8','r9','r10','r11','r12','r13','r14','r15','rip'],[hex(x) for x in unpack('Q'*17,context+120)]))
            rsp = int(result['registers']['rsp'],16)
            stack = []
            for slot in range(rsp,rsp+4096,8):
                value = read(slot,8)
                if not value: continue
                address = int.from_bytes(value,'little')
                for base,size,name in modules:
                    if base <= address < base+size and ('DivaMegaMix.exe' in name or 'DivaRoom.dll' in name or 'dinput8.dll' in name):
                        stack.append({'slot':hex(slot),'module':Path(name).name,'rva':hex(address-base)})
            result['stack_candidates_not_unwound'] = stack
            result['exception_object_bytes'] = read(unpack('Q',p+48)[0],128).hex()
            obj=read(unpack('Q',p+48)[0],16)
            if len(obj)==16:
                message_ptr=int.from_bytes(obj[8:16],'little')
                message=bytearray()
                for i in range(512):
                    ch=read(message_ptr+i,1)
                    if not ch or ch==b'\0': break
                    message+=ch
                result['exception_message_candidate']=message.decode('utf-8','replace')
    result['mod_modules'] = [{'name':n, 'base':hex(b),'size':s} for b,s,n in modules if 'diva' in n.lower() or 'dinput' in n.lower()]
    return result

if __name__ == '__main__':
    print(json.dumps([inspect(Path(p)) for p in sys.argv[1:]],indent=2))
