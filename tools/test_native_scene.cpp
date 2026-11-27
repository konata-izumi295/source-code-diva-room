#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include "../DivaRoom/NativeScene.h"
#include <cstdio>

// Isolated ABI/table regression: no live game and no injected process.
namespace RoomView {
void Open(){} void Update(){} bool ReleaseScene(){return true;}
void SetLoadingApi(LoadingApi){}
void SetInputReader(unsigned(*)()){}
}
int main(){
    using namespace NativeScene;
    auto* arena=static_cast<unsigned char*>(VirtualAlloc(nullptr,0xc00000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));
    if(!arena)return 1;
    base=reinterpret_cast<uintptr_t>(arena);
    auto* mains=reinterpret_cast<State*>(base+0xbf74c0);
    const int ids[]={0,1,2,4,5,3,6,7,8,10,9,11};
    for(int i=0;i<12;++i)mains[i].id=ids[i];
    auto* subs=reinterpret_cast<Substate*>(base+0xbf6ee0);
    for(int i=0;i<47;++i)subs[i].id=i;
    for(int i=0;i<12;++i)if(mainLookup(ids[i])!=mains+i)return 2;
    for(int i=0;i<47;++i)if(subLookup(i)!=(i==42?&menuSubstate:subs+i))return 3;
    if(mainLookup(12)||subLookup(47)||mainLookup(-1)||subLookup(-1))return 4;
    if(mainLookup(RoomState)!=&roomState||subLookup(RoomSubstate)!=&roomSubstate)return 5;
    installed=false;if(Request()||pending)return 6;
    installed=true;if(!Request()||!pending)return 7;
    returning=true;if(!ReturnSelection()||ReturnSelection())return 8;
    VirtualFree(arena,0,MEM_RELEASE);
    puts("PASS: all stock scenes retained; custom scenes and sentinels distinct; guarded selection.");
    return 0;
}
