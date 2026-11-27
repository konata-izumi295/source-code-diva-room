#pragma once
#include "NativeScene.h"
#include "NativeRenderSites.h"

// The native renderer records CPU command streams, then executes them on its
// immediate D3D context (2c14c0 -> 2b8370). Calling D3D from the recording job
// would run too soon. Insert a private marker after UI target setup; consume it
// during execution, before native sprites, dialogs and post-processing.
namespace NativeRender {
inline uintptr_t base{};
inline bool installed{};
inline constexpr wchar_t Marker[]=L"DIVA_ROOM_SCENE_V1";
template<class F> F fn(uintptr_t rva){return reinterpret_cast<F>(base+rva);}
inline void setup(void* renderer,uintptr_t unused,unsigned char clear){
    fn<void(*)(void*,uintptr_t,unsigned char)>(NativeRenderSites::SetupRva)(renderer,unused,clear);
    // Context 1 is execute_3d's normal screen/UI pass (native-ui-schedule.txt).
    if(!RoomView::HasRoomVisuals()||*reinterpret_cast<int*>(static_cast<char*>(renderer)+8)!=1)return;
    auto* state=*reinterpret_cast<unsigned char**>(renderer);
    fn<void(*)(void*)>(NativeRenderSites::FlushRva)(state);
    auto* stream=*reinterpret_cast<unsigned char**>(state);
    auto*& cursor=*reinterpret_cast<unsigned char**>(stream+0x10);
    auto* end=*reinterpret_cast<unsigned char**>(stream+8);
    constexpr uint32_t bytes=sizeof(Marker);
    if(cursor>end||static_cast<size_t>(end-cursor)<8+bytes)return;
    uint32_t opcode=28;
    memcpy(cursor,&opcode,4);memcpy(cursor+4,&bytes,4);memcpy(cursor+8,Marker,bytes);
    cursor+=8+bytes;
    *reinterpret_cast<uint32_t*>(state+0x20)|=2;
}
inline void marker(ID3D11DeviceContext* context,void* annotation,unsigned char** cursor){
    uint32_t bytes{};memcpy(&bytes,*cursor,4);
    if(bytes==sizeof(Marker)&&memcmp(*cursor+4,Marker,sizeof(Marker))==0){
        *cursor+=4+bytes;RoomView::RenderNative(context);return;
    }
    fn<void(*)(ID3D11DeviceContext*,void*,unsigned char**)>(NativeRenderSites::MarkerRva)(context,annotation,cursor);
}
inline bool Install(uintptr_t module){
    if(installed)return true;
    base=module;using namespace NativeRenderSites;
    auto same=[](uintptr_t rva,const auto& bytes){return memcmp(reinterpret_cast<void*>(base+rva),bytes,sizeof(bytes))==0;};
    if(!same(SetupRva,SetupBytes)||!same(FlushRva,FlushBytes)||!same(MarkerRva,MarkerBytes))return false;
    std::vector<NativeScene::Patch> patches{NativeScene::site(SetupCallRva,SetupCallBytes),NativeScene::site(MarkerHandlerRva,MarkerHandlerBytes)};
    for(auto& p:patches)if(memcmp(reinterpret_cast<void*>(base+p.rva),p.before.data(),p.before.size()))return false;
    unsigned char* relay=nullptr;SYSTEM_INFO info{};GetSystemInfo(&info);
    for(uintptr_t address=(base+0x10000000)&~(uintptr_t(info.dwAllocationGranularity)-1);address<base+0x60000000;address+=info.dwAllocationGranularity){
        relay=static_cast<unsigned char*>(VirtualAlloc(reinterpret_cast<void*>(address),4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));if(relay)break;
    }
    if(!relay)return false;
    auto jump=[](unsigned char* p,void* target){p[0]=0xff;p[1]=0x25;memset(p+2,0,4);memcpy(p+6,&target,8);};
    jump(relay,reinterpret_cast<void*>(setup));jump(relay+16,reinterpret_cast<void*>(marker));
    auto callDelta=static_cast<int32_t>(reinterpret_cast<intptr_t>(relay)-static_cast<intptr_t>(base+SetupCallRva+5));
    auto markerDelta=static_cast<int32_t>(reinterpret_cast<intptr_t>(relay+16)-static_cast<intptr_t>(base+MarkerHandlerRva+7));
    memcpy(patches[0].after.data()+1,&callDelta,4);memcpy(patches[1].after.data()+3,&markerDelta,4);
    DWORD old{};
    if(!VirtualProtect(relay,4096,PAGE_EXECUTE_READ,&old)){VirtualFree(relay,0,MEM_RELEASE);return false;}
    size_t ready=0;
    for(auto& p:patches){if(!VirtualProtect(reinterpret_cast<void*>(base+p.rva),p.before.size(),PAGE_EXECUTE_READWRITE,&p.protection))break;++ready;}
    if(ready!=patches.size()){
        for(size_t i=ready;i>0;--i){auto& p=patches[i-1];VirtualProtect(reinterpret_cast<void*>(base+p.rva),p.before.size(),p.protection,&old);}
        VirtualFree(relay,0,MEM_RELEASE);return false;
    }
    for(auto& p:patches){memcpy(reinterpret_cast<void*>(base+p.rva),p.after.data(),p.after.size());VirtualProtect(reinterpret_cast<void*>(base+p.rva),p.after.size(),p.protection,&old);}
    FlushInstructionCache(GetCurrentProcess(),nullptr,0);
    RoomView::UseNativeRenderPass();installed=true;return true;
}
}
