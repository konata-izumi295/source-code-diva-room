#pragma once
#include <Windows.h>
#include <array>
#include <cstdint>
#include <cstring>
#include <vector>
#include "NativeSceneSites.h"
#include "NativeLoading.h"
#include "RoomView.h"

// ABI and lifecycle verified in research/native-state-*.txt.
// Extend the lookup tables; never reuse a stock scene or its task object.
namespace NativeScene {
inline uintptr_t base{};
inline bool installed{}, pending{}, returning{};
inline constexpr int RoomState=13; // 12 is the engine's "no next state" sentinel.
inline constexpr int RoomSubstate=48; // 47 is the substate sentinel.
// GAME_SWITCH / substate 42 owns the seven-row menu. State 10 / substate 39
// is a different selector; its similar name does not make it this dispatcher.
inline constexpr int MenuState=9, MenuSubstate=42;
using Callback=bool(*)();
struct Substate { int id; unsigned flags; Callback init,ctrl,dest; };
struct State { int id; unsigned padding; Callback init,ctrl,dest; int sequence[24]; int next,padding2; };
static_assert(sizeof(Substate)==0x20 && sizeof(State)==0x88);
inline State roomState{};
inline Substate roomSubstate{},menuSubstate{};
template<class F> F fn(uintptr_t rva){return reinterpret_cast<F>(base+rva);}
inline bool yes(){return true;}
inline bool no(){return false;}
inline void requestReturn() {
    returning=true;
    fn<void(*)(int)>(NativeSceneSites::ChangeStateRva)(MenuState);
}
inline bool roomInit() {
    // The engine has completed the menu's dest callbacks before entering here.
    // Refuse to draw on top of a surviving menu task.
    if(*reinterpret_cast<void**>(base+0xcc5eef8)) {requestReturn();return true;}
    NativeLoading::stopMenuMusic();
    RoomView::Open();
    return true;
}
inline bool roomCtrl(){RoomView::Update();return false;}
inline bool roomDest(){return RoomView::ReleaseScene();}
inline bool menuCtrl() {
    if(!pending)return fn<bool(*)()>(0x653040)();
    if(fn<bool(*)()>(NativeSceneSites::MenuBusyRva)())return false;
    if(!fn<bool(*)()>(NativeSceneSites::MenuDoneRva)())return false;
    pending=false;
    fn<void(*)(int)>(NativeSceneSites::ChangeStateRva)(RoomState);
    return false;
}
inline State* mainLookup(int id) {
    if(id==RoomState)return &roomState;
    auto* states=reinterpret_cast<State*>(base+0xbf74c0);
    for(int i=0;i<12;++i)if(states[i].id==id)return states+i;
    return nullptr;
}
inline Substate* subLookup(int id) {
    if(id==RoomSubstate)return &roomSubstate;
    if(id==MenuSubstate)return &menuSubstate;
    auto* states=reinterpret_cast<Substate*>(base+0xbf6ee0);
    for(int i=0;i<47;++i)if(states[i].id==id)return states+i;
    return nullptr;
}
inline bool Request(){if(!installed)return false;pending=true;return true;}
inline bool ReturnSelection(){bool value=returning;returning=false;return value;}

struct Patch { uintptr_t rva;std::vector<unsigned char> before,after;DWORD protection{}; };
template<size_t N> Patch site(uintptr_t rva,const unsigned char(&bytes)[N]){return {rva,{bytes,bytes+N},{bytes,bytes+N}};}
inline void jump(Patch& p,void* target){
    p.after.assign(p.before.size(),0x90);p.after[0]=0xff;p.after[1]=0x25;
    memset(p.after.data()+2,0,4);memcpy(p.after.data()+6,&target,8);
}
template<size_t N> bool same(uintptr_t rva,const unsigned char(&bytes)[N]){return memcmp(reinterpret_cast<void*>(base+rva),bytes,N)==0;}
inline bool Install(uintptr_t module) {
    if(installed)return true;
    base=module;using namespace NativeSceneSites;
    if(!NativeLoading::ready||!same(ChangeStateRva,ChangeStateBytes)||!same(MenuDoneRva,MenuDoneBytes)||!same(MenuBusyRva,MenuBusyBytes)||!same(FadeInRva,FadeInBytes))return false;
    auto* originalMenu=reinterpret_cast<Substate*>(base+0xbf6ee0)+MenuSubstate;
    if(originalMenu->id!=MenuSubstate||originalMenu->init!=fn<Callback>(0x652ff0)||originalMenu->ctrl!=fn<Callback>(0x653040)||originalMenu->dest!=fn<Callback>(0x653190))return false;
    std::vector<Patch> patches{site(MainLookupRva,MainLookupBytes),site(SubLookupRva,SubLookupBytes),site(StateNamesRva,StateNamesBytes)};
    for(auto& p:patches)if(memcmp(reinterpret_cast<void*>(base+p.rva),p.before.data(),p.before.size()))return false;
    menuSubstate=*originalMenu;menuSubstate.ctrl=menuCtrl;
    roomSubstate={RoomSubstate,1,roomInit,roomCtrl,roomDest};
    roomState={RoomState,0,yes,no,yes,{},MenuState,0};
    for(auto& id:roomState.sequence)id=47;
    roomState.sequence[0]=RoomSubstate;
    // The native transition logger indexes its name table by state ID.
    // Extend that table too, preserving sentinel 12 and all stock names.
    unsigned char* storage=nullptr;
    SYSTEM_INFO info{};GetSystemInfo(&info);
    for(uintptr_t address=(base+0x11000000)&~(uintptr_t(info.dwAllocationGranularity)-1);address<base+0x70000000;address+=info.dwAllocationGranularity){
        storage=static_cast<unsigned char*>(VirtualAlloc(reinterpret_cast<void*>(address),4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));if(storage)break;
    }
    if(!storage)return false;
    auto** names=reinterpret_cast<const char**>(storage);
    memcpy(names,reinterpret_cast<void*>(base+0xbf6e70),12*sizeof(char*));
    names[12]="NONE";names[13]="DIVA_ROOM";
    jump(patches[0],reinterpret_cast<void*>(mainLookup));jump(patches[1],reinterpret_cast<void*>(subLookup));
    auto distance=reinterpret_cast<intptr_t>(storage)-static_cast<intptr_t>(base+StateNamesRva+7);
    if(distance<INT32_MIN||distance>INT32_MAX){VirtualFree(storage,0,MEM_RELEASE);return false;}
    auto displacement=static_cast<int32_t>(distance);memcpy(patches[2].after.data()+3,&displacement,4);
    DWORD old{};if(!VirtualProtect(storage,4096,PAGE_READONLY,&old)){VirtualFree(storage,0,MEM_RELEASE);return false;}
    size_t readyCount=0;
    for(auto& p:patches){if(!VirtualProtect(reinterpret_cast<void*>(base+p.rva),p.before.size(),PAGE_EXECUTE_READWRITE,&p.protection))break;++readyCount;}
    if(readyCount!=patches.size()){
        for(size_t i=readyCount;i>0;--i){auto& p=patches[i-1];VirtualProtect(reinterpret_cast<void*>(base+p.rva),p.before.size(),p.protection,&old);}
        VirtualFree(storage,0,MEM_RELEASE);return false;
    }
    for(auto& p:patches)memcpy(reinterpret_cast<void*>(base+p.rva),p.after.data(),p.after.size());
    for(auto& p:patches){VirtualProtect(reinterpret_cast<void*>(base+p.rva),p.after.size(),p.protection,&old);FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(base+p.rva),p.after.size());}
    NativeLoading::returnToMenu=requestReturn;
    installed=true;return true;
}
}
