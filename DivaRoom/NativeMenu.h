#pragma once
#include <Windows.h>
#include <bcrypt.h>
#include <array>
#include <vector>
#include <cstdint>
#include <cstring>
#include "NativeMenuSites.h"
#include "MenuDescription.h"
#include "RoomView.h"
#include "NativeLoading.h"
#include "NativeScene.h"
#pragma comment(lib, "bcrypt.lib")

// Version-specific native menu adapter. Sites were inspected in Ghidra.
// Native arrays stay at six; the draw sites use our own seven-name tables.
namespace NativeMenu {
inline uintptr_t base;
inline bool installed = false;
inline bool spritesRequested = false;
inline bool spritesReady = false;
inline bool slotHasDiva=false;
inline bool slotExiting=false;
inline const char* normal[] = {
    "nsw_menu_selector_rhythmgame", "nsw_menu_selector_divaroom",
    "nsw_menu_selector_customize", "nsw_menu_selector_playlist",
    "nsw_menu_selector_gallery", "nsw_menu_selector_eshop", "nsw_menu_selector_option"
};
inline const char* selected[] = {
    "nsw_menu_selector_rhythmgame_sel", "nsw_menu_selector_divaroom_sel",
    "nsw_menu_selector_customize_sel", "nsw_menu_selector_playlist_sel",
    "nsw_menu_selector_gallery_sel", "nsw_menu_selector_eshop_sel", "nsw_menu_selector_option_sel"
};
template<class F> F fn(uintptr_t rva) { return reinterpret_cast<F>(base+rva); }
inline int originalIndex(int value) { return value > 1 ? value-1 : 0; }
inline thread_local int footerIndex=-1;
inline void footer(void* state,unsigned char) {
    int index=*reinterpret_cast<int*>(static_cast<char*>(state)-0x300+0x74);
    const int previous=footerIndex;
    footerIndex=index;
    fn<void(*)(void*,unsigned char)>(0x6c14b0)(state,static_cast<unsigned char>(index==1?7:originalIndex(index)+1));
    footerIndex=previous;
}
inline const char* footerText(int id) {
    return footerIndex==1 ? divaDescription() : fn<const char*(*)(int)>(0x239bc0)(id);
}
inline void initializeList(void* list,int* config) {
    // Six visible rows, with the focused row third from the top. The AET
    // slots are ordered spatially instead of wrapping at six logical items.
    config[3]=2;
    fn<void(*)(void*,int*)>(0x6695d0)(list,config);
}
inline int initial() {
    slotHasDiva=false;
    slotExiting=false;
    if (!spritesRequested) {
        struct StringRange { const char* first; const char* last; } empty{};
        fn<void(*)(uint32_t, StringRange&)>(0x5b4770)(1345048883,empty);
        spritesRequested=true;
    }
    int old = fn<int(*)()>(0x6bfcf0)();
    if(NativeScene::ReturnSelection())return 1;
    return old >= 0 && old < 6 ? (old == 0 ? 0 : old+1) : 0;
}
inline bool confirm(void* list) {
    bool pressed = fn<bool(*)(void*)>(0x66a8e0)(list);
    int index = *reinterpret_cast<int*>(static_cast<char*>(list)+4);
    if (pressed && index == 1) {
        return NativeScene::Request();
    }
    return pressed;
}
inline unsigned char dispatch(void* menu) {
    int index = *reinterpret_cast<int*>(static_cast<char*>(menu)+0x74);
    if(index==1)return 8; // routed by the independent scene adapter after native exit
    return static_cast<unsigned char>(originalIndex(index)+1);
}
inline unsigned char background(void* state, int index) {
    // The native loader has a separate completion step; requesting alone never
    // uploads the sprite atlas. Run it on the game's menu update thread.
    if(spritesRequested && !spritesReady && !fn<bool(*)(uint32_t)>(0x5b4810)(1345048883)) {
        spritesReady=true;
    }
    // Reuse one native controller through its release/init lifecycle, preserving
    // all six original compositions and the game's fixed-size arrays.
    if(spritesReady) {
        auto* bytes=static_cast<char*>(state);
        auto& current=*reinterpret_cast<int*>(bytes+0x3194);
        auto& outgoing=*reinterpret_cast<int*>(bytes+0x31a0);
        const bool wantsDiva=index==1;
        if(slotExiting) {
            if(!fn<bool(*)(void*)>(0x660430)(state)) return 0;
            fn<void(*)(void*)>(0x65f910)(state);
            current=6; outgoing=-1; slotExiting=false;
        }
        if(index<=1 && slotHasDiva!=wantsDiva) {
            if(current==0) {
                fn<void(*)(void*,int)>(0x660330)(state,4);
                slotExiting=true;
                return 0;
            }
            // Let a previous native exit complete before replacing its object.
            if(outgoing==0) {
                fn<unsigned char(*)(void*)>(0x6c1ca0)(state);
                return 0;
            }
            fn<void(*)(void*)>(0x6603c0)(state);
            fn<void(*)(void*,const char*,int,int,int)>(0x65f820)(state,
                wantsDiva?"chara_mainmenu_divaroom":"chara_mainmenu_rhythmgame",8,2,0x512);
            slotHasDiva=wantsDiva;
        }
    }
    return fn<unsigned char(*)(void*,int)>(0x6c1ad0)(state, originalIndex(index));
}

inline bool supportedExecutable() {
    wchar_t path[MAX_PATH];
    if (!GetModuleFileNameW(nullptr,path,MAX_PATH)) return false;
    HANDLE file=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,0,nullptr);
    if (file==INVALID_HANDLE_VALUE) return false;
    BCRYPT_ALG_HANDLE alg=nullptr; BCRYPT_HASH_HANDLE hash=nullptr;
    bool ok=BCryptOpenAlgorithmProvider(&alg,BCRYPT_SHA256_ALGORITHM,nullptr,0)>=0;
    if (ok) ok=BCryptCreateHash(alg,&hash,nullptr,0,nullptr,0,0)>=0;
    std::array<unsigned char,65536> buffer{};
    DWORD size=0;
    while(ok) {
        if(!ReadFile(file,buffer.data(),static_cast<DWORD>(buffer.size()),&size,nullptr)) { ok=false; break; }
        if(!size) break;
        ok=BCryptHashData(hash,buffer.data(),size,0)>=0;
    }
    unsigned char result[32]{};
    if(ok) ok=BCryptFinishHash(hash,result,32,0)>=0;
    if(hash) BCryptDestroyHash(hash);
    if(alg) BCryptCloseAlgorithmProvider(alg,0);
    CloseHandle(file);
    constexpr unsigned char expected[]={0x6f,0x4d,0xf7,0x14,0xc2,0x85,0x15,0xc9,0x3b,0x30,0x23,0xe7,0xd6,0xda,0xfa,0x90,0x95,0xdd,0x88,0x35,0xf7,0x62,0xd5,0x4d,0xb1,0x72,0x6f,0xb8,0xbc,0x04,0x50,0x4d};
    return ok && !memcmp(result,expected,32);
}
struct Patch { uintptr_t rva; std::vector<unsigned char> before,after; DWORD protection=0; };

// Ghidra: main-menu control vtable slot 0x140cc6f98 references 0x1406be770.
// Let the original task finish its confirmation, exit animation and fade.
// The scene manager, not this menu task, updates the room afterwards.
inline uint64_t control(void* menu) {
    return fn<uint64_t(*)(void*)>(0x6be770)(menu);
}
template<size_t N> Patch site(uintptr_t rva,const unsigned char (&bytes)[N]) {
    return {rva,{bytes,bytes+N},{bytes,bytes+N}};
}
// Replaces the entire native string-array lookup, avoiding index 6 accessing
// the original six-element buffers. Only volatile RAX and destination change.
inline void names(Patch& p,const char** table,bool rdx) {
    p.after.assign(p.before.size(),0x90);
    p.after[0]=0x48; p.after[1]=0xb8; // mov rax, table
    auto address=reinterpret_cast<uintptr_t>(table);
    memcpy(p.after.data()+2,&address,8);
    if(rdx) { // mov rdx,[rax+rdx*8]
        unsigned char op[]={0x48,0x8b,0x14,0xd0}; memcpy(p.after.data()+10,op,4);
    } else { // mov r8,[rax+r8*8]
        unsigned char op[]={0x4e,0x8b,0x04,0xc0}; memcpy(p.after.data()+10,op,4);
    }
}
inline unsigned char* allocateRelay() {
    SYSTEM_INFO si{}; GetSystemInfo(&si);
    uintptr_t start=(base+0x10000000)&~(uintptr_t(si.dwAllocationGranularity)-1);
    for(uintptr_t p=start;p<base+0x70000000;p+=si.dwAllocationGranularity) {
        auto* memory=static_cast<unsigned char*>(VirtualAlloc(reinterpret_cast<void*>(p),4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));
        if(memory) return memory;
    }
    return nullptr;
}
inline void call(Patch& p,unsigned char* relay,void* target) {
    relay[0]=0xff; relay[1]=0x25; memset(relay+2,0,4);
    memcpy(relay+6,&target,8); // indirect absolute jump; preserves ABI registers
    auto displacement=static_cast<int32_t>(reinterpret_cast<uintptr_t>(relay)-(base+p.rva+5));
    p.after[0]=0xe8; memcpy(p.after.data()+1,&displacement,4);
}
inline bool Install() {
    if(installed) return true;
    base=reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
    if(!supportedExecutable()) return false;
    NativeLoading::configure(base);
    using namespace NativeMenuSites;
    std::vector<Patch> patches{
        site(CountRva,CountBytes),site(NormalNamesRva,NormalNamesBytes),
        site(SelectedNamesRva,SelectedNamesBytes),site(DialogNameRva,DialogNameBytes),
        site(InitialSelectionRva,InitialSelectionBytes),site(ConfirmRva,ConfirmBytes),
        site(DispatchRva,DispatchBytes),site(BackgroundRva,BackgroundBytes),
        site(ListInitializeRva,ListInitializeBytes),
        site(FooterRva,FooterBytes),site(FooterTextRva,FooterTextBytes)};
    Patch controlSlot{0xcc6f98,std::vector<unsigned char>(8),std::vector<unsigned char>(8)};
    auto originalControl=base+0x6be770;
    auto replacementControl=reinterpret_cast<uintptr_t>(&control);
    memcpy(controlSlot.before.data(),&originalControl,8);
    memcpy(controlSlot.after.data(),&replacementControl,8);
    patches.push_back(controlSlot);
    // Validate every site before modifying any, including other mods' patches.
    for(auto& p:patches) if(memcmp(reinterpret_cast<void*>(base+p.rva),p.before.data(),p.before.size())) {
        return false;
    }
    auto* relay=allocateRelay();
    if(!relay) return false;
    patches[0].after[3]=7; // total count, retaining six visible slots and scrolling
    names(patches[1],normal,false); names(patches[2],selected,false); names(patches[3],selected,true);
    call(patches[4],relay,reinterpret_cast<void*>(&initial));
    call(patches[5],relay+16,reinterpret_cast<void*>(&confirm));
    call(patches[6],relay+32,reinterpret_cast<void*>(&dispatch));
    call(patches[7],relay+48,reinterpret_cast<void*>(&background));
    call(patches[8],relay+64,reinterpret_cast<void*>(&initializeList));
    call(patches[9],relay+80,reinterpret_cast<void*>(&footer));
    call(patches[10],relay+96,reinterpret_cast<void*>(&footerText));
    DWORD old=0;
    if(!VirtualProtect(relay,4096,PAGE_EXECUTE_READ,&old)) { VirtualFree(relay,0,MEM_RELEASE); return false; }
    FlushInstructionCache(GetCurrentProcess(),relay,4096);
    size_t ready=0;
    for(auto& p:patches) {
        if(!VirtualProtect(reinterpret_cast<void*>(base+p.rva),p.before.size(),PAGE_EXECUTE_READWRITE,&p.protection)) break;
        ++ready;
    }
    if(ready!=patches.size()) {
        for(size_t i=ready;i>0;--i) VirtualProtect(reinterpret_cast<void*>(base+patches[i-1].rva),patches[i-1].before.size(),patches[i-1].protection,&old);
        VirtualFree(relay,0,MEM_RELEASE); return false;
    }
    for(auto& p:patches) memcpy(reinterpret_cast<void*>(base+p.rva),p.after.data(),p.after.size());
    for(auto it=patches.rbegin();it!=patches.rend();++it) {
        auto& p=*it;
        VirtualProtect(reinterpret_cast<void*>(base+p.rva),p.after.size(),p.protection,&old);
        FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(base+p.rva),p.after.size());
    }
    installed=true;
    NativeScene::Install(base);
    return true;
}
}
