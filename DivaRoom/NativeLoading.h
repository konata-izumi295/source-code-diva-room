#pragma once
#include <Windows.h>
#include <cstdint>
#include <cstring>
#include "NativeLoadingSites.h"
#include "NativeSceneSites.h"
#include "RoomView.h"

// Verified WAIT_SCREEN lifecycle in this supported executable. The scene ID
// 0x521 resolves to AET_NSWGAM_CMN_MAIN: loading_bg and now_loading.
// Keep all calls on the native task-update thread, never DML's Present callback.
namespace NativeLoading {
inline uintptr_t base{};
inline bool ready{},soundReady{},musicReady{},roomMusicReady{},roomMusicOwned{};
inline ULONGLONG musicPollAt{};
inline unsigned musicRetries{};
inline void (*returnToMenu)(){};
template<class F> F fn(uintptr_t rva){return reinterpret_cast<F>(base+rva);}
inline bool begin() {
    auto* task=reinterpret_cast<unsigned char*>(base+0xcc0b530);
    if(*reinterpret_cast<int*>(task+0x70)!=0 || !fn<bool(*)(void*)>(NativeLoadingSites::ExistsRva)(task))return false;
    fn<void(*)(uintptr_t,int,unsigned char)>(NativeLoadingSites::BeginRva)(0,0,0);
    // The previous scene finished its native fade-out. Reveal WAIT_SCREEN.
    fn<void(*)(uintptr_t,float,unsigned)>(NativeSceneSites::FadeInRva)(0,0.25f,0);
    return true;
}
inline void finish(){fn<void(*)()>(NativeLoadingSites::FinishRva)();}
inline bool finished(){return fn<bool(*)()>(NativeLoadingSites::FinishedRva)();}
inline void reset(){fn<void(*)(uintptr_t)>(NativeLoadingSites::ResetRva)(0);}
inline void sound(int kind) {
    if(!soundReady)return;
    using namespace NativeLoadingSites;
    if(kind==3){fn<void(*)(const char*,float)>(SoundRva)("se_ft_sys_dialog_open",1.f);return;}
    fn<void(*)()>(kind==0?ConfirmSoundRva:kind==1?CancelSoundRva:SelectSoundRva)();
}
inline void stopMenuMusic(){if(musicReady)fn<void(*)(unsigned)>(NativeLoadingSites::StopMusicRva)(0);}
inline bool startRoomMusic(){
    if(!roomMusicReady)return false;
    // Same channel/path/restart ABI as the verified native menu BGM callers.
    roomMusicOwned=fn<bool(*)(unsigned,const char*,unsigned char)>(NativeLoadingSites::PlayMusicRva)(0,"rom/sound/bgm/divaroom.ogg",1);
    musicPollAt=GetTickCount64()+1500;musicRetries=0;
    return roomMusicOwned;
}
inline void updateRoomMusic(){
    if(!roomMusicOwned||GetTickCount64()<musicPollAt)return;
    musicPollAt=GetTickCount64()+500;
    // Active includes pending playback (channel +0x4c) as well as playing
    // (+0x50). Never restart a stream that is still loading or playing.
    if(fn<bool(*)()>(NativeLoadingSites::MusicActiveRva)()){musicRetries=0;return;}
    if(musicRetries++<3){
        fn<bool(*)(unsigned,const char*,unsigned char)>(NativeLoadingSites::PlayMusicRva)(0,"rom/sound/bgm/divaroom.ogg",1);
        musicPollAt=GetTickCount64()+1500;
    }
}
inline void stopRoomMusic(){
    if(roomMusicOwned){stopMenuMusic();roomMusicOwned=false;}
}
inline void returnMenu(){if(returnToMenu)returnToMenu();}
inline unsigned inputPressed(){
    using namespace NativeSceneSites;
    void* input=fn<void*(*)(int)>(InputStateRva)(0);
    if(!input)return 0;
    auto mapped=fn<bool(*)(void*,int)>(InputMappedPressRva);
    auto raw=fn<bool(*)(void*,int)>(InputPressRva);
    // Same action queries as PAUSE_MENU_SWITCH (65be90): keyboard and
    // configured controller bindings flow through the game's mapping table.
    unsigned result=0;
    if(mapped(input,0xa0))result|=1;
    if(mapped(input,3))result|=2;
    if(mapped(input,4))result|=4;
    if(mapped(input,10)||raw(input,0x91))result|=8;
    if(mapped(input,8))result|=16;
    return result;
}
template<size_t N> bool same(uintptr_t rva,const unsigned char(&expected)[N]) {
    return memcmp(reinterpret_cast<void*>(base+rva),expected,N)==0;
}
inline bool configure(uintptr_t module) {
    base=module;using namespace NativeLoadingSites;
    ready=same(BeginRva,BeginBytes)&&same(FinishRva,FinishBytes)&&same(FinishedRva,FinishedBytes)&&same(ResetRva,ResetBytes)&&same(ExistsRva,ExistsBytes)&&same(NativeSceneSites::FadeInRva,NativeSceneSites::FadeInBytes);
    // Audio compatibility must never disable the seventh menu option.
    // Do not validate/call EnterSound: it is a title-screen routine hooked by
    // an installed mod, not the loading transition.
    soundReady=same(ConfirmSoundRva,ConfirmSoundBytes)&&same(CancelSoundRva,CancelSoundBytes)&&same(SelectSoundRva,SelectSoundBytes)&&same(SoundRva,SoundBytes);
    musicReady=same(StopMusicRva,StopMusicBytes);
    roomMusicReady=musicReady&&same(PlayMusicRva,PlayMusicBytes)&&same(MusicActiveRva,MusicActiveBytes);
    using namespace NativeSceneSites;
    if(same(InputStateRva,InputStateBytes)&&same(InputMappedPressRva,InputMappedPressBytes)&&same(InputPressRva,InputPressBytes))RoomView::SetInputReader(inputPressed);
    if(ready)RoomView::SetLoadingApi({begin,finish,finished,reset,nullptr,returnMenu,sound,nullptr,startRoomMusic,updateRoomMusic,stopRoomMusic});
    return ready;
}
}
